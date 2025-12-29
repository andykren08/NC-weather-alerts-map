import requests
import geopandas as gpd
import folium
from folium.plugins import LocateControl
import os
import json
from datetime import datetime, timezone
import pytz
from branca.element import Template, MacroElement
from folium.plugins import LocateControl, FloatImage  # <--- Added FloatImage

# --- 1. CONFIGURATION: NWS HAZARD DATA (Color & Priority) ---
# Source: https://www.weather.gov/help-map
# Priority: Lower number = Higher Importance. 
# We draw High Priority items LAST so they appear ON TOP.
HAZARD_DATA = {
    "Tsunami Warning": {"color": "#FD6347", "priority": 1},
    "Tornado Warning": {"color": "#FF0000", "priority": 2},
    "Extreme Wind Warning": {"color": "#FF8C00", "priority": 3},
    "Severe Thunderstorm Warning": {"color": "#FFA500", "priority": 4},
    "Flash Flood Warning": {"color": "#8B0000", "priority": 5},
    "Flash Flood Statement": {"color": "#8B0000", "priority": 6},
    "Severe Weather Statement": {"color": "#00FFFF", "priority": 7},
    "Shelter In Place Warning": {"color": "#FA8072", "priority": 8},
    "Evacuation Immediate": {"color": "#7FFF00", "priority": 9},
    "Civil Danger Warning": {"color": "#FFB6C1", "priority": 10},
    "Nuclear Power Plant Warning": {"color": "#4B0082", "priority": 11},
    "Radiological Hazard Warning": {"color": "#4B0082", "priority": 12},
    "Hazardous Materials Warning": {"color": "#4B0082", "priority": 13},
    "Fire Warning": {"color": "#A0522D", "priority": 14},
    "Civil Emergency Message": {"color": "#FFB6C1", "priority": 15},
    "Law Enforcement Warning": {"color": "#C0C0C0", "priority": 16},
    "Storm Surge Warning": {"color": "#B524F7", "priority": 17},
    "Hurricane Force Wind Warning": {"color": "#CD5C5C", "priority": 18},
    "Hurricane Warning": {"color": "#DC143C", "priority": 19},
    "Typhoon Warning": {"color": "#DC143C", "priority": 20},
    "Special Marine Warning": {"color": "#FFA500", "priority": 21},
    "Blizzard Warning": {"color": "#FF4500", "priority": 22},
    "Snow Squall Warning": {"color": "#C71585", "priority": 23},
    "Ice Storm Warning": {"color": "#8B008B", "priority": 24},
    "Winter Storm Warning": {"color": "#FF69B4", "priority": 25},
    "High Wind Warning": {"color": "#DAA520", "priority": 26},
    "Tropical Storm Warning": {"color": "#B22222", "priority": 27},
    "Storm Warning": {"color": "#9400D3", "priority": 28},
    "Tsunami Advisory": {"color": "#D2691E", "priority": 29},
    "Tsunami Watch": {"color": "#FF00FF", "priority": 30},
    "Avalanche Warning": {"color": "#1E90FF", "priority": 31},
    "Earthquake Warning": {"color": "#8B4513", "priority": 32},
    "Volcano Warning": {"color": "#2F4F4F", "priority": 33},
    "Ashfall Warning": {"color": "#A9A9A9", "priority": 34},
    "Coastal Flood Warning": {"color": "#228B22", "priority": 35},
    "Lakeshore Flood Warning": {"color": "#228B22", "priority": 36},
    "Flood Warning": {"color": "#00FF00", "priority": 37},
    "High Surf Warning": {"color": "#228B22", "priority": 38},
    "Dust Storm Warning": {"color": "#FFE4C4", "priority": 39},
    "Blowing Dust Warning": {"color": "#FFE4C4", "priority": 40},
    "Lake Effect Snow Warning": {"color": "#008B8B", "priority": 41},
    "Excessive Heat Warning": {"color": "#C71585", "priority": 42},
    "Tornado Watch": {"color": "#FFFF00", "priority": 43},
    "Severe Thunderstorm Watch": {"color": "#DB7093", "priority": 44},
    "Flash Flood Watch": {"color": "#2E8B57", "priority": 45},
    "Gale Warning": {"color": "#DDA0DD", "priority": 46},
    "Flood Watch": {"color": "#2E8B57", "priority": 47},
    "Hurricane Watch": {"color": "#FF00FF", "priority": 48},
    "Fire Weather Watch": {"color": "#FFDEAD", "priority": 49},
    "Extreme Cold Warning": {"color": "#0000FF", "priority": 50},
    "Wind Chill Warning": {"color": "#B0C4DE", "priority": 51},
    "Hard Freeze Warning": {"color": "#9400D3", "priority": 52},
    "Freeze Warning": {"color": "#483D8B", "priority": 53},
    "Red Flag Warning": {"color": "#FF1493", "priority": 54},
    "Storm Surge Watch": {"color": "#DB7093", "priority": 55},
    "Hurricane Force Wind Watch": {"color": "#9932CC", "priority": 56},
    "Typhoon Watch": {"color": "#FF00FF", "priority": 57},
    "Tropical Storm Watch": {"color": "#F08080", "priority": 58},
    "Storm Watch": {"color": "#FFE4B5", "priority": 59},
    "Hurricane Local Statement": {"color": "#FFE4B5", "priority": 60},
    "Typhoon Local Statement": {"color": "#FFE4B5", "priority": 61},
    "Tropical Storm Local Statement": {"color": "#FFE4B5", "priority": 62},
    "Tropical Depression Local Statement": {"color": "#FFE4B5", "priority": 63},
    "Avalanche Watch": {"color": "#F4A460", "priority": 64},
    "Blue Alert": {"color": "#FFFFFF", "priority": 65},
    "Child Abduction Emergency": {"color": "#FFFFFF", "priority": 66},
    "Earthquake Advisory": {"color": "#8B4513", "priority": 67},
    "Volcano Advisory": {"color": "#2F4F4F", "priority": 68},
    "Ashfall Advisory": {"color": "#696969", "priority": 69},
    "Coastal Flood Advisory": {"color": "#7CFC00", "priority": 70},
    "Lakeshore Flood Advisory": {"color": "#7CFC00", "priority": 71},
    "Flood Advisory": {"color": "#00FF7F", "priority": 72},
    "High Surf Advisory": {"color": "#BA55D3", "priority": 73},
    "Heavy Freezing Spray Warning": {"color": "#00BFFF", "priority": 74},
    "Dense Fog Advisory": {"color": "#708090", "priority": 75},
    "Dense Smoke Advisory": {"color": "#F0E68C", "priority": 76},
    "Small Craft Advisory": {"color": "#D8BFD8", "priority": 77},
    "Dust Advisory": {"color": "#FFE4C4", "priority": 78},
    "Blowing Dust Advisory": {"color": "#FFE4C4", "priority": 79},
    "Lake Wind Advisory": {"color": "#D2B48C", "priority": 80},
    "Wind Advisory": {"color": "#D2B48C", "priority": 81},
    "Frost Advisory": {"color": "#6495ED", "priority": 82},
    "Ashfall Watch": {"color": "#A9A9A9", "priority": 83},
    "Freezing Fog Advisory": {"color": "#008080", "priority": 84},
    "Winter Weather Advisory": {"color": "#7B68EE", "priority": 85},
    "Heat Advisory": {"color": "#FF7F50", "priority": 86},
    "Wind Chill Advisory": {"color": "#AFEEEE", "priority": 87},
    "Rip Current Statement": {"color": "#40E0D0", "priority": 88},
    "Beach Hazards Statement": {"color": "#40E0D0", "priority": 89},
    "Gale Watch": {"color": "#FFC0CB", "priority": 90},
    "Winter Storm Watch": {"color": "#4682B4", "priority": 91},
    "Hazardous Weather Outlook": {"color": "#EEE8AA", "priority": 92},
    "Hydrologic Outlook": {"color": "#90EE90", "priority": 93},
    "Short Term Forecast": {"color": "#98FB98", "priority": 94},
    "Special Weather Statement": {"color": "#FFE4B5", "priority": 95},
    "Marine Weather Statement": {"color": "#FFDEAD", "priority": 96},
    "Air Quality Alert": {"color": "#808080", "priority": 97},
    "Air Stagnation Advisory": {"color": "#808080", "priority": 98},
    "Hazardous Seas Warning": {"color": "#D8BFD8", "priority": 99},
    "Low Water Advisory": {"color": "#A52A2A", "priority": 100},
}

