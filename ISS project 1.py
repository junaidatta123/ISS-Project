import requests
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import datetime
from cartopy.feature.nightshade import Nightshade
import numpy as np

# Global variables
positions = []
view_from_iss = None
view_on_earth = None
iss_dot = None
trail = None
timestamp_text = None
iss_info_text = None
nightshade = None
ax = None

# Get ISS position
def get_iss_position():
    try:
        response = requests.get("http://api.open-notify.org/iss-now.json")
        response.raise_for_status()
        data = response.json()
        lat = float(data['iss_position']['latitude'])
        lon = float(data['iss_position']['longitude'])
        timestamp = data['timestamp']
        return lat, lon, timestamp
    except Exception as e:
        print("Error:", e)
        return None

# Update function for animation
def update(frame):
    global positions, iss_dot, trail, timestamp_text, iss_info_text, view_from_iss, view_on_earth, nightshade

    result = get_iss_position()
    if result:
        lat, lon, timestamp = result
        dt = datetime.datetime.utcfromtimestamp(timestamp)

        # Update ISS trail
        positions.append((lon, lat))
        if len(positions) > 200:
            positions.pop(0)
        lons, lats = zip(*positions)
        trail.set_data(lons, lats)
        iss_dot.set_data([lon], [lat])

        # Simulate the Earth point visible to ISS (approximate)
        earth_lat = lat - 20
        earth_lon = lon

        # Update viewpoint symbols
        view_from_iss.set_data([earth_lon], [earth_lat])
        view_on_earth.set_data([lon], [lat])

        # Update text
        timestamp_text.set_text(f'Time: {dt.strftime("%Y-%m-%d %H:%M:%S")} UTC')
        speed_mph = 4.758 * 3600  # approx 17130 mph
        iss_info_text.set_text(
            f'Lat: {lat:.2f}° | Lon: {lon:.2f}° | Alt: ~263 mi | Speed: {int(speed_mph)} mph'
        )

        # Update nightshade
        if nightshade:
            nightshade.remove()
        nightshade = Nightshade(dt, alpha=0.3)
        ax.add_feature(nightshade)

# Set up figure and map
fig = plt.figure(figsize=(12, 6))
proj = ccrs.PlateCarree()
ax = plt.axes(projection=proj)
ax.set_global()
ax.coastlines()
ax.add_feature(cfeature.BORDERS, linestyle=':')
ax.add_feature(cfeature.LAND, facecolor='lightyellow')
ax.add_feature(cfeature.OCEAN, facecolor='lightblue')

# Plot elements
iss_dot, = ax.plot([], [], 'ro', label='ISS', transform=ccrs.Geodetic())
trail, = ax.plot([], [], color='blue', linewidth=1, transform=ccrs.Geodetic())
view_from_iss, = ax.plot([], [], 'go', label='Earth View from ISS', transform=ccrs.Geodetic())
view_on_earth, = ax.plot([], [], 'mo', label='View of ISS from Earth', transform=ccrs.Geodetic())

# Texts
timestamp_text = ax.text(0.5, -0.08, '', transform=ax.transAxes, ha='center', fontsize=10)
iss_info_text = ax.text(0.5, -0.12, '', transform=ax.transAxes, ha='center', fontsize=10)

# Initial ISS position
initial = get_iss_position()
if initial:
    lat, lon, timestamp = initial
    positions.append((lon, lat))
    iss_dot.set_data([lon], [lat])
    dt = datetime.datetime.utcfromtimestamp(timestamp)
    timestamp_text.set_text(f'Time: {dt.strftime("%Y-%m-%d %H:%M:%S")} UTC')
    nightshade = Nightshade(dt, alpha=0.3)
    ax.add_feature(nightshade)

# Legend
ax.legend(loc='lower left')

# Animate
ani = FuncAnimation(fig, update, interval=5000, blit=False)

plt.tight_layout()
plt.show()

