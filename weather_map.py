import requests
import geopandas as gpd
import folium
from folium.plugins import LocateControl
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

# 2. Initialize Map (Using Google Hybrid for built-in County Lines)
m = folium.Map(location=[35.2, -76.2], zoom_start=7, tiles=None)
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                attr='Google', name='Satellite with Borders/Cities').add_to(m)
folium.TileLayer('CartoDB positron', name='Light Mode').add_to(m)
LocateControl(auto_start=False).add_to(m)

# 3. Fetch Data
marine_zones = "AMZ130,AMZ131,AMZ135,AMZ136,AMZ137,AMZ150,AMZ152,AMZ154,AMZ156,AMZ158,AMZ170,AMZ172,AMZ174,ANZ083,ANZ089,ANZ800,ANZ899"
urls = ["https://api.weather.gov/alerts/active?area=NC", f"https://api.weather.gov/alerts/active?zone={marine_zones}"]

all_features = []
active_event_types = {}
headers = {'User-Agent': 'NCWeatherMap/1.0 (your-email@example.com)'}

for url in urls:
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            features = res.json().get('features', [])
            for f in features:
                # TRY to get geometry, but DON'T crash if it fails
                if not f.get('geometry'):
                    try:
                        affected = f['properties'].get('affectedZones', [])
                        if affected:
                            z_res = requests.get(affected[0], headers=headers, timeout=5)
                            if z_res.status_code == 200:
                                f['geometry'] = z_res.json().get('geometry')
                    except:
                        continue # Skip this specific alert's shape and move to next

                if f.get('geometry'):
                    all_features.append(f)
                    etype = f['properties'].get('event', 'Alert')
                    active_event_types[etype] = get_color(etype)
    except Exception as e:
        print(f"URL skip: {e}")

# 4. Final Map Construction
if all_features:
    try:
        gdf = gpd.GeoDataFrame.from_features(all_features).set_crs(epsg=4326)
        folium.GeoJson(gdf, name="Active Alerts",
            style_function=lambda x: {'fillColor': get_color(x['properties']['event']), 'color': 'black', 'weight': 1, 'fillOpacity': 0.5},
            tooltip=folium.GeoJsonTooltip(fields=['event', 'headline'], aliases=['Alert:', 'Details:'])
        ).add_to(m)
    except:
        pass

# 5. Legend/Title UI
legend_items = "".join([f'<li><span style="background:{c}; border:1px solid black; display:inline-block; width:12px; height:12px; margin-right:5px;"></span>{n}</li>' for n, c in sorted(active_event_types.items())])
macro_html = f'''
{{% macro html(this, kwargs) %}}
<div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index:9999; background:white; padding:10px; border:2px solid black; border-radius:5px; text-align:center;">
    <b>North Carolina Weather Alerts</b><br><small>Updated: {local_time}</small>
</div>
<div style="position: fixed; bottom: 30px; right: 10px; z-index:9999; background:white; padding:10px; border:2px solid grey; border-radius:5px; font-size:12px;">
    <b>Legend</b><ul style="list-style:none; padding:0; margin:0;">{legend_items or "<li>No alerts found</li>"}</ul>
</div>
{{% endmacro %}}
'''
macro = MacroElement(); macro._template = Template(macro_html); m.get_root().add_child(macro)
folium.LayerControl(position='topright', collapsed=False).add_to(m)
m.save("index.html")
