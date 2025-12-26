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
m = folium.Map(location=[35.5, -76.0], zoom_start=7, tiles=None)
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                attr='Google', name='Satellite Hybrid').add_to(m)
folium.TileLayer('CartoDB positron', name='Light Street Map').add_to(m)
LocateControl(auto_start=False, flyTo=True).add_to(m)

# 3. Load County Borders
county_file = "nc_counties.json"
if os.path.exists(county_file):
    with open(county_file, 'r') as f:
        folium.GeoJson(json.load(f), name="County Lines",
                       style_function=lambda x: {'color': '#666666', 'weight': 1.2, 'fillOpacity': 0}).add_to(m)

# 4. FETCH DATA (Exhaustive list to close Carova & Hatteras gaps)
marine_list = [
    "ANZ633", "ANZ658","ANZ678",
    "AMZ230", "AMZ131","AMZ231","AMZ150","AMZ170",
    "AMZ135","AMZ152","AMZ172","AMZ136","AMZ137",
    "AMZ156","AMZ154","AMZ174""AMZ176","AMZ158","AMZ178",
    "AMZ250","AMZ270"
]
marine_zones = ",".join(marine_list)

urls = [
    "https://api.weather.gov/alerts/active?area=NC,VA,SC", 
    f"https://api.weather.gov/alerts/active?zone={marine_zones}"
]

all_features = []
active_events = {}
headers = {'User-Agent': 'NCWeatherMap/13.0'}

def get_color(event_name):
    e = event_name.lower()
    if 'small craft' in e: return '#2980b9'  # Marine Blue
    if 'gale' in e: return '#8e44ad'         # Purple
    if 'winter' in e or 'snow' in e or 'blizzard' in e: return '#9b59b6' # Winter Purple
    if 'ice' in e or 'freeze' in e or 'frost' in e: return '#1abc9c' # Cold Teal
    if 'heat' in e: return '#e74c3c'         # Heat Red
    if 'wind' in e: return '#7f8c8d'         # Wind Grey
    if 'flood' in e: return '#27ae60'        # Flood Green
    return '#e67e22' # Severe Orange

for url in urls:
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            for f in res.json().get('features', []):
                ename = f['properties']['event']
                active_events[ename] = get_color(ename)
                
                # CRITICAL: If geometry is missing, fetch the actual zone shape
                if not f.get('geometry'):
                    z_links = f['properties'].get('affectedZones', [])
                    if z_links:
                        z_res = requests.get(z_links[0], headers=headers, timeout=5)
                        if z_res.status_code == 200:
                            f['geometry'] = z_res.json().get('geometry')
                
                if f.get('geometry'):
                    all_features.append(f)
    except: continue

# 5. Add Alerts
if all_features:
    folium.GeoJson(gpd.GeoDataFrame.from_features(all_features).set_crs(epsg=4326),
                   name="Active Hazards",
                   style_function=lambda x: {
                       'fillColor': get_color(x['properties']['event']),
                       'color': 'black', 'weight': 1, 'fillOpacity': 0.5
                   },
                   tooltip=folium.GeoJsonTooltip(fields=['event', 'headline'])).add_to(m)

# 6. UI: Clean Legend
legend_items = "".join([f'<li><span style="background:{c}; border:1px solid black; display:inline-block; width:12px; height:12px; margin-right:5px;"></span>{n}</li>' for n, c in sorted(active_events.items())])
macro_html = f'''
{{% macro html(this, kwargs) %}}
<div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index:9999; background:white; padding:10px; border:2px solid black; border-radius:5px; text-align:center; font-family:Arial; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
    <b>Regional Weather Alerts</b><br><small>Updated: {local_time}</small>
</div>
<div style="position: fixed; bottom: 30px; right: 10px; z-index:9999; background:white; padding:10px; border:1px solid grey; border-radius:5px; font-family:Arial; font-size:12px; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
    <b>Active Hazards</b><ul style="list-style:none; padding:0; margin:0;">{legend_items or "<li>No active alerts</li>"}</ul>
</div>
{{% endmacro %}}
'''
legend = MacroElement(); legend._template = Template(macro_html); m.get_root().add_child(legend)
folium.LayerControl(collapsed=False).add_to(m)
m.save("index.html")
