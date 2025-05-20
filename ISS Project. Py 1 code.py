# Import necessary libraries
import matplotlib.pyplot as plt              # For drawing the map window
import cartopy.crs as ccrs                   # For map projections (how the globe is shown flat)
import cartopy.feature as cfeature           # For map details like land, borders, etc.

# Create a window for the map
map_figure = plt.figure(figsize=(12, 6))     # Width 12, height 6 in inches
world_map = map_figure.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())  # Flat world map

# Show the full world
world_map.set_global()

# Add map features: land, ocean, coastlines, and country borders
world_map.add_feature(cfeature.LAND, facecolor='lightgray')     # Continents
world_map.add_feature(cfeature.OCEAN, facecolor='lightblue')    # Water
world_map.add_feature(cfeature.COASTLINE, linewidth=0.5)        # Outline of continents
world_map.add_feature(cfeature.BORDERS, linewidth=0.5)          # Country borders

# Add grid lines with labels (latitude and longitude)
grid_lines = world_map.gridlines(draw_labels=True, linewidth=0.2, color='gray', alpha=0.5)
grid_lines.top_labels = False     # No labels on top edge
grid_lines.right_labels = False   # No labels on right edge

# Add a title at the top of the map
world_map.set_title("World Map with Continents and Borders", fontsize=14)

# Show the map on the screen
plt.tight_layout()
plt.show()

