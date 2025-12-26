import requests
import geopandas as gpd
import folium
from folium.plugins import LocateControl
import os
from datetime import datetime, timezone
import pytz
from branca.element import Template, MacroElement

# 1. Time Setup
utc_now = datetime.now(timezone.utc)
local_time = utc_now.astimezone(pytz.timezone('US/Eastern')).strftime('%I:%M %p %Z')

# 2. Map Setup
m = folium.Map(location=[35.2, -76.2], zoom_start=7, tiles=None)

# Robust Hybrid Satellite (Borders are part of the image)
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                attr='Google', name='Satellite Hybrid (Borders)').add_to(m)
folium.TileLayer('CartoDB positron', name='Light Street Map').add_to(m)

# 3. FIX: Local County Loading with Path Safety
# We use os.path.join to ensure GitHub Actions finds the file in the current folder
base_path = os.path.dirname(os.path.abspath(__file__))
county_path = os.path.join(base_path, "nc_counties.json")

if os.path.exists(county_path):
    folium.GeoJson(
        county_path,
        name="NC County Borders",
        style_function=lambda x: {'color': '#444444', 'weight': 1.5, 'fillOpacity': 0},
        z_index=10
    ).add_to(m)

# 4. FIX: Expanded Marine Zones (Includes VA and SC coastal zones)
# Added ANZ600s (VA/NC border) and AMZ200s (SC border)
marine_zones = (
    "ANZ633,ANZ634,ANZ656,ANZ658,"  # VA/NC Border & Currituck
    "AMZ130,AMZ131,AMZ135,AMZ136,AMZ137," # NC Sounds
    "AMZ150,AMZ152,AMZ154,AMZ156,AMZ158," # NC Coastal
    "AMZ250,AMZ252,AMZ254,AMZ256" # NC/SC Border & SC Coastal
)

urls = [
    "https://api.weather.gov/alerts/active?area=NC,VA,SC", # Check all 3 states
    f"https://api.weather.gov/alerts/active?zone={marine_zones}"
]

all_features = []
active_events = {}
headers = {'User-Agent': 'NCWeatherMap/4.0 (your-email@example.com)'}

for url in urls:
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            for f in res.json().get('features', []):
                # Ensure we have a geometry
                if not f.get('geometry'):
                    try:
                        z_url = f['properties'].get('affectedZones', [None])[0]
                        if z_url:
                            f['geometry'] = requests.get(z_url, headers=headers).json().get('geometry')
                    except: continue
                
                if f.get('geometry'):
                    event_name = f['properties']['event']
                    all_features.append(f)
                    active_events[event_name] = "#3498db" if 'Small Craft' in event_name else "#e67e22"
    except: continue

# 5. Add Weather Layer
if all_features:
    folium.GeoJson(
        gpd.GeoDataFrame.from_features(all_features).set_crs(epsg=4326),
        name="Active Weather Alerts",
        style_function=lambda x: {
            'fillColor': "#3498db" if 'Small Craft' in x['properties']['event'] else "#e67e22",
            'color': 'black', 'weight': 1, 'fillOpacity': 0.5
        },
        tooltip=folium.GeoJsonTooltip(fields=['event', 'headline'])
    ).add_to(m)

# 6. FIX: Legend without the "Macro" text in Layer Control
legend_html = "".join([f'<li><span style="background:{c}; border:1px solid black; display:inline-block; width:12px; height:12px; margin-right:5px;"></span>{n}</li>' for n, c in active_events.items()])
macro_html = f'''
{{% macro html(this, kwargs) %}}
<div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index:9999; background:white; padding:10px; border:2px solid black; border-radius:5px; text-align:center; font-family: Arial;">
    <b>Coastal Weather Monitor</b><br><small>Updated: {local_time}</small>
</div>
<div style="position: fixed; bottom: 30px; right: 10px; z-index:9999; background:white; padding:10px; border:1px solid grey; border-radius:5px; font-size:12px; font-family: Arial;">
    <b>Legend</b><ul style="list-style:none; padding:0; margin:0;">{legend_html or "<li>No alerts</li>"}</ul>
</div>
{{% endmacro %}}
'''

# We add the MacroElement but do NOT give it a name to prevent it showing in the LayerControl
macro = MacroElement()
macro._template = Template(macro_html)
m.get_root().add_child(macro)

# Add LayerControl last
folium.LayerControl(position='topright', collapsed=False).add_to(m)
m.save("index.html")
