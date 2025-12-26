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
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                attr='Google', name='Satellite Hybrid').add_to(m)
folium.TileLayer('CartoDB positron', name='Light Mode').add_to(m)
LocateControl(auto_start=False, flyTo=True).add_to(m)

# 3. Load County Borders
county_file = "nc_counties.json"
if os.path.exists(county_file):
    with open(county_file, 'r') as f:
        folium.GeoJson(json.load(f), name="County Lines",
                       style_function=lambda x: {'color': '#666666', 'weight': 1.2, 'fillOpacity': 0}).add_to(m)

# 4. Fetch Land & Sea Data (NC, VA, SC)
marine_zones = "ANZ633,ANZ634,ANZ656,ANZ658,AMZ130,AMZ131,AMZ135,AMZ150,AMZ152,AMZ154,AMZ156,AMZ158,AMZ250,AMZ252,AMZ254,AMZ256"
urls = ["https://api.weather.gov/alerts/active?area=NC,VA,SC", f"https://api.weather.gov/alerts/active?zone={marine_zones}"]

all_features = []
active_events = {}
headers = {'User-Agent': 'NCWeatherMap/9.0'}

def get_color(event_name):
    event_name = event_name.lower()
    if 'small craft' in event_name: return '#3498db'  # Blue
    if 'winter' in event_name or 'snow' in event_name or 'blizzard' in event_name: return '#9b59b6'  # Purple
    if 'wind' in event_name: return '#95a5a6' # Grey
    if 'heat' in event_name: return '#e74c3c' # Red
    if 'freeze' in event_name or 'frost' in event_name or 'cold' in event_name: return '#1abc9c' # Cyan
    if 'flood' in event_name: return '#2ecc71' # Green
    return '#e67e22' # Orange (Default/Severe)

for url in urls:
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            for f in res.json().get('features', []):
                ename = f['properties']['event']
                active_events[ename] = get_color(ename)
                
                if not f.get('geometry'):
                    z_url = f['properties'].get('affectedZones', [None])[0]
                    if z_url:
                        f['geometry'] = requests.get(z_url, headers=headers).json().get('geometry')
                
                if f.get('geometry'):
                    all_features.append(f)
    except: continue

# 5. Add Weather Layer
if all_features:
    folium.GeoJson(gpd.GeoDataFrame.from_features(all_features).set_crs(epsg=4326),
                   name="Active Weather Alerts",
                   style_function=lambda x: {
                       'fillColor': get_color(x['properties']['event']),
                       'color': 'black', 'weight': 1, 'fillOpacity': 0.5
                   },
                   tooltip=folium.GeoJsonTooltip(fields=['event', 'headline'])).add_to(m)

# 6. UI: Custom Legend
legend_items = "".join([f'<li><span style="background:{c}; border:1px solid black; display:inline-block; width:12px; height:12px; margin-right:5px;"></span>{n}</li>' for n, c in sorted(active_events.items())])
macro_html = f'''
{{% macro html(this, kwargs) %}}
<div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index:9999; background:white; padding:10px; border:2px solid black; border-radius:5px; text-align:center; font-family:Arial; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
    <b>Regional Weather Alerts</b><br><small>Updated: {local_time}</small>
</div>
<div style="position: fixed; bottom: 30px; right: 10px; z-index:9999; background:white; padding:10px; border:1px solid grey; border-radius:5px; font-family:Arial; font-size:12px; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
    <b>Legend</b><ul style="list-style:none; padding:0; margin:0;">{legend_items or "<li>No active alerts</li>"}</ul>
</div>
{{% endmacro %}}
'''
legend = MacroElement(); legend._template = Template(macro_html); m.get_root().add_child(legend)
folium.LayerControl(collapsed=False).add_to(m)
m.save("index.html")
