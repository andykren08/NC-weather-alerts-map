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

# 4. FETCH DATA 
# Fixed commas to prevent string concatenation errors
marine_list = [
    "ANZ633", "ANZ658", "ANZ678", "AMZ230", "AMZ131", "AMZ231", 
    "AMZ150", "AMZ170", "AMZ135", "AMZ152", "AMZ172", "AMZ136", 
    "AMZ137", "AMZ156", "AMZ154", "AMZ174", "AMZ176", "AMZ158", 
    "AMZ178", "AMZ250", "AMZ270"
]
marine_zones = ",".join(marine_list)

urls = [
    "https://api.weather.gov/alerts/active?area=NC,VA,SC", 
    f"https://api.weather.gov/alerts/active?zone={marine_zones}"
]

all_features = []
seen_ids = set() # Prevent duplicate alerts
active_events = {}
headers = {'User-Agent': 'NCWeatherMap/13.0'}

for url in urls:
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200: continue
        
        features = res.json().get('features', [])
        for f in features:
            alert_id = f['properties'].get('id')
            if alert_id in seen_ids: continue
            seen_ids.add(alert_id)

            ename = f['properties']['event']
            active_events[ename] = get_color(ename)
            
            # IMPROVED GEOMETRY LOGIC
            # If geometry is null, we must fetch the shape from the first affected zone
            if not f.get('geometry') or f['geometry'] is None:
                z_links = f['properties'].get('affectedZones', [])
                if z_links:
                    try:
                        # Fetching the actual polygon for the marine zone (e.g., AMZ154)
                        z_res = requests.get(z_links[0], headers=headers, timeout=5)
                        if z_res.status_code == 200:
                            f['geometry'] = z_res.json().get('geometry')
                    except Exception as e:
                        print(f"Error fetching zone geometry: {e}")
            
            if f.get('geometry'):
                all_features.append(f)
    except Exception as e:
        print(f"Request error: {e}")
        continue

# 5. Add Alerts
if all_features:
    # Use GeoDataFrame to handle the geometry collection properly
    gdf = gpd.GeoDataFrame.from_features(all_features).set_crs(epsg=4326)
    
    folium.GeoJson(
        gdf,
        name="Active Hazards",
        style_function=lambda x: {
            'fillColor': get_color(x['properties']['event']),
            'color': 'black', 
            'weight': 1, 
            'fillOpacity': 0.6 # Increased slightly for better visibility over water
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['event', 'headline'],
            aliases=['Alert:', 'Details:'],
            localize=True
        )
    ).add_to(m)
m.save("index.html")
