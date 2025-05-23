# ===== ISS TRACKER WITH IMPROVED DAY/NIGHT VISUALIZATION =====
# Features:
# 1. Shows day areas on map (yellow shading) - correctly shading the DAY side
# 2. Plots ISS orbit path before/after current time
# 3. Includes target location and distance calculations
# 4. Faster day/night calculation using cartopy
# 5. Working long time steps with Shift+arrow keys (10-minute jumps)

import ephem
import datetime
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.feature.nightshade import Nightshade
import requests
import numpy as np

# Set backend for better compatibility
plt.switch_backend('Qt5Agg')

# ===== CONFIGURATION =====
# Current time in UTC
current_time = datetime.datetime.utcnow()

# Time steps for navigation:
# - Regular arrow keys: 30 seconds
# - Shift+arrow keys: 10 minutes
time_step = datetime.timedelta(seconds=30)
long_time_step = datetime.timedelta(minutes=10)

# Target location (latitude, longitude)
target_lat, target_lon = 7.398, 27.083  # Example coordinates

# ISS visibility range in kilometers
ISS_VIEW_RANGE = 2000

# Where to get ISS position data
TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"

# Orbit path settings:
# - Shows 30 minutes before and after current time
# - Plots a point every 60 seconds
isspath_dt_before = datetime.timedelta(minutes=30)
isspath_dt_after = datetime.timedelta(minutes=30)
isspath_step = datetime.timedelta(seconds=60)
# ===== END CONFIGURATION =====

def fetch_latest_tle():
    """Get the most recent ISS position data from the internet"""
    try:
        response = requests.get(TLE_URL)
        response.raise_for_status()
        lines = response.text.strip().split('\n')
        return lines[0].strip(), lines[1].strip(), lines[2].strip()
    except Exception as e:
        print(f"Warning: Couldn't get fresh ISS data. Using backup data.\nError: {e}")
        return (
            "ISS (ZARYA)",
            "1 25544U 98067A   25140.37106448  .00008533  00000+0  15939-3 0  9993",
            "2 25544  51.6374  84.8753 0002567 126.2244  18.1297 15.49625942510847"
        )

def calculate_visibility_circle(lat, lon, radius_km):
    """Draw a circle around the ISS showing its visibility range"""
    angles = np.linspace(0, 2 * np.pi, 100)
    earth_radius_km = 6371.0
    circle_lons, circle_lats = [], []
    
    for angle in angles:
        # Math to calculate points on a circle on Earth's surface
        delta = radius_km / earth_radius_km
        circle_lat = np.arcsin(
            np.sin(np.radians(lat)) * np.cos(delta) + 
            np.cos(np.radians(lat)) * np.sin(delta) * np.cos(angle)
        )
        circle_lon = np.radians(lon) + np.arctan2(
            np.sin(angle) * np.sin(delta) * np.cos(np.radians(lat)),
            np.cos(delta) - np.sin(np.radians(lat)) * np.sin(circle_lat)
        )
        circle_lats.append(np.degrees(circle_lat))
        circle_lons.append(np.degrees(circle_lon))
    
    return circle_lons, circle_lats

def calculate_orbit_path(iss_obj, center_time, dt_before, dt_after, step):
    """Calculate where the ISS will be before and after current time"""
    times = []
    start_time = center_time - dt_before
    end_time = center_time + dt_after
    
    current = start_time
    while current <= end_time:
        times.append(current)
        current += step
    
    lons, lats = [], []
    for t in times:
        iss_obj.compute(t)
        lons.append(float(iss_obj.sublong) * 180.0 / ephem.pi)
        lats.append(float(iss_obj.sublat) * 180.0 / ephem.pi)
    
    return lons, lats

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points on Earth's surface (in km)"""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    return 6371 * 2 * np.arcsin(np.sqrt(a))

def straight_line_distance(lat1, lon1, alt1, lat2, lon2, alt2=0):
    """Calculate straight-line distance through space (in km)"""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    R = 6371.0
    x1 = (R + alt1) * np.cos(lat1) * np.cos(lon1)
    y1 = (R + alt1) * np.cos(lat1) * np.sin(lon1)
    z1 = (R + alt1) * np.sin(lat1)
    x2 = (R + alt2) * np.cos(lat2) * np.cos(lon2)
    y2 = (R + alt2) * np.cos(lat2) * np.sin(lon2)
    z2 = (R + alt2) * np.sin(lat2)
    return np.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)

