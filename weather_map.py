import requests
import geopandas as gpd
import folium
import pandas as pd
from datetime import datetime, timezone
import pytz # Standard in most environments
from branca.element import Template, MacroElement

def get_color(event):
    event = event.lower()
    if 'small craft' in event: return '#3498db'
    if 'gale' in event: return '#8e44ad'
    if 'flood' in event: return '#2ecc71'
    if 'tornado' in event: return '#e74c3c'
    if 'winter' in event: return '#95a5a6'
    return '#e67e22'

headers = {'User-Agent': 'MyWeatherApp/1.0 (contact@example.com)'}
NC_COUNTIES_URL = "https://raw.githubusercontent.com/codeforamerica/click_counties/master/data/counties/north_carolina.geojson"

# 1. Setup Time and Map
utc_now = datetime.now(timezone.utc)
eastern = pytz.timezone('US/Eastern')
local_time = utc_now.astimezone(eastern).strftime('%I:%M %p %Z')

m = folium.Map(location=[35.2, -76.5], zoom_start=7, tiles=None)

# 2. Add Backgrounds
folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)
folium.TileLayer('CartoDB positron', name='Light Labels').add_to(m)
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}',
    attr='Esri', name='Terrain', overlay=False
).add_to(m)

# 3. Add Counties
folium.GeoJson(NC_COUNTIES_URL, name='County Boundaries',
               style_function=lambda x: {'color': '#555', 'weight': 1, 'fillOpacity': 0}).add_to(m)

# 4. Fetch Weather
nc_marine_zones = ["AMZ131", "AMZ135", "AMZ136", "AMZ137", "AMZ150", "AMZ152", "AMZ154", "AMZ156", "AMZ158", "AMZ230", "AMZ231"]
urls = ["https://api.weather.gov/alerts/active?area=NC", f"https://api.weather.gov/alerts/active?zone={','.join(nc_marine_zones)}"]

all_features = []
active_event_types = {}

for url in urls:
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            for f in res.json().get('features', []):
                props = f['properties']
                if props.get('status') != 'Actual': continue
                end_time = props.get('ends')
                if end_time and pd.to_datetime(end_time) < utc_now: continue
                
                if not f.get('geometry'):
                    az = props.get('affectedZones', [])
                    if az:
                        z_res = requests.get(az[0], headers=headers)
                        if z_res.status_code == 200: f['geometry'] = z_res.json().get('geometry')
                
                if f.get('geometry'):
                    all_features.append(f)
                    event_name = props.get('event', 'Other')
                    active_event_types[event_name] = get_color(event_name)
    except: continue

# Add Alerts to Map
if all_features:
    gdf = gpd.GeoDataFrame.from_features(all_features).set_crs(epsg=4326)
    folium.GeoJson(gdf, name="Weather Alerts",
                   style_function=lambda x: {'fillColor': get_color(x['properties']['event']), 'color': 'black', 'weight': 1, 'fillOpacity': 0.5},
                   tooltip=folium.GeoJsonTooltip(fields=['event', 'headline'], aliases=['Alert:', 'Details:'])).add_to(m)

# 5. Add Title and Legend (Combined HTML)
legend_items = "".join([f'<li><span style="background:{color}; opacity:0.7;"></span>{event}</li>' for event, color in sorted(active_event_types.items())])
if not legend_items:
    legend_items = "<li><i>No Active Alerts</i></li>"

title_html = f'''
{{% macro html(this, kwargs) %}}
<div id="maptitle" style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index:9999; 
     background-color:rgba(255, 255, 255, 0.9); padding: 10px 20px; border-radius: 10px; border: 2px solid #34495e;
     font-family: Arial, sans-serif; font-size: 18px; font-weight: bold; text-align: center; box-shadow: 0px 2px 5px rgba(0,0,0,0.2);">
    Current North Carolina Weather Alerts<br>
    <span style="font-size: 12px; font-weight: normal; color: #555;">Updated: {local_time}</span>
</div>

<div id="maplegend" style="position: fixed; z-index:9999; border:2px solid grey; background-color:rgba(255, 255, 255, 0.8); 
     border-radius:6px; padding: 10px; font-size:14px; right: 20px; bottom: 20px; font-family: Arial, sans-serif;">
    <div style="font-weight:bold; margin-bottom:5px;">Legend</div>
    <ul style="list-style:none; padding:0; margin:0;">{legend_items}</ul>
</div>
<style> li span {{ display: inline-block; width: 14px; height: 14px; margin-right: 8px; border: 1px solid #999; }} </style>
{{% endmacro %}}
'''

macro = MacroElement(); macro._template = Template(title_html); m.get_root().add_child(macro)
folium.LayerControl(collapsed=False).add_to(m)
m.save("index.html")
