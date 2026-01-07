import requests
import geopandas as gpd
import folium
import os
import json
from datetime import datetime, timezone
import pytz
from branca.element import Template, MacroElement
from folium.plugins import LocateControl, Fullscreen

# --- 1. CONFIGURATION: NWS HAZARD DATA ---
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
    "Hydrologic Outlook": {"color": "#90EE90", "priority": 105},
    "Short Term Forecast": {"color": "#98FB98", "priority": 106},
    "Administrative Message": {"color": "#C0C0C0", "priority": 107},
    "Test": {"color": "#F0FFFF", "priority": 108},
    "Child Abduction Emergency": {"color": "#FFFFFF", "priority": 109},
    "Blue Alert": {"color": "#FFFFFF", "priority": 110},
}

def get_event_color(event_name):
    return HAZARD_DATA.get(event_name, {}).get("color", "#808080")

def get_event_priority(event_name):
    return HAZARD_DATA.get(event_name, {}).get("priority", 999)

# --- 2. CATEGORIZATION LOGIC ---
def get_category(event_name):
    ename = event_name.upper()
    if any(word in ename for word in ["TORNADO", "SEVERE THUNDERSTORM", "EXTREME WIND", "SHELTER", "EVACUATION", "CIVIL", "NUCLEAR", "HAZARDOUS"]):
        return "Severe"
    if any(word in ename for word in ["HURRICANE", "TROPICAL", "TYPHOON", "STORM SURGE"]):
        return "Tropical"
    if any(word in ename for word in ["WINTER", "SNOW", "BLIZZARD", "ICE", "FREEZING", "FREEZE", "FROST", "COLD"]):
        return "Winter"
    if any(word in ename for word in ["FLOOD", "HYDROLOGIC", "WATER"]):
        return "Hydro"
    if any(word in ename for word in ["MARINE", "GALE", "SURF", "SEAS", "WAVE", "SMALL CRAFT", "RIP CURRENT", "BEACH"]):
        return "Marine"
    if "HEAT" in ename:
        return "Heat"
    if any(word in ename for word in ["FIRE", "RED FLAG"]):
        return "Fire"
    if any(word in ename for word in ["AIR QUALITY", "STAGNATION", "SMOKE"]):
        return "Air Quality"
    if any(word in ename for word in ["WIND", "FOG", "DUST", "ASHFALL"]):
        return "Wind & Visibility"
    return "Other"

# --- 3. MAP & SETUP ---
utc_now = datetime.now(timezone.utc)
local_time = utc_now.astimezone(pytz.timezone('US/Eastern')).strftime('%I:%M %p %Z')
date_str = utc_now.astimezone(pytz.timezone('US/Eastern')).strftime('%b %d, %Y')

# *** FIX 1: Use OpenStreetMap. It is the most reliable default. ***
m = folium.Map(location=[35.5, -79.5], zoom_start=8, tiles="OpenStreetMap")

Fullscreen(position='topleft', force_separate_button=True).add_to(m)

# *** FIX 2: Set additional tile layers to show=False by default ***
# This prevents them from blanketing the map with a white box if they fail to load.
folium.TileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Esri Satellite',
    show=False  # <--- MUST BE FALSE or it hides the base map!
).add_to(m)

folium.TileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Esri NatGeo',
    show=False
).add_to(m)

LocateControl(auto_start=False, flyTo=True).add_to(m)

# Initialize Category Groups
groups = {
    "Severe": folium.FeatureGroup(name="⚠️ Severe (Tornado/SVR)", show=True),
    "Tropical": folium.FeatureGroup(name="🌀 Tropical/Hurricane", show=True),
    "Winter": folium.FeatureGroup(name="❄️ Winter Weather", show=True),
    "Hydro": folium.FeatureGroup(name="🌊 Flooding/Hydro", show=True),
    "Marine": folium.FeatureGroup(name="⚓ Marine Hazards", show=True),
    "Heat": folium.FeatureGroup(name="🌡️ Heat Hazards", show=True),
    "Fire": folium.FeatureGroup(name="🔥 Fire (Red Flag)", show=True),
    "Air Quality": folium.FeatureGroup(name="🌫️ Air Quality", show=True),
    "Wind & Visibility": folium.FeatureGroup(name="🌬️ Wind & Visibility", show=True),
    "Other": folium.FeatureGroup(name="ℹ️ Other Advisories", show=True)
}