def get_event_color(event_name):
    # Lookup color, default to Gray if not found
    return HAZARD_DATA.get(event_name, {}).get("color", "#808080")

def get_event_priority(event_name):
    # Lookup priority, default to 999 (lowest priority) if not found
    return HAZARD_DATA.get(event_name, {}).get("priority", 999)

# --- 2. SETUP TIME ---
utc_now = datetime.now(timezone.utc)
local_time = utc_now.astimezone(pytz.timezone('US/Eastern')).strftime('%I:%M %p %Z')
date_str = utc_now.astimezone(pytz.timezone('US/Eastern')).strftime('%b %d, %Y')

# --- 3. MAP SETUP ---
m = folium.Map(location=[35.5, -79.5], zoom_start=8, tiles=None)

# --- BASEMAPS ---
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Satellite Hybrid', overlay=False, control=True, show=False).add_to(m)
folium.TileLayer('https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}', attr='Google', name='Terrain', overlay=False, control=True, show=False).add_to(m)
folium.TileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google', name='Street Map', overlay=False, control=True, show=True).add_to(m)
folium.TileLayer('CartoDB positron', name='Light Gray Base', overlay=False, control=True, show=False).add_to(m)
LocateControl(auto_start=False, flyTo=True).add_to(m)

# --- 4. LOAD COUNTY BORDERS ---
county_file = "nc_counties.json"
if os.path.exists(county_file):
    with open(county_file, 'r') as f:
        folium.GeoJson(
            json.load(f), 
            name="County Lines",
            style_function=lambda x: {'color': 'black', 'weight': 1.5, 'fillOpacity': 0, 'dashArray': '5, 5', 'opacity': 0.7},
            overlay=True, control=True
        ).add_to(m)

