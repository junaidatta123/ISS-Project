# Import required libraries
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import datetime
from datetime import timedelta

# Set the current UTC time
time_point = datetime.datetime.utcnow()

# Create the figure and add a world map
map_figure = plt.figure(figsize=(12, 6))
world_map = map_figure.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())  # Flat map view

# Show the whole Earth
world_map.set_global()

# Add map features
world_map.add_feature(cfeature.LAND, facecolor='lightgray')
world_map.add_feature(cfeature.OCEAN, facecolor='lightblue')
world_map.add_feature(cfeature.COASTLINE, linewidth=0.5)
world_map.add_feature(cfeature.BORDERS, linewidth=0.5)

# Add latitude and longitude grid lines
grid = world_map.gridlines(draw_labels=True, linewidth=0.2, color='gray', alpha=0.5)
grid.top_labels = False
grid.right_labels = False

# Title that shows the current UTC time
title = world_map.set_title(f"Current UTC Time: {time_point.strftime('%Y-%m-%d %H:%M:%S')}", fontsize=14)

# Function to update the time using arrow keys
def update_time(event):
    global time_point
    if event.key == 'right':
        time_point += timedelta(minutes=5)
    elif event.key == 'left':
        time_point -= timedelta(minutes=5)
    else:
        return  # Do nothing if it's not a left or right arrow

    # Update the title text with the new time
    title.set_text(f"Current UTC Time: {time_point.strftime('%Y-%m-%d %H:%M:%S')}")
    map_figure.canvas.draw_idle()  # Refresh the plot window

# Connect the keyboard input to the update function
map_figure.canvas.mpl_connect('key_press_event', update_time)

# Show the map
plt.tight_layout()
plt.show()