# --- 4. FETCH & PROCESS DATA ---
marine_list = ["ANZ633", "ANZ658", "ANZ678", "AMZ230", "AMZ131", "AMZ231", "AMZ150", "AMZ170", "AMZ135", "AMZ152", "AMZ172", "AMZ136", "AMZ137", "AMZ156", "AMZ154", "AMZ174", "AMZ176", "AMZ158", "AMZ178", "AMZ250", "AMZ270", "AMZ252", "AMZ272", "ANZ828", "ANZ830", "ANZ833", "ANZ835", "ANZ935", "ANZ930", "ANZ925"]
urls = ["https://api.weather.gov/alerts/active?area=NC", f"https://api.weather.gov/alerts/active?zone={','.join(marine_list)}"]

all_features = []
seen_ids = set()
active_events = {}
headers = {'User-Agent': 'NCWeatherMap/13.0'}
zone_geom_cache = {}

for url in urls:
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200: continue
        for f in res.json().get('features', []):
            props = f['properties']
            if props.get('id') in seen_ids or props.get('messageType') == 'Cancel': continue
            
            # Check expiration
            ends_str = props.get('ends')
            if ends_str:
                try:
                    if datetime.fromisoformat(ends_str.replace("Z", "+00:00")) < utc_now: continue
                except: pass

            seen_ids.add(props.get('id'))
            ename = props['event']
            active_events[ename] = get_event_color(ename)
            
            if f.get('geometry'):
                all_features.append(f)
            else:
                for z_link in props.get('affectedZones', []):
                    zone_id = z_link.split('/')[-1]
                    if not (zone_id.startswith('NC') or zone_id in marine_list): continue
                    geom = zone_geom_cache.get(z_link)
                    if not geom:
                        z_res = requests.get(z_link, headers=headers, timeout=5)
                        if z_res.status_code == 200:
                            geom = z_res.json().get('geometry')
                            zone_geom_cache[z_link] = geom
                    if geom:
                        all_features.append({"type": "Feature", "properties": props, "geometry": geom})
    except: continue

# --- 5. ADD TO MAP BY CATEGORY ---
if all_features:
    all_features.sort(key=lambda x: get_event_priority(x['properties']['event']), reverse=True)
    
    for feat in all_features:
        cat = get_category(feat['properties']['event'])
        folium.GeoJson(
            feat,
            style_function=lambda x: {
                'fillColor': get_event_color(x['properties']['event']),
                'color': 'black', 'weight': 1, 'fillOpacity': 0.5
            },
            tooltip=folium.GeoJsonTooltip(fields=['event', 'headline'], aliases=['Alert:', 'Details:'])
        ).add_to(groups[cat])

for g in groups.values():
    g.add_to(m)

# --- 6. LEGEND & OVERLAYS ---
legend_html_items = ""
if not active_events:
    legend_html_items = "<li>No Active Hazards</li>"
else:
    for event in sorted(active_events.keys(), key=lambda k: get_event_priority(k)):
        legend_html_items += f"""
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="background:{active_events[event]}; width: 15px; height: 15px; border: 1px solid black; margin-right: 8px;"></div>
            <span>{event}</span>
        </div>"""

template = f"""
{{% macro html(this, kwargs) %}}
<div style='position: fixed; z-index:9999; border:2px solid grey; background:rgba(255,255,255,0.9);
     padding: 10px; right: 20px; bottom: 20px; width: 220px; border-radius:6px;'>
    <b>NC Weather Hazards</b><br><small>Updated: {local_time}</small><hr>
    {legend_html_items}
</div>
{{% endmacro %}}"""

macro = MacroElement()
macro._template = Template(template)
m.get_root().add_child(macro)

# County Borders (Filtered to prevent crash if file is missing)
if os.path.exists("nc_counties.json"):
    try:
        with open("nc_counties.json", 'r') as f:
            folium.GeoJson(
                json.load(f), 
                name="County Lines", 
                style_function=lambda x: {'color': 'black', 'weight': 1, 'fillOpacity': 0, 'dashArray': '5, 5'}
            ).add_to(m)
    except:
        pass

folium.LayerControl(collapsed=False).add_to(m)
m.save("index.html")
print("Map saved to index.html")
