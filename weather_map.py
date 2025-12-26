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
folium.TileLayer('CartoDB positron', name='Light Mode').add_to(m)

# 3. FIX: Self-Hosted County Borders (Simplified)
county_file = "nc_counties.json"
if os.path.exists(county_file):
    with open(county_file, 'r') as f:
        data = json.load(f)
    folium.GeoJson(data, name="County Lines",
                   style_function=lambda x: {'color': '#666666', 'weight': 1.5, 'fillOpacity': 0}).add_to(m)

# 4. FIX: Marine Advisories (Broadened for VA and SC Coasts)
# ANZ = Wakefield (VA), AMZ = NC/SC
marine_zones = "ANZ633,ANZ634,ANZ656,ANZ658,AMZ130,AMZ131,AMZ135,AMZ150,AMZ152,AMZ154,AMZ156,AMZ158,AMZ250,AMZ252,AMZ254,AMZ256"
urls = ["https://api.weather.gov/alerts/active?area=NC,VA,SC", f"https://api.weather.gov/alerts/active?zone={marine_zones}"]

all_features = []
alert_list = []
headers = {'User-Agent': 'NCWeatherMap/7.0'}

for url in urls:
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            features = res.json().get('features', [])
            for f in features:
                props = f['properties']
                # Catch Small Craft, Gale, etc.
                alert_list.append({'event': props['event'], 'area': props['areaDesc']})
                
                if not f.get('geometry'):
                    z_url = props.get('affectedZones', [None])[0]
                    if z_url:
                        z_data = requests.get(z_url, headers=headers).json()
                        f['geometry'] = z_data.get('geometry')
                
                if f.get('geometry'):
                    all_features.append(f)
    except: continue

# 5. Add Alerts to Map
if all_features:
    folium.GeoJson(gpd.GeoDataFrame.from_features(all_features).set_crs(epsg=4326),
                   style_function=lambda x: {
                       'fillColor': '#3498db' if 'Small Craft' in x['properties']['event'] else '#e67e22',
                       'color': 'black', 'weight': 1, 'fillOpacity': 0.5
                   },
                   tooltip=folium.GeoJsonTooltip(fields=['event', 'headline'])).add_to(m)

# 6. FIX: Custom UI (Corrected MacroElement Usage)
table_rows = "".join([f"<tr><td style='border-bottom:1px solid #ddd; padding:2px;'>{a['event']}</td><td style='border-bottom:1px solid #ddd; padding:2px;'>{a['area']}</td></tr>" for a in alert_list[:8]])
macro_html = f'''
{{% macro html(this, kwargs) %}}
<div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index:9999; background:white; padding:10px; border:2px solid black; border-radius:5px; text-align:center; font-family:Arial; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
    <b>Coastal Weather Monitor</b><br><small>Updated: {local_time}</small>
</div>
<div style="position: fixed; bottom: 30px; left: 20px; z-index:9999; background:white; padding:10px; border:1px solid grey; border-radius:5px; font-family:Arial; font-size:10px; max-width: 320px; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
    <b>North Carolina Weather Alerts</b>
    <table style="width:100%; border-collapse: collapse; margin-top:5px;">
        <tr style="background:#f2f2f2;"><th>Event</th><th>Area</th></tr>
        {table_rows or "<tr><td colspan='2'>No alerts found</td></tr>"}
    </table>
</div>
{{% endmacro %}}
'''

# Corrected way to add the Macro
legend = MacroElement()
legend._template = Template(macro_html)
m.get_root().add_child(legend)

folium.LayerControl(collapsed=False).add_to(m)
m.save("index.html")
