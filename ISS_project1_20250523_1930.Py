# ===== ISS TRACKER WITH DAY/NIGHT & ORBIT PATH =====
# Features:
# 1. Shows day/night areas on map
# 2. Plots ISS orbit path before/after current time
# 3. Includes all previous functionality (target location, distances, etc.)

import ephem
import datetime
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import sys
import requests
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

# Set backend for Spyder compatibility
plt.switch_backend('Qt5Agg')

# ===== CONFIGURATION =====
ISS_VIEW_RANGE = 2000  # Visibility range in kilometers
TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"
time_step = datetime.timedelta(seconds=30)

# Target location (latitude, longitude)
target_lat, target_lon = 47.398, 20.083

# Orbit path configuration
isspath_dt_before = datetime.timedelta(minutes=30)  # Show path 30 mins before
isspath_dt_after = datetime.timedelta(minutes=30)   # Show path 30 mins after
isspath_step = datetime.timedelta(seconds=30)       # Time between path points

# Day/Night visualization settings
daynight_resolution = 100  # Resolution for day/night terminator calculation
# ===== END CONFIGURATION =====

def fetch_latest_tle():
    """Download the most recent ISS TLE data from Celestrak"""
    try:
        response = requests.get(TLE_URL)
        response.raise_for_status()
        lines = response.text.strip().split('\n')
        return lines[0].strip(), lines[1].strip(), lines[2].strip()
    except Exception as e:
        print(f"ERROR: Failed to fetch TLE data. Using fallback TLE.\nReason: {e}")
        return (
            "ISS (ZARYA)",
            "1 25544U 98067A   25140.37106448  .00008533  00000+0  15939-3 0  9993",
            "2 25544  51.6374  84.8753 0002567 126.2244  18.1297 15.49625942510847"
        )

# Load TLE data
name, line1, line2 = fetch_latest_tle()

try:
    iss = ephem.readtle(name, line1, line2)
except ValueError as e:
    print(f"ERROR: Invalid TLE data.\n{e}")
    print("Verify data from:", TLE_URL)
    sys.exit(1)

# Initialize time
current_time = datetime.datetime.utcnow()

# Set up the map
fig = plt.figure(figsize=(12, 6), num="ISS Tracker - Use Arrow Keys")
ax = plt.axes(projection=ccrs.PlateCarree())
ax.stock_img()
ax.coastlines()
ax.add_feature(cfeature.BORDERS)

# Create custom colormap for day/night (transparent night)
cmap = LinearSegmentedColormap.from_list('day_night', ['#00000000', '#00000080'])
norm = plt.Normalize(0, 1)

# Plot elements
iss_marker, = ax.plot([], [], 'ro', markersize=8, label="ISS", transform=ccrs.Geodetic())
visibility_circle, = ax.plot([], [], '--', color='magenta', linewidth=1, 
                           label=f"{ISS_VIEW_RANGE} km Visibility", transform=ccrs.Geodetic())
target_marker, = ax.plot([target_lon], [target_lat], 'b*', markersize=10, 
                        label="Target Location", transform=ccrs.Geodetic())
orbit_path, = ax.plot([], [], 'g-', linewidth=1, alpha=0.5, 
                     label="Orbit Path", transform=ccrs.Geodetic())
title = ax.set_title("", pad=20)

# Day/Night terminator
daynight_grid = np.zeros((daynight_resolution, daynight_resolution))
daynight_img = ax.imshow(daynight_grid, extent=(-180, 180, -90, 90),
                        cmap=cmap, norm=norm, transform=ccrs.PlateCarree())

def calculate_day_night(time):
    """Calculate day/night regions for given time"""
    grid = np.zeros((daynight_resolution, daynight_resolution))
    obs = ephem.Observer()
    obs.date = time
    sun = ephem.Sun()
    
    # Create longitude/latitude grid
    lons = np.linspace(-180, 180, daynight_resolution)
    lats = np.linspace(-90, 90, daynight_resolution)
    
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            obs.lat = str(lat)
            obs.lon = str(lon)
            sun.compute(obs)
            # 0 = day, 1 = night (will be mapped to transparency)
            grid[i, j] = 1 if sun.alt < 0 else 0
    
    return grid

def calculate_orbit_path(iss_obj, center_time, dt_before, dt_after, step):
    """Calculate ISS positions for orbit path"""
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
    """Calculate ground distance between two points on Earth (in km)"""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    return 6371 * 2 * np.arcsin(np.sqrt(a))

def straight_line_distance(lat1, lon1, alt1, lat2, lon2, alt2=0):
    """Calculate straight-line distance between two points (one in space) in km"""
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
    """Update all map elements"""
    try:
        iss.compute(current_time)
        lon = float(iss.sublong) * 180.0 / ephem.pi
        lat = float(iss.sublat) * 180.0 / ephem.pi
        alt_km = iss.elevation / 1000.0
        
        # Update ISS marker
        iss_marker.set_data([lon], [lat])
        
        # Update orbit path
        path_lons, path_lats = calculate_orbit_path(iss, current_time, 
                                                 isspath_dt_before, isspath_dt_after, 
                                                 isspath_step)
        orbit_path.set_data(path_lons, path_lats)
        
        # Update day/night
        daynight_grid = calculate_day_night(current_time)
        daynight_img.set_array(daynight_grid)
        
        # Calculate distances
        ground_dist = haversine_distance(lat, lon, target_lat, target_lon)
        direct_dist = straight_line_distance(lat, lon, alt_km, target_lat, target_lon)
        
        # Update title
        title_text = f"Time (UTC): {current_time}\n"
        title_text += f"ISS Position: Lat {lat:.2f}° | Lon {lon:.2f}° | Alt {alt_km:.0f} km\n"
        title_text += f"Ground Distance: {ground_dist:.0f} km | Direct Distance: {direct_dist:.0f} km"
        title.set_text(title_text)
        
        # Print to console
        print(f"Time: {current_time} | Ground: {ground_dist:.0f} km | Direct: {direct_dist:.0f} km")
        
        fig.canvas.draw_idle()
    except Exception as e:
        print(f"Error updating position: {e}")

def on_key(event):
    """Handle keyboard time navigation"""
    global current_time
    if event.key == "right":
        current_time += time_step
    elif event.key == "left":
        current_time -= time_step
    update_position()

# Connect keyboard events
fig.canvas.mpl_connect('key_press_event', on_key)

# Initial update
update_position()
plt.legend(loc='upper right')
plt.tight_layout()

print("INSTRUCTIONS:")
print("1. Click on the map window to give it focus")
print("2. Use LEFT/RIGHT arrow keys to move through time")
print("3. Close the window to exit")

plt.show()
