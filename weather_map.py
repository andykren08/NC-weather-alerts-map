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
    """
    Maps NWS Event names to hex colors.
    Add more events here as needed.
    """
    event_name = event_name.lower()
    
    # Marine / Beach Hazards
    if 'small craft' in event_name: return '#FF8C00'  # DarkOrange
    if 'gale' in event_name: return '#FF0000'         # Red
    if 'hurricane' in event_name: return '#8B0000'    # DarkRed
    if 'rip current' in event_name: return '#40E0D0'  # Turquoise
    if 'beach hazards' in event_name: return '#00CED1' # DarkTurquoise
    if 'special marine' in event_name: return '#FFA500' # Orange

    # Severe Weather
    if 'tornado' in event_name: return '#FF00FF'      # Magenta
    if 'severe thunderstorm' in event_name: return '#FFA500' # Orange
    if 'flash flood' in event_name: return '#00FF00'  # Lime
    if 'flood' in event_name: return '#32CD32'        # LimeGreen
    
    # Winter
    if 'winter' in event_name: return '#1E90FF'       # DodgerBlue
    if 'freeze' in event_name: return '#00BFFF'       # DeepSkyBlue
    
    # Fire
    if 'fire' in event_name or 'red flag' in event_name: return '#FF4500' # OrangeRed

    return '#808080' # Gray (Default fallback)

# --- 2. SETUP TIME ---
utc_now = datetime.now(timezone.utc)
local_time = utc_now.astimezone(pytz.timezone('US/Eastern')).strftime('%I:%M %p %Z')
date_str = utc_now.astimezone(pytz.timezone('US/Eastern')).strftime('%b %d, %Y')

# --- 3. MAP SETUP ---
m = folium.Map(location=[35.5, -76.0], zoom_start=7, tiles=None)
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                 attr='Google', name='Satellite Hybrid').add_to(m)
folium.TileLayer('CartoDB positron', name='Light Street Map').add_to(m)
LocateControl(auto_start=False, flyTo=True).add_to(m)

# --- 4. LOAD COUNTY BORDERS ---
county_file = "nc_counties.json"
if os.path.exists(county_file):
    with open(county_file, 'r') as f:
        folium.GeoJson(json.load(f), name="County Lines",
                       style_function=lambda x: {'color': '#666666', 'weight': 1.2, 'fillOpacity': 0}).add_to(m)

# --- 5. FETCH DATA ---
# Coastal/Marine Zones for NC/VA/SC
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
active_events = {} # format: { 'Event Name': 'HexColor' }
headers = {'User-Agent': 'NCWeatherMap/13.0'}

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
            
            # Save event and color for the Legend later
            color = get_color(ename)
            active_events[ename] = color
            
            # --- IMPROVED GEOMETRY LOGIC ---
            # If standard geometry is missing (common for Marine zones), fetch it from the zone URL
            if not f.get('geometry'):
                z_links = f['properties'].get('affectedZones', [])
                if z_links:
                    try:
                        # Fetch the polygon for the specific zone
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
            localize=True
        )
    ).add_to(m)

# --- 7. CREATE FLOATING LEGEND & TITLE ---
# We build an HTML list of the events we actually found during the fetch loop.

legend_html_items = ""
if not active_events:
    legend_html_items = "<li><span style='margin-left:10px;'>No Active Hazards</span></li>"
else:
    for event, color in active_events.items():
        legend_html_items += f"""
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="background:{color}; width: 15px; height: 15px; border: 1px solid black; margin-right: 8px; border-radius:3px;"></div>
            <span style="font-size:12px;">{event}</span>
        </div>
        """

# Define the HTML template for the floating box
template = f"""
{{% macro html(this, kwargs) %}}
<div id='maplegend' class='maplegend' 
    style='position: absolute; z-index:9999; border:2px solid grey; background-color:rgba(255, 255, 255, 0.9);
     border-radius:6px; padding: 10px; font-size:14px; right: 20px; bottom: 20px; width: 220px; box-shadow: 0 0 15px rgba(0,0,0,0.2);'>
     
    <div class='legend-title' style="font-weight: bold; margin-bottom: 5px; font-size: 16px;">NC Weather Alerts</div>
    <div style="font-size: 11px; color: #555; margin-bottom: 10px;">
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

# --- 8. SAVE MAP ---
output_file = "index.html"
m.save(output_file)
print(f"Map saved to {output_file}")
