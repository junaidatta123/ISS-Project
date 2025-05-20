import ephem
import datetime
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# Set the backend explicitly for Spyder
plt.switch_backend('Qt5Agg')  # Best for Spyder's interactive plots

# ISS TLE data
name = "ISS (ZARYA)"
line1 = "1 25544U 98067A   12304.22916904  .00016548  00000-0  28330-3 0  5509"
line2 = "2 25544  51.6482 170.5822 0016684 224.8813 236.0409 15.51231918798998"

# Create satellite object
iss = ephem.readtle(name, line1, line2)

# Time management
current_time = datetime.datetime(2012, 1, 8, 11, 23, 42)
time_step = datetime.timedelta(seconds=10)

# Position history
past_lons = []
past_lats = []

# Set up the map
fig = plt.figure(figsize=(12, 6), num="ISS Tracker - Use Arrow Keys")
ax = plt.axes(projection=ccrs.PlateCarree())
ax.stock_img()
ax.coastlines()
ax.add_feature(cfeature.BORDERS)

# ISS visualization
marker, = ax.plot([], [], 'ro', markersize=8, label="ISS", transform=ccrs.Geodetic())
trail, = ax.plot([], [], 'b-', linewidth=1.5, alpha=0.6, transform=ccrs.Geodetic())
title = ax.set_title("", pad=20)

def update_position():
    """Update the ISS position on the map"""
    iss.compute(current_time)
    lon = float(iss.sublong) * 180.0 / ephem.pi
    lat = float(iss.sublat) * 180.0 / ephem.pi
    
    # Store history (limit to 100 points for performance)
    past_lons.append(lon)
    past_lats.append(lat)
    if len(past_lons) > 100:
        past_lons.pop(0)
        past_lats.pop(0)
    
    # Update visuals
    marker.set_data(lon, lat)
    trail.set_data(past_lons, past_lats)
    title.set_text(f"Time (UTC): {current_time}\nLatitude: {lat:.2f}° | Longitude: {lon:.2f}°")
    
    # Redraw
    fig.canvas.draw_idle()

def on_key(event):
    """Handle keyboard events"""
    global current_time
    if event.key == "right":
        current_time += time_step
    elif event.key == "left":
        current_time -= time_step
    else:
        return
    update_position()
    print(f"Time updated to: {current_time}")  # Debug output in Spyder console

# Connect events
fig.canvas.mpl_connect('key_press_event', on_key)

# Initial setup
update_position()
plt.legend(loc='upper right')
plt.tight_layout()

# Special instructions for Spyder
print("IMPORTANT: Click on the plot window and ensure it has focus before using arrow keys!")
plt.show()