def update_position():
    """Update everything on the map"""
    try:
        # Calculate ISS position
        iss.compute(current_time)
        lon = float(iss.sublong) * 180.0 / ephem.pi
        lat = float(iss.sublat) * 180.0 / ephem.pi
        alt_km = iss.elevation / 1000.0
        
        # Update ISS marker position
        iss_marker.set_data([lon], [lat])
        
        # Update orbit path
        path_lons, path_lats = calculate_orbit_path(iss, current_time, 
                                                 isspath_dt_before, isspath_dt_after, 
                                                 isspath_step)
        orbit_path.set_data(path_lons, path_lats)
        
        # Update day/night shading (now showing DAY in yellow)
        for patch in night_patches:
            patch.remove()
        night_patches.clear()
        # We invert the alpha to shade day instead of night
        night_patches.append(ax.add_feature(Nightshade(current_time, alpha=0.7, color='yellow')))
        
        # Update visibility circle
        circle_lons, circle_lats = calculate_visibility_circle(lat, lon, ISS_VIEW_RANGE)
        visibility_circle.set_data(circle_lons, circle_lats)

        # Calculate distances
        ground_dist = haversine_distance(lat, lon, target_lat, target_lon)
        direct_dist = straight_line_distance(lat, lon, alt_km, target_lat, target_lon)
        
        # Update title with information
        title_text = f"Time (UTC): {current_time}\n"
        title_text += f"ISS Position: Lat {lat:.2f}° | Lon {lon:.2f}° | Alt {alt_km:.0f} km\n"
        title_text += f"Ground Distance: {ground_dist:.0f} km | Direct Distance: {direct_dist:.0f} km"
        title.set_text(title_text)
        
        # Refresh the display
        fig.canvas.draw_idle()
    except Exception as e:
        print(f"Error updating position: {e}")

def on_key(event):
    """Handle keyboard time navigation (fixed Shift detection)"""
    global current_time
    
    # Debug: Uncomment to check key presses in terminal
    # print(f"Key pressed: {event.key}")  
    
    if event.key.lower() in ("right", "shift+right"):
        if "shift" in event.key.lower():
            current_time += long_time_step  # 10-minute jump
            print("10-minute jump forward")  # Optional confirmation
        else:
            current_time += time_step  # 30-second jump
            
    elif event.key.lower() in ("left", "shift+left"):
        if "shift" in event.key.lower():
            current_time -= long_time_step  # 10-minute jump
            print("10-minute jump backward")  # Optional confirmation
        else:
            current_time -= time_step  # 30-second jump
    
    update_position()

# ===== SETUP =====
# Get ISS position data
name, line1, line2 = fetch_latest_tle()
iss = ephem.readtle(name, line1, line2)

# Clean up time (remove seconds/microseconds)
current_time = current_time.replace(second=0, microsecond=0)

# Create the map
fig = plt.figure(figsize=(12, 6), num="ISS Tracker - Use Arrow Keys")
ax = plt.axes(projection=ccrs.PlateCarree())
ax.stock_img()  # Add basic map features
ax.coastlines()
ax.add_feature(cfeature.BORDERS)

# Create map elements:
# - Red dot for ISS
# - Magenta circle for visibility range
# - Blue star for target location
# - Green line for orbit path
iss_marker, = ax.plot([], [], 'ro', markersize=8, label="ISS", transform=ccrs.Geodetic())
visibility_circle, = ax.plot([], [], '--', color='magenta', linewidth=1, 
                           label=f"{ISS_VIEW_RANGE} km Visibility", transform=ccrs.Geodetic())
target_marker, = ax.plot([target_lon], [target_lat], 'b*', markersize=10, 
                        label="Target Location", transform=ccrs.Geodetic())
orbit_path, = ax.plot([], [], 'g-', linewidth=1, alpha=0.5, 
                     label="Orbit Path", transform=ccrs.Geodetic())
title = ax.set_title("", pad=20)

# Setup for day/night shading
night_patches = []
night_patches.append(ax.add_feature(Nightshade(current_time, alpha=0.7, color='yellow')))

# Connect keyboard controls
fig.canvas.mpl_connect('key_press_event', on_key)

# First update of the display
update_position()
plt.legend(loc='upper right')
plt.tight_layout()

print("INSTRUCTIONS:")
print("1. Click on the map window to give it focus")
print("2. Use LEFT/RIGHT arrow keys to move through time (30-second steps)")
print("3. Use SHIFT+LEFT/SHIFT+RIGHT for 10-minute steps")
print("4. Close the window to exit")

plt.show()