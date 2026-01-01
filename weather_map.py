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
from folium.plugins import Fullscreen

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
    "Heavy Freezing Spray Warning": {"color": "#00BFFF", "priority": 25},
    "Winter Storm Warning": {"color": "#FF69B4", "priority": 26},
    "Lake Effect Snow Warning": {"color": "#008B8B", "priority": 27},
    "Dust Storm Warning": {"color": "#FFE4C4", "priority": 28},
    "Blowing Dust Warning": {"color": "#FFE4C4", "priority": 29},
    "High Wind Warning": {"color": "#DAA520", "priority": 30},
    "Tropical Storm Warning": {"color": "#B22222", "priority": 31},
    "Storm Warning": {"color": "#9400D3", "priority": 32},
    "Tsunami Advisory": {"color": "#D2691E", "priority": 33},
    "Tsunami Watch": {"color": "#FF00FF", "priority": 34},
    "Avalanche Warning": {"color": "#1E90FF", "priority": 35},
    "Earthquake Warning": {"color": "#8B4513", "priority": 36},
    "Volcano Warning": {"color": "#2F4F4F", "priority": 37},
    "Ashfall Warning": {"color": "#A9A9A9", "priority": 38},
    "Flood Warning": {"color": "#00FF00", "priority": 39},
    "Coastal Flood Warning": {"color": "#228B22", "priority": 40},
    "Lakeshore Flood Warning": {"color": "#228B22", "priority": 41},
    "Ashfall Advisory": {"color": "#696969", "priority": 42},
    "High Surf Warning": {"color": "#228B22", "priority": 43},
    "Extreme Heat Warning": {"color": "#C71585", "priority": 44},
    "Tornado Watch": {"color": "#FFFF00", "priority": 45},
    "Severe Thunderstorm Watch": {"color": "#DB7093", "priority": 46},
    "Flood Watch": {"color": "#2E8B57", "priority": 47},
    "Gale Warning": {"color": "#DDA0DD", "priority": 48},
    "Flood Statement": {"color": "#00FF00", "priority": 49},
    "Extreme Cold Warning": {"color": "#0000FF", "priority": 50},
    "Freeze Warning": {"color": "#483D8B", "priority": 51},
    "Red Flag Warning": {"color": "#FF1493", "priority": 52},
    "Storm Surge Watch": {"color": "#DB7FF7", "priority": 53},
    "Hurricane Watch": {"color": "#FF00FF", "priority": 54},
    "Hurricane Force Wind Watch": {"color": "#9932CC", "priority": 55},
    "Typhoon Watch": {"color": "#FF00FF", "priority": 56},
    "Tropical Storm Watch": {"color": "#F08080", "priority": 57},
    "Storm Watch": {"color": "#FFE4B5", "priority": 58},
    "Tropical Cyclone Local Statement": {"color": "#FFE4B5", "priority": 59},
    "Winter Weather Advisory": {"color": "#7B68EE", "priority": 60},
    "Avalanche Advisory": {"color": "#CD853F", "priority": 61},
    "Cold Weather Advisory": {"color": "#AFEEEE", "priority": 62},
    "Heat Advisory": {"color": "#FF7F50", "priority": 63},
    "Flood Advisory": {"color": "#00FF7F", "priority": 64},
    "Coastal Flood Advisory": {"color": "#7CFC00", "priority": 65},
    "Lakeshore Flood Advisory": {"color": "#7CFC00", "priority": 66},
    "High Surf Advisory": {"color": "#BA55D3", "priority": 67},
    "Dense Fog Advisory": {"color": "#708090", "priority": 68},
    "Dense Smoke Advisory": {"color": "#F0E68C", "priority": 69},
    "Small Craft Advisory": {"color": "#D8BFD8", "priority": 70},
    "Brisk Wind Advisory": {"color": "#D8BFD8", "priority": 71},
    "Hazardous Seas Warning": {"color": "#D8BFD8", "priority": 72},
    "Dust Advisory": {"color": "#BDB76B", "priority": 73},
    "Blowing Dust Advisory": {"color": "#BDB76B", "priority": 74},
    "Lake Wind Advisory": {"color": "#D2B48C", "priority": 75},
    "Wind Advisory": {"color": "#D2B48C", "priority": 76},
    "Frost Advisory": {"color": "#6495ED", "priority": 77},
    "Freezing Fog Advisory": {"color": "#008080", "priority": 78},
    "Freezing Spray Advisory": {"color": "#00BFFF", "priority": 79},
    "Low Water Advisory": {"color": "#A52A2A", "priority": 80},
    "Local Area Emergency": {"color": "#C0C0C0", "priority": 81},
    "Winter Storm Watch": {"color": "#4682B4", "priority": 82},
    "Rip Current Statement": {"color": "#40E0D0", "priority": 83},
    "Beach Hazards Statement": {"color": "#40E0D0", "priority": 84},
    "Gale Watch": {"color": "#FFC0CB", "priority": 85},
    "Avalanche Watch": {"color": "#F4A460", "priority": 86},
    "Hazardous Seas Watch": {"color": "#483D8B", "priority": 87},
    "Heavy Freezing Spray Watch": {"color": "#BC8F8F", "priority": 88},
    "Coastal Flood Watch": {"color": "#66CDAA", "priority": 89},
    "Lakeshore Flood Watch": {"color": "#66CDAA", "priority": 90},
    "High Wind Watch": {"color": "#B8860B", "priority": 91},
    "Extreme Heat Watch": {"color": "#800000", "priority": 92},
    "Extreme Cold Watch": {"color": "#5F9EA0", "priority": 93},
    "Freeze Watch": {"color": "#00FFFF", "priority": 94},
    "Fire Weather Watch": {"color": "#FFDEAD", "priority": 95},
    "Extreme Fire Danger": {"color": "#E9967A", "priority": 96},
    "911 Telephone Outage": {"color": "#C0C0C0", "priority": 97},
    "Coastal Flood Statement": {"color": "#6B8E23", "priority": 98},
    "Lakeshore Flood Statement": {"color": "#6B8E23", "priority": 99},
    "Special Weather Statement": {"color": "#FFE4B5", "priority": 100},
    "Marine Weather Statement": {"color": "#FFDAB9", "priority": 101},
    "Air Quality Alert": {"color": "#808080", "priority": 102},
    "Air Stagnation Advisory": {"color": "#808080", "priority": 103},
    #  "Hazardous Weather Outlook": {"color": "#EEE8AA", "priority": 104},
    "Hydrologic Outlook": {"color": "#90EE90", "priority": 105},
    "Short Term Forecast": {"color": "#98FB98", "priority": 106},
    "Administrative Message": {"color": "#C0C0C0", "priority": 107},
    "Test": {"color": "#F0FFFF", "priority": 108},
    "Child Abduction Emergency": {"color": "#FFFFFF", "priority": 109},
    "Blue Alert": {"color": "#FFFFFF", "priority": 110},
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

