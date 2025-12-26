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
    if 'special marine' in event: return '#e74c3c' # Bright Red
    return '#e67e22'                            # Orange

# 2. Initialize Map with Basemap Options
m = folium.Map(location=[35.2, -76.2], zoom_start=7, tiles=None)

# Add Basemaps to the Switcher
folium.TileLayer('CartoDB positron', name='Light Mode (Best for Alerts)', control=True).add_to(m)
folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)
folium.TileLayer('CartoDB dark_matter', name='Dark Mode').add_to(m)
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Satellite View'
).add_to(m)

# Add "Find My Location" Button
LocateControl(auto_start=False, flyTo=True).add_to(m)

# 3. Fetch Data - NC Land and expanded Marine Zones
# Includes Sounds (AMZ), Coastal Waters (AMZ), and Offshore (ANZ)
nc_marine_zones = "AMZ130,AMZ131,AMZ135,AMZ136,AMZ137,AMZ150,AMZ152,AMZ154,AMZ156,AMZ158,ANZ083,ANZ084,ANZ089"
urls = [
    "https://api.weather.gov/alerts/active?area=NC",
    f"https://api.weather.gov/alerts/active?zone={nc_marine_zones}"
]

all_features = []
active_event_types = {}
headers = {'User-Agent': 'NCWeatherMap/1.0 (contact@example.com)'}

for url in urls:
    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code == 200:
            features = res.json().get('features', [])
            for f in features:
                # Deep geometry check: if shape is missing, try to fetch it from the zone link
                if not f.get('geometry'):
                    zones = f['properties'].get('affectedZones', [])
                    if zones:
                        zone_res = requests.get(zones[0], headers=headers, timeout=10)
                        if zone_res.status_code == 200:
                            f['geometry'] = zone_res.json().get('geometry')
                
                if f.get('geometry'):
                    all_features.append(f)
                    etype = f['properties'].get('event', 'Alert')
                    active_event_types[etype] = get_color(etype)
    except Exception as e:
        print(f"Error fetching: {e}")

# 4. Create Weather Layer
if all_features:
    gdf = gpd.GeoDataFrame.from_features(all_features).set_crs(epsg=4326)
    folium.GeoJson(gdf, name="Active Alerts",
        style_function=lambda x: {
            'fillColor': get_color(x['properties']['event']),
            'color': 'black', 'weight': 1, 'fillOpacity': 0.6
        },
        tooltip=folium.GeoJsonTooltip(fields=['event', 'headline'], aliases=['Alert:', 'Details:'])
    ).add_to(m)

# 5. UI Elements: Title, Legend, and Layer Control
legend_items = "".join([f'<li><span style="background:{color}; border:1px solid black; display:inline-block; width:12px; height:12px; margin-right:5px;"></span>{name}</li>' for name, color in sorted(active_event_types.items())])
if not legend_items: legend_items = "<li><i>No active alerts</i></li>"

macro_html = f'''
{{% macro html(this, kwargs) %}}
<div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index:9999; background:white; padding:10px; border:2px solid black; border-radius:5px; font-family:Arial; text-align:center; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
    <b>North Carolina Weather & Marine Alerts</b><br>
    <small>Updated: {local_time}</small>
</div>
<div style="position: fixed; bottom: 30px; right: 10px; z-index:9999; background:white; padding:10px; border:2px solid grey; border-radius:5px; font-family:Arial; font-size:12px; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
    <b>Legend</b><ul style="list-style:none; padding:0; margin:0;">{legend_items}</ul>
</div>
{{% endmacro %}}
'''
macro = MacroElement(); macro._template = Template(macro_html); m.get_root().add_child(macro)

# Add the Basemap Switcher (Layer Control)
folium.LayerControl(position='topright', collapsed=False).add_to(m)

m.save("index.html")