# --- 5. FETCH DATA ---
marine_list = ["ANZ633", "ANZ658", "ANZ678", "AMZ230", "AMZ131", "AMZ231", "AMZ150", "AMZ170", "AMZ135", "AMZ152", "AMZ172", "AMZ136", "AMZ137", "AMZ156", "AMZ154", "AMZ174", "AMZ176", "AMZ158", "AMZ178", "AMZ250", "AMZ270"]
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
            
            # Use new color function
            active_events[ename] = get_event_color(ename) 
            
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
                        new_f = {"type": "Feature", "properties": f['properties'], "geometry": geom}
                        all_features.append(new_f)

    except Exception as e:
        print(f"Request error: {e}")
        continue

# --- 6. SORT & ADD ALERTS TO MAP ---
if all_features:
    # *** CRITICAL STEP: SORT BY PRIORITY ***
    # We sort strictly DESCENDING by priority number (100 -> 1).
    # Since Folium draws items in order, the last items in the list are drawn ON TOP.
    # High Priority = Low Number (1, 2, 3). So we want these at the END of the list.
    
    all_features.sort(key=lambda x: get_event_priority(x['properties']['event']), reverse=True)

    gdf = gpd.GeoDataFrame.from_features(all_features).set_crs(epsg=4326)
    
    folium.GeoJson(
        gdf,
        name="Active Hazards",
        style_function=lambda x: {
            'fillColor': get_event_color(x['properties']['event']),
            'color': 'black', 
            'weight': 1, 
            'fillOpacity': 0.5
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['event', 'headline'],
            aliases=['Alert:', 'Details:'],
            localize=True,
            style="font-size: 13px; padding: 10px; max-width: 300px; white-space: normal; word-wrap: break-word; color: black;"
        ),
        overlay=True,
        control=True
    ).add_to(m)

# --- 7. ADD LAYER CONTROL ---
folium.LayerControl(collapsed=True).add_to(m)

# --- 8. LEGEND & SAVE ---
# Sort the legend items by priority as well so the legend looks logical
legend_html_items = ""
if not active_events:
    legend_html_items = "<li><span style='margin-left:10px;'>No Active North Carolina Hazards</span></li>"
else:
    # Sort keys by priority for the legend display
    sorted_events = sorted(active_events.keys(), key=lambda k: get_event_priority(k))
    
    for event in sorted_events:
        color = active_events[event]
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

# --- ADD LOGO ---
logo_file = "nws.png"  # Ensure this file is in the same directory as index.html

# 'bottom' and 'left' are percentages (0-100) of the screen
FloatImage(logo_file, bottom=5, left=5).add_to(m)

m.save("index.html")
print("Map saved to index.html")