# --- ADD FULLSCREEN BUTTON HERE ---
Fullscreen(
    position='topleft',
    title='Full Screen',
    title_cancel='Exit Full Screen',
    force_separate_button=True
).add_to(m)

# --- BASEMAPS ---

# Add ESRI Satellite
# 1. ESRI World Imagery (Satellite)
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Esri Satellite',
    overlay=False,
    control=True,
    show=False
).add_to(m)

# 2. ESRI World Street Map
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Esri Street Map',
    overlay=False,
    control=True,
    show=False
).add_to(m)

# 3. ESRI National Geographic (Good for weather maps)
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Esri NatGeo',
    overlay=False,
    control=True,
    show=True
).add_to(m)

# Your existing layers
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Google Satellite', overlay=False, control=True, show=False).add_to(m)
folium.TileLayer('https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}', attr='Google', name='Google Terrain', overlay=False, control=True, show=False).add_to(m)
folium.TileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google', name='Google Street', overlay=False, control=True, show=False).add_to(m)
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
marine_list = ["ANZ633", "ANZ658", "ANZ678", "AMZ230", "AMZ131", "AMZ231", "AMZ150", "AMZ170", "AMZ135", "AMZ152", "AMZ172", "AMZ136", "AMZ137", "AMZ156", "AMZ154", "AMZ174", "AMZ176", "AMZ158", "AMZ178", "AMZ250", "AMZ270", "AMZ252", "AMZ272", "AMZ270", "AMZ178", "AMZ176", "AMZ174", "AMZ172", "AMZ170", "ANZ678", "ANZ828", "ANZ830", "ANZ833", "ANZ835", "ANZ935", "ANZ930", "ANZ925"]
marine_zones = ",".join(marine_list)

