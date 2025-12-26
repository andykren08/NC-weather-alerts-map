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
    if 'small craft' in event: return '#3498db' # Blue
    if 'gale' in event: return '#8e44ad'        # Purple
    if 'flood' in event: return '#2ecc71'       # Green
    if 'tornado' in event: return '#e74c3c'     # Red
    if 'wind' in event: return '#d35400'        # Dark Orange
    return '#e67e22'                            # Orange

# 2. Initialize Map
m = folium.Map(location=[35.2, -79.0], zoom_start=7, tiles='CartoDB positron')
LocateControl(auto_start=False).add_to(m)

# 3. Fetch Data - NC Land AND all Coastal Marine Offices
# MHX = Newport/Morehead City, ILM = Wilmington, AKQ = Wakefield (covers NE NC)
urls = [
    "https://api.weather.gov/alerts/active?area=NC",
    "https://api.weather.gov/alerts/active?wfo=MHX",
    "https://api.weather.gov/alerts/active?wfo=ILM",
    "https://api.weather.gov/alerts/active?wfo=AKQ"
]

all_features = []
active_event_types = {}
seen_ids = set() # Prevent double-counting the same alert
headers = {'User-Agent': 'NCWeatherMap/1.0 (contact@example.com)'}

for url in urls:
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            for f in res.json().get('features', []):
                alert_id = f['properties'].get('id')
                if alert_id not in seen_ids and f.get('geometry'):
                    all_features.append(f)
                    seen_ids.add(alert_id)
                    etype = f['properties'].get('event', 'Alert')
                    active_event_types[etype] = get_color(etype)
    except: continue

# 4. Add Weather Layer
if all_features:
    gdf = gpd.GeoDataFrame.from_features(all_features).set_crs(epsg=4326)
    folium.GeoJson(gdf, name="Weather Alerts",
        style_function=lambda x: {
            'fillColor': get_color(x['properties']['event']),
            'color': 'black', 'weight': 1, 'fillOpacity': 0.6
        },
        tooltip=folium.GeoJsonTooltip(fields=['event', 'headline'], aliases=['Alert:', 'Details:'])
    ).add_to(m)

# 5. Add Custom Title and Legend HTML
legend_items = "".join([f'<li><span style="background:{color}; border:1px solid black; display:inline-block; width:12px; height:12px; margin-right:5px;"></span>{name}</li>' for name, color in sorted(active_event_types.items())])
if not legend_items: legend_items = "<li><i>No active alerts</i></li>"

macro_html = f'''
{{% macro html(this, kwargs) %}}
<div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index:9999; background:white; padding:10px; border:2px solid black; border-radius:5px; font-family:Arial; text-align:center; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
    <b>North Carolina Weather Alerts</b><br>
    <small>Updated: {local_time}</small>
</div>
<div style="position: fixed; bottom: 30px; right: 10px; z-index:9999; background:white; padding:10px; border:2px solid grey; border-radius:5px; font-family:Arial; font-size:12px; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
    <b>Legend</b><ul style="list-style:none; padding:0; margin:0; max-height: 200px; overflow-y: auto;">{legend_items}</ul>
</div>
{{% endmacro %}}
'''
macro = MacroElement(); macro._template = Template(macro_html); m.get_root().add_child(macro)

m.save("index.html")
