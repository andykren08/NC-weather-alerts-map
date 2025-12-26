import requests
import geopandas as gpd
import folium
from folium.plugins import LocateControl
import os
import json
from datetime import datetime, timezone
import pytz
from branca.element import Template, MacroElement

# 1. Setup Time
utc_now = datetime.now(timezone.utc)
local_time = utc_now.astimezone(pytz.timezone('US/Eastern')).strftime('%I:%M %p %Z')

# 2. Map Setup
m = folium.Map(location=[35.2, -76.2], zoom_start=7, tiles=None)

# High-Res Satellite with Labels (Hybrid)
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                attr='Google', name='Satellite Hybrid').add_to(m)
folium.TileLayer('CartoDB positron', name='Light Street Map').add_to(m)

# Add "Locate Me" Button
LocateControl(auto_start=False, flyTo=True).add_to(m)

# 3. Load Local County Borders
county_file = "nc_counties.json"
if os.path.exists(county_file):
    with open(county_file, 'r') as f:
        data = json.load(f)
    folium.GeoJson(data, name="County Lines",
                   style_function=lambda x: {'color': '#666666', 'weight': 1.2, 'fillOpacity': 0}).add_to(m)

# 4. Fetch Land & Sea Data (NC, VA, SC)
marine_zones = "ANZ633,ANZ634,ANZ656,ANZ658,AMZ130,AMZ131,AMZ135,AMZ150,AMZ152,AMZ154,AMZ156,AMZ158,AMZ250,AMZ252,AMZ254,AMZ256"
urls = ["https://api.weather.gov/alerts/active?area=NC,VA,SC", f"https://api.weather.gov/alerts/active?zone={marine_zones}"]

all_features = []
active_events = {} # For the legend
headers = {'User-Agent': 'NCWeatherMap/8.0'}

for url in urls:
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            features = res.json().get('features', [])
            for f in features:
                props = f['properties']
                etype = props['event']
                
                # Assign colors for the legend
                if 'Small Craft' in etype: color = '#3498db'
                elif 'Gale' in etype: color = '#8e44ad'
                elif 'Flood' in etype: color = '#2ecc71'
                elif 'Tornado' in etype: color = '#e74c3c'
                else: color = '#e67e22'
                
                active_events[etype] = color
                
                if not f.get('geometry'):
                    z_url = props.get('affectedZones', [None])[0]
                    if z_url:
                        f['geometry'] = requests.get(z_url, headers=headers).json().get('geometry')
                
                if f.get('geometry'):
                    all_features.append(f)
    except: continue

# 5. Add Alerts to Map
if all_features:
    folium.GeoJson(gpd.GeoDataFrame.from_features(all_features).set_crs(epsg=4326),
                   name="Active Weather Alerts",
                   style_function=lambda x: {
                       'fillColor': '#3498db' if 'Small Craft' in x['properties']['event'] else '#e67e22',
                       'color': 'black', 'weight': 1, 'fillOpacity': 0.5
                   },
                   tooltip=folium.GeoJsonTooltip(fields=['event', 'headline'])).add_to(m)

# 6. UI: Floating Title & Color-Coded Legend
legend_items = "".join([f'<li><span style="background:{c}; border:1px solid black; display:inline-block; width:12px; height:12px; margin-right:5px;"></span>{n}</li>' for n, c in sorted(active_events.items())])

macro_html = f'''
{{% macro html(this, kwargs) %}}
<div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index:9999; background:white; padding:10px; border:2px solid black; border-radius:5px; text-align:center; font-family:Arial; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
    <b>North Carolina Weather Alerts</b><br><small>Updated: {local_time}</small>
</div>
<div style="position: fixed; bottom: 30px; right: 10px; z-index:9999; background:white; padding:10px; border:1px solid grey; border-radius:5px; font-family:Arial; font-size:12px; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
    <b>Legend</b><ul style="list-style:none; padding:0; margin:0;">{legend_items or "<li>No active alerts</li>"}</ul>
</div>
{{% endmacro %}}
'''

# Add legend to root to keep it out of the Layer Control list
legend = MacroElement()
legend._template = Template(macro_html)
m.get_root().add_child(legend)

folium.LayerControl(collapsed=False).add_to(m)
m.save("index.html")