urls = [
    "https://api.weather.gov/alerts/active?area=NC", 
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
            props = f['properties']
            alert_id = props.get('id')
            if alert_id in seen_ids: continue
            seen_ids.add(alert_id)

            # --- FILTER 1: REMOVE CANCELED ALERTS ---
            # If the NWS issues a cancellation, the alert stays in the feed 
            # until the message expires, even though it's "dead".
            if props.get('messageType') == 'Cancel':
                continue
            
            # --- FILTER 2: REMOVE EXPIRED HAZARD TIMES ---
            # Even if active, if the "ends" time has passed, don't show it.
            ends_str = props.get('ends')
            if ends_str:
                try:
                    ends_dt = datetime.fromisoformat(ends_str.replace("Z", "+00:00"))
                    if ends_dt < utc_now:
                        continue
                except ValueError:
                    pass

            # --- FILTER 3: KEYWORD SEARCH (Backup) ---
            # Sometimes 'messageType' is 'Update' but the headline says 'Cancelled'
            headline = props.get('headline', '').upper()
            description = props.get('description', '').upper()
            if 'CANCELLED' in headline or 'EXPIRATION' in headline:
                 # Double check this isn't a "Storm Cancelled... but Flood Warning continues" message
                 # usually simplicity is best: if the HEADLINE says cancelled, skip it.
                 continue

            ename = props['event']
            
            # Use new color function
            active_events[ename] = get_event_color(ename) 
            
            if f.get('geometry'):
                all_features.append(f)
            else:
                z_links = props.get('affectedZones', [])
                for z_link in z_links:
                    zone_id = z_link.split('/')[-1]
                    is_nc_zone = zone_id.startswith('NC') 
                    is_wanted_marine = zone_id in marine_list

                    if not (is_nc_zone or is_wanted_marine):
                        continue

                    geom = zone_geom_cache.get(z_link)
                    if not geom:
                        try:
                            z_res = requests.get(z_link, headers=headers, timeout=5)
                            if z_res.status_code == 200:
                                geom = z_res.json().get('geometry')
                                zone_geom_cache[z_link] = geom 
                        except Exception: pass
                    
                    if geom:
                        new_f = {"type": "Feature", "properties": props, "geometry": geom}
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

# --- ADD NWS LOGO ---
logo_file = "nws.png"
float_image = FloatImage(logo_file, bottom=5, left=5)
float_image.add_to(m)

# --- FORCE RESIZE WITH CSS ---
# This injects CSS to force the logo (which is an <img> tag inside the float div) to be 100px wide.
# You can change '100px' to whatever size looks best (e.g., '150px' or '10%').
resize_css = f"""
<style>
    img[src="{logo_file}"] {{
        width: 100px !important;
        height: auto !important;
    }}
</style>
"""
m.get_root().html.add_child(folium.Element(resize_css))

# --- 7. ADD LAYER CONTROL ---
folium.LayerControl(collapsed=False).add_to(m)

# Save the map first
m.save("index.html")

# --- ADD AUTO-REFRESH ---
# Re-open the file and inject a meta refresh tag
with open("index.html", "r") as f:
    html_content = f.read()

# Refreshes page every 300 seconds (5 minutes)
refresh_tag = '<meta http-equiv="refresh" content="300">' 
html_content = html_content.replace('<head>', f'<head>{refresh_tag}')

with open("index.html", "w") as f:
    f.write(html_content)

print("Map saved to index.html (with 5-minute auto-refresh)")
