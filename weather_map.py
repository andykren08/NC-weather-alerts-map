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

# Basemaps
folium.TileLayer('CartoDB positron', name='Light Mode').add_to(m)
folium.TileLayer('OpenStreetMap', name='Detailed Street Map').add_to(m)
folium.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
    attr='Google',
    name='Satellite Hybrid (Borders & Cities)'
).add_to(m)

LocateControl(auto_start=False, flyTo=True).add_to(m)

# 3. Add Permanent County Boundaries
# Using a lightweight GeoJSON for NC Counties
county_url = "https://raw.githubusercontent.com/codeforamerica/click_container/master/NC_counties.geojson"
try:
    folium.GeoJson(
        county_url,
        name="NC County Borders",
        style_function=lambda x: {
            'color': '#555555',
            'weight': 1,
            'fillOpacity': 0
        },
        control=True
    ).add_to(m)
except:
    print("Could not load county lines")

# 4. Fetch Weather Data (Massive Marine Search)
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

# 5. Add Weather Alerts Layer
if all_features:
    gdf = gpd.GeoDataFrame.from_features(all_features).set_crs(epsg=4326)
    folium.GeoJson(gdf, name="Active Weather Alerts",
        style_function=lambda x: {
            'fillColor': get_color(x['properties']['event']),
            'color': 'black', 'weight': 1, 'fillOpacity': 0.6
        },
        tooltip=folium.GeoJsonTooltip(fields=['event', 'headline'], aliases=['Alert:', 'Details:'])
    ).add_to(m)

# 6. UI Elements
legend_items = "".join([f'<li><span style="background:{color}; border:1px solid black; display:inline-block; width:12px; height:12px; margin-right:5px;"></span>{name}</li>' for name, color in sorted(active_event_types.items())])
if not legend_items: legend_items = "<li><i>No active alerts</i></li>"

macro_html = f'''
{{% macro html(this, kwargs) %}}
<div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index:9999; background:white; padding:10px; border:2px solid black; border-radius:5px; font-family:Arial; text-align:center;">
    <b>North Carolina Weather Alerts</b><br><small>Updated: {local_time}</small>
</div>
<div style="position: fixed; bottom: 30px; right: 10px; z-index:9999; background:white; padding:10px; border:2px solid grey; border-radius:5px; font-family:Arial; font-size:12px;">
    <b>Legend</b><ul style="list-style:none; padding:0; margin:0;">{legend_items}</ul>
</div>
{{% endmacro %}}
'''
macro = MacroElement(); macro._template = Template(macro_html); m.get_root().add_child(macro)

folium.LayerControl(position='topright', collapsed=False).add_to(m)

m.save("index.html")
