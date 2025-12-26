import requests
import geopandas as gpd
import folium
from folium.plugins import LocateControl
import pandas as pd
from datetime import datetime, timezone
import pytz

def get_color(event):
    event = event.lower()
    if 'small craft' in event: return '#3498db'
    if 'gale' in event: return '#8e44ad'
    if 'flood' in event: return '#2ecc71'
    if 'tornado' in event: return '#e74c3c'
    return '#e67e22'

headers = {'User-Agent': 'NCWeatherMap/1.0 (contact@example.com)'}

# 1. Setup Time
utc_now = datetime.now(timezone.utc)
local_time = utc_now.astimezone(pytz.timezone('US/Eastern')).strftime('%I:%M %p %Z')

# 2. Initialize Map
m = folium.Map(location=[35.2, -79.0], zoom_start=7)
folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)
LocateControl(auto_start=False).add_to(m)

# 3. Fetch Data with Error Handling
all_features = []
active_events = {}

# NC Land & Marine Zones
urls = ["https://api.weather.gov/alerts/active?area=NC"]

for url in urls:
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for f in data.get('features', []):
                if f.get('geometry'):
                    all_features.append(f)
                    name = f['properties'].get('event', 'Alert')
                    active_events[name] = get_color(name)
    except Exception as e:
        print(f"Skipping a URL due to error: {e}")

# 4. Add to Map
if all_features:
    gdf = gpd.GeoDataFrame.from_features(all_features).set_crs(epsg=4326)
    folium.GeoJson(gdf, name="Alerts",
        style_function=lambda x: {'fillColor': get_color(x['properties']['event']), 'color': 'black', 'weight': 1, 'fillOpacity': 0.5},
        tooltip=folium.GeoJsonTooltip(fields=['event', 'headline'])
    ).add_to(m)

# 5. Save index.html
m.save("index.html")
print("Map saved successfully!")
