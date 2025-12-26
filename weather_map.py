import requests
import geopandas as gpd
import folium
from folium.plugins import LocateControl
from datetime import datetime, timezone
import pytz
from branca.element import Template, MacroElement

# 1. Setup Time
utc_now = datetime.now(timezone.utc)
local_time = utc_now.astimezone(pytz.timezone('US/Eastern')).strftime('%I:%M %p %Z')

# 2. Map Setup
m = folium.Map(location=[35.2, -76.2], zoom_start=7, tiles=None)

# Using Google Hybrid: It is the most robust way to see borders/cities on satellite
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                attr='Google', name='Satellite (Borders & Cities)').add_to(m)
folium.TileLayer('CartoDB positron', name='Light Mode').add_to(m)

# 3. FIX: Add NC County Outlines via a reliable, permanent URL
# This source is part of a highly-stable project and rarely fails.
counties_url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries/USA/NC.json"
folium.GeoJson(counties_url, name="County Lines", 
               style_function=lambda x: {'color': '#444444', 'weight': 1, 'fillOpacity': 0}).add_to(m)

# 4. FETCH DATA - Updated 2025 Marine Codes
# Includes the new 60NM offshore extension zones
marine_zones = "AMZ150,AMZ152,AMZ154,AMZ156,AMZ158,AMZ130,AMZ131,AMZ135,ANZ680,ANZ682,ANZ684,ANZ686"
urls = ["https://api.weather.gov/alerts/active?area=NC", f"https://api.weather.gov/alerts/active?zone={marine_zones}"]

all_features = []
active_events = {}
headers = {'User-Agent': 'NCWeatherMap/2.0'}

for url in urls:
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            for f in res.json().get('features', []):
                # Ensure we have a shape to draw
                if not f.get('geometry'):
                    zones = f['properties'].get('affectedZones', [])
                    if zones:
                        z_res = requests.get(zones[0], headers=headers, timeout=5)
                        f['geometry'] = z_res.json().get('geometry')
                
                if f.get('geometry'):
                    all_features.append(f)
                    active_events[f['properties']['event']] = "#3498db" if 'Small Craft' in f['properties']['event'] else "#e67e22"
    except: continue

if all_features:
    folium.GeoJson(gpd.GeoDataFrame.from_features(all_features).set_crs(epsg=4326),
                   style_function=lambda x: {'fillColor': '#3498db' if 'Small Craft' in x['properties']['event'] else '#e67e22', 
                                             'color': 'black', 'weight': 1, 'fillOpacity': 0.5},
                   tooltip=folium.GeoJsonTooltip(fields=['event', 'headline'])).add_to(m)

# 5. UI: Title & Legend
legend_html = "".join([f'<li><span style="background:{c}; border:1px solid black; display:inline-block; width:12px; height:12px; margin-right:5px;"></span>{n}</li>' for n, c in active_events.items()])
macro_html = f'''
{{% macro html(this, kwargs) %}}
<div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index:9999; background:white; padding:10px; border:2px solid black; border-radius:5px; text-align:center;">
    <b>North Carolina Weather Alerts</b><br><small>Updated: {local_time}</small>
</div>
<div style="position: fixed; bottom: 30px; right: 10px; z-index:9999; background:white; padding:10px; border:1px solid grey; border-radius:5px; font-size:12px;">
    <b>Legend</b><ul style="list-style:none; padding:0; margin:0;">{legend_html or "<li>No alerts</li>"}</ul>
</div>
{{% endmacro %}}
'''
macro = MacroElement(); macro._template = Template(macro_html); m.get_root().add_child(macro)
folium.LayerControl().add_to(m)
m.save("index.html")
