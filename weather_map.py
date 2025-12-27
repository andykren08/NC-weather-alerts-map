import requests
import geopandas as gpd
import folium
from folium.plugins import LocateControl
import os
import json
from datetime import datetime, timezone
import pytz
from branca.element import Template, MacroElement

# --- 1. CONFIGURATION & COLOR MAPPING ---
def get_color(event_name):
    event_name = event_name.lower()
    if 'small craft' in event_name: return '#FF8C00' 
    if 'gale' in event_name: return '#FF0000'         
    if 'hurricane' in event_name: return '#8B0000'    
    if 'rip current' in event_name: return '#40E0D0'  
    if 'beach hazards' in event_name: return '#00CED1' 
    if 'special marine' in event_name: return '#FFA500' 
    if 'tornado' in event_name: return '#FF00FF'      
    if 'severe thunderstorm' in event_name: return '#FFA500' 
    if 'flash flood' in event_name: return '#00FF00'  
    if 'flood' in event_name: return '#32CD32'        
    if 'winter' in event_name: return '#1E90FF'       
    if 'freeze' in event_name: return '#00BFFF'       
    if 'fire' in event_name or 'red flag' in event_name: return '#FF4500' 
    return '#808080' 

# --- 2. SETUP TIME ---
utc_now = datetime.now(timezone.utc)
local_time = utc_now.astimezone(pytz.timezone('US/Eastern')).strftime('%I:%M %p %Z')
date_str = utc_now.astimezone(pytz.timezone('US/Eastern')).strftime('%b %d, %Y')

# --- 3. MAP SETUP ---
m = folium.Map(location=[35.5, -79.5], zoom_start=8, tiles=None)

# --- BASEMAPS ---

# 1. Satellite Hybrid (Hidden on Load)
folium.TileLayer(
    'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
    attr='Google', 
    name='Satellite Hybrid', 
    overlay=False,
    control=True,
    show=False  # <--- Hidden
).add_to(m)

# 2. Terrain (Hidden on load)
folium.TileLayer(
    'https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
    attr='Google',
    name='Terrain',
    overlay=False,
    control=True,
    show=False # <--- Hidden
).add_to(m)

# 3. Street Map (Default: show=True)
folium.TileLayer(
    'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
    attr='Google',
    name='Street Map',
    overlay=False,
    control=True,
    show=True # <--- This one is visible on load
).add_to(m)

# 4. Light Gray Base (Hidden on load)
folium.TileLayer(
    'CartoDB positron', 
    name='Light Gray Base', 
    overlay=False,
    control=True,
    show=False # <--- Hidden
).add_to(m)

LocateControl(auto_start=False, flyTo=True).add_to(m)

# --- 4. LOAD COUNTY BORDERS ---
county_file = "nc_counties.json"
if os.path.exists(county_file):
    with open(county_file, 'r') as f:
        folium.GeoJson(
            json.load(f), 
            name="County Lines",
            style_function=lambda x: {
                'color': 'black',       
                'weight': 1.5, 
                'fillOpacity': 0,
                'dashArray': '5, 5',    
                'opacity': 0.7
            },
            overlay=True,
            control=True
        ).add_to(m)

# --- 5. FETCH DATA ---
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
seen_ids = set()
active_events = {} 
headers = {'User-Agent': 'NCWeatherMap/13.0'}
zone_geom_cache = {}

print("Fetching alerts...")

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
            
            if f.get('geometry'):
                all_features.append(f)
            else:
                z_links = f['properties'].get('affectedZones', [])
                for z_link in z_links:
                    geom = zone_geom_cache.get(z_link)
                    if not geom:
                        try:
                            z_res = requests.get(z_link, headers=headers, timeout=5)
                            if z_res.status_code == 200:
                                geom = z_res.json().get('geometry')
                                zone_geom_cache[z_link] = geom 
                        except Exception: pass
                    
                    if geom:
                        new_f = {
                            "type": "Feature",
                            "properties": f['properties'],
                            "geometry": geom
                        }
                        all_features.append(new_f)

    except Exception as e:
        print(f"Request error: {e}")
        continue

# --- 6. ADD ALERTS TO MAP ---
if all_features:
    gdf = gpd.GeoDataFrame.from_features(all_features).set_crs(epsg=4326)
    
    folium.GeoJson(
        gdf,
        name="Active Hazards",
        style_function=lambda x: {
            'fillColor': get_color(x['properties']['event']),
            'color': 'black', 
            'weight': 1, 
            'fillOpacity': 0.5
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['event', 'headline'],
            aliases=['Alert:', 'Details:'],
            localize=True,
            style="font-size: 15px; padding: 8px; max-width: 400px; color: black;"
        ),
        overlay=True,
        control=True
    ).add_to(m)

# --- 7. ADD LAYER CONTROL ---
folium.LayerControl(collapsed=True).add_to(m)

# --- 8. LEGEND & SAVE ---
legend_html_items = ""
if not active_events:
    legend_html_items = "<li><span style='margin-left:10px;'>No Active North Carolina Hazards</span></li>"
else:
    for event, color in active_events.items():
        legend_html_items += f"""
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="background:{color}; width: 15px; height: 15px; border: 1px solid black; margin-right: 8px; border-radius:3px;"></div>
            <span style="font-size:14px;">{event}</span>
        </div>
        """

template = f"""
{{% macro html(this, kwargs) %}}
<div id='maplegend' class='maplegend' 
    style='position: absolute; z-index:9999; border:2px solid grey; background-color:rgba(255, 255, 255, 0.9);
     border-radius:6px; padding: 10px; font-size:14px; right: 20px; bottom: 20px; width: 220px; box-shadow: 0 0 15px rgba(0,0,0,0.2);'>
    <div class='legend-title' style="font-weight: bold; margin-bottom: 5px; font-size: 18px;">Latest North Carolina Weather Hazards</div>
    <div style="font-size: 13px; color: #555; margin-bottom: 10px;">
        Updated: {date_str}<br>{local_time}
    </div>
    <div class='legend-scale'>
       {legend_html_items}
    </div>
</div>
<style type='text/css'>
  .maplegend a {{ color: #777; }}
  .maplegend a:hover {{ color: #555; }}
</style>
{{% endmacro %}}
"""

macro = MacroElement()
macro._template = Template(template)
m.get_root().add_child(macro)

m.save("index.html")
print("Map saved to index.html (Default: Satellite)")
