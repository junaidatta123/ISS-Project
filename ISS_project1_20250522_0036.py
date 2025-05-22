# ===== ISS TRACKER WITH LIVE TLE DATA & VISIBILITY RANGE =====
# Features:
# 1. Downloads the latest ISS orbit data (TLE) automatically
# 2. Tracks ISS position in real-time (UTC)
# 3. Draws a 2000 km visibility range circle (yellow dashed line)
# 4. Use LEFT/RIGHT arrow keys to move through time

import ephem
import datetime
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import sys
import requests
import numpy as np

# Set backend for Spyder compatibility
plt.switch_backend('Qt5Agg')

# ===== CONFIGURATION =====
ISS_VIEW_RANGE = 2000  # Visibility range in kilometers (2000 km ≈ ISS horizon)
TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"
# ===== END CONFIGURATION =====

def fetch_latest_tle():
    """Download the most recent ISS TLE data from Celestrak"""
    try:
        response = requests.get(TLE_URL)
        response.raise_for_status()
        lines = response.text.strip().split('\n')
        return lines[0].strip(), lines[1].strip(), lines[2].strip()  # Name, Line1, Line2
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
time_step = datetime.timedelta(seconds=10)

# Set up the map
fig = plt.figure(figsize=(12, 6), num="ISS Tracker - Use Arrow Keys")
ax = plt.axes(projection=ccrs.PlateCarree())
ax.stock_img()
ax.coastlines()
ax.add_feature(cfeature.BORDERS)

# Plot ISS and visibility range
iss_marker, = ax.plot([], [], 'ro', markersize=8, label="ISS", transform=ccrs.Geodetic())
visibility_circle, = ax.plot([], [], 'y--', linewidth=1, label=f"{ISS_VIEW_RANGE} km Visibility", transform=ccrs.Geodetic())
title = ax.set_title("", pad=20)

def calculate_visibility_circle(lat, lon, radius_km):
    """Generate points for a circle around (lat, lon) with given radius (great-circle distance)"""
    angles = np.linspace(0, 2 * np.pi, 100)
    earth_radius_km = 6371.0
    circle_lons, circle_lats = [], []
    
    for angle in angles:
        # Calculate new latitude/longitude using haversine formula
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

def update_position():
    """Update ISS position and visibility circle"""
    try:
        iss.compute(current_time)
        lon = float(iss.sublong) * 180.0 / ephem.pi
        lat = float(iss.sublat) * 180.0 / ephem.pi
        
        # Update ISS marker
        iss_marker.set_data([lon], [lat])
        
        # Update visibility circle
        circle_lons, circle_lats = calculate_visibility_circle(lat, lon, ISS_VIEW_RANGE)
        visibility_circle.set_data(circle_lons, circle_lats)
        
        # Update title
        title.set_text(f"Time (UTC): {current_time}\nLatitude: {lat:.2f}° | Longitude: {lon:.2f}°")
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