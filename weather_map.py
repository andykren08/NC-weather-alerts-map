import requests
import geopandas as gpd
import folium
from folium.plugins import LocateControl
import pandas as pd
from datetime import datetime, timezone
import pytz
from branca.element import Template, MacroElement

# 1. Setup Time and Colors
utc_now = datetime.now(timezone.utc)
local_time = utc_now.astimezone(pytz.timezone('US/Eastern')).strftime('%I:%M %p %Z')

def get_color(event):
    event = event.lower()
    if 'small craft' in event: return '#3498db'
    if 'gale' in event: return '#8e44ad'
    if 'flood' in event: return '#2ecc71'
    if 'tornado' in event: return '#e74c3c'
    return '#e67e22'

# 2. Initialize Map
m = folium.Map(location=[35.2, -76.2], zoom_start=7, tiles=None)

# Add Better Basemaps (Including Hybrid Satellite with Labels)
folium.TileLayer('CartoDB positron', name='Light Mode (Labels Only)').add_to(m)
folium.TileLayer('OpenStreetMap', name='Detailed Street Map').add_to(m)
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Satellite (No Labels)'
).add_to(m)
folium.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
    attr='Google',
    name='Satellite Hybrid (Borders & Cities)'
).add_to(m)

LocateControl(auto_start=False, flyTo=True).add_to(m)

# 3. Fetch Data - Massive Marine Zone List
# Added even more coastal and offshore codes to prevent missing alerts
marine_zones = "AMZ130,AMZ131,AMZ135,AMZ136,AMZ137,AMZ150,AMZ152,AMZ154,AMZ156,AMZ158,AMZ170,AMZ172,AMZ174,ANZ083,ANZ084,ANZ089,ANZ430,ANZ431"
urls = [
    "https://api.weather.gov/alerts/active?area=NC",
    f"https://api.weather.gov/alerts/active?zone={marine_zones}"
]

all_features = []
active_event_types = {}
headers = {'User-Agent': 'NCWeatherMap/1.0 (contact@example.com)'}

for url in urls:
    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code == 200:
            for f in res.json().get('features', []):
                # Deep geometry check for marine polygons
                if not f.get('geometry'):
                    zones = f['properties'].get('affectedZones', [])
                    if zones:
                        z_res = requests.get(zones[0], headers=headers, timeout=10)
                        if z_res.status_code == 200:
                            f['geometry'] = z_res.json().get('geometry')
                
                if f.get('geometry'):
                    all_features.append(f)
                    etype = f['properties'].get('event', 'Alert')
                    active_event_types[etype] = get_color(etype)
    except: continue

# 4. Add Layers
if all_features:
    gdf = gpd.GeoDataFrame.from_features(all_features).set_crs(epsg=4326)
    folium.GeoJson(gdf, name="Active Alerts",
        style_function=lambda x: {'fillColor': get_color(x['properties']['event']), 'color': 'black', 'weight': 1, 'fillOpacity': 0.6},
        tooltip=folium.GeoJsonTooltip(fields=['event', 'headline'], aliases=['Alert:', 'Details:'])
    ).add_to(m)

# 5. Legend & Title
legend_items = "".join([f'<li><span style="background:{color}; border:1px solid black; display:inline-block; width:12px; height:12px; margin-right:5px;"></span>{name}</li>' for name, color in sorted(active_event_types.items())])
if not legend_items: legend_items = "<li><i>No active alerts</i></li>"

macro_html = f'''
{{% macro html(this, kwargs) %}}
<div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index:9999; background:white; padding:10px; border:2px solid black; border-radius:5px; font-family:Arial; text-align:center; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
    <b>North Carolina Weather Alerts</b><br><small>Updated: {local_time}</small>
</div>
<div style="position: fixed; bottom: 30px; right: 10px; z-index:9999; background:white; padding:10px; border:2px solid grey; border-radius:5px; font-family:Arial; font-size:12px; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
    <b>Legend</b><ul style="list-style:none; padding:0; margin:0;">{legend_items}</ul>
</div>
{{% endmacro %}}
'''
macro = MacroElement(); macro._template = Template(macro_html); m.get_root().add_child(macro)
folium.LayerControl(position='topright', collapsed=False).add_to(m)

m.save("index.html")
