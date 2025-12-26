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
                attr='Google', name='Satellite Hybrid (Built-in Borders)').add_to(m)
folium.TileLayer('CartoDB positron', name='Light Mode').add_to(m)

# 3. County Loading (Self-Hosted Fix)
county_file = "nc_counties.json"
if os.path.exists(county_file):
    folium.GeoJson(county_file, name="County Lines",
                   style_function=lambda x: {'color': '#555555', 'weight': 1, 'fillOpacity': 0}).add_to(m)

# 4. Fetching Land & Sea Data (NC, VA, SC)
marine_zones = "ANZ633,ANZ634,ANZ656,ANZ658,AMZ130,AMZ131,AMZ135,AMZ150,AMZ152,AMZ154,AMZ156,AMZ158,AMZ250,AMZ252"
urls = ["https://api.weather.gov/alerts/active?area=NC,VA,SC", f"https://api.weather.gov/alerts/active?zone={marine_zones}"]

all_features = []
alert_list = [] # For our new table
headers = {'User-Agent': 'NCWeatherMap/6.0'}

for url in urls:
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            features = res.json().get('features', [])
            for f in features:
                props = f['properties']
                # Save to list for the table
                alert_list.append({'event': props['event'], 'area': props['areaDesc']})
                
                # Ensure geometry for the map
                if not f.get('geometry'):
                    z_url = props.get('affectedZones', [None])[0]
                    if z_url:
                        f['geometry'] = requests.get(z_url, headers=headers).json().get('geometry')
                
                if f.get('geometry'):
                    all_features.append(f)
    except: continue

# 5. Add Map Layers
if all_features:
    folium.GeoJson(gpd.GeoDataFrame.from_features(all_features).set_crs(epsg=4326),
                   style_function=lambda x: {'fillColor': '#3498db' if 'Small Craft' in x['properties']['event'] else '#e67e22',
                                             'color': 'black', 'weight': 1, 'fillOpacity': 0.5},
                   tooltip=folium.GeoJsonTooltip(fields=['event', 'headline'])).add_to(m)

# 6. UI: Clean Legend & Alert Table
table_rows = "".join([f"<tr><td>{a['event']}</td><td>{a['area']}</td></tr>" for a in alert_list[:10]]) # Show top 10
macro_html = f'''
{{% macro html(this, kwargs) %}}
<div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index:9999; background:white; padding:10px; border:2px solid black; border-radius:5px; text-align:center; font-family:Arial;">
    <b>Coastal Alert Monitor</b><br><small>Updated: {local_time}</small>
</div>
<div style="position: fixed; bottom: 20px; left: 20px; z-index:9999; background:white; padding:10px; border:1px solid grey; border-radius:5px; font-family:Arial; font-size:11px; max-width: 300px;">
    <b>North Carolina Active Alerts (Top 10)</b>
    <table style="width:100%; border-collapse: collapse;">{table_rows or "<tr><td>No active alerts</td></tr>"}</table>
</div>
{{% endmacro %}}
'''
m.get_root().add_child(MacroElement().from_template(Template(macro_html)))
folium.LayerControl(collapsed=False).add_to(m)
m.save("index.html")
