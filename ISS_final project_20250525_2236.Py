# ===== ISS TRACKER WITH DAY/NIGHT & ORBIT PATH =====
# Features:
# - Shows day/night areas on the map
# - Plots ISS location at the current time
# - Plots a target location on the map
# - Plots ISS orbit path before/after the current time
# - Plots the circle within which the Sun is not visible from the ISS
# - Shows the horizon visible from the ISS at the current time
# - The map can be centered on the night hemisphere
# - The current time can be changed in small as well as in larger steps
# - The current time (UTC) and the ISS - target distance is printed in the console

# Instructions:
# Set/check the configuration parameters at the beginning of the code
#   before you run the program
# Further instructions are printedn in the console when the code is run
#   or can be read at the very end of the code

import ephem                              # Astronomical calculations (satellite positions, sun/moon)
import datetime                            # Time manipulation
import matplotlib.pyplot as plt          # Plotting and visualization
import cartopy.crs as ccrs               # Map projections
import cartopy.feature as cfeature       # Map features (coastlines, borders)
import cartopy.feature.nightshade as cpyns    # Day/night shading
import shapely.geometry as sgeom            # Geometric calculations
import sys
import requests                           # HTTP requests to fetch TLE data
import numpy as np                        # Numerical computations
from matplotlib.colors import LinearSegmentedColormap

global current_time, sun, obs
global ax, iss_marker, visibility_circle, target_marker, orbit_path, title, sunsight_curve

# ===== CONFIGURATION =====

# Target location (latitude, longitude)
target_lat, target_lon = 7.398, 27.083

# Initialize time
current_time = datetime.datetime.utcnow()
# current_time = datetime.datetime.strptime("2025.05.28 07:30", "%Y.%m.%d %H:%M")

# Time steps for navigation:
# - Regular arrow keys: 30 seconds
# - Shift+arrow keys: 10 minutes
time_step = datetime.timedelta(seconds=60)
long_time_step = datetime.timedelta(minutes=10)

# ISS visibility range in kilometers
ISS_VIEW_RANGE = 2000  # Visibility range in kilometers
# Where to get ISS position data
TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"

# Orbit path settings:
# - Shows 30 minutes before and after current time
isspath_dt_before = datetime.timedelta(minutes=45)  # Show path X mins before
isspath_dt_after = datetime.timedelta(minutes=45)   # Show path X mins after
# - Plots a point every 60 seconds
isspath_step = datetime.timedelta(seconds=60)       # Time between path points

# Sunsight curve settings
sunsight_resolution = 100  # Resolution for sun sight curve calculation

# The radius of the Earth in km
R = 6371.0 # km
# ===== END CONFIGURATION =====

# ===== Subroutine Definition =====
def calculate_sunsight(time, lon, lat, iss):
    """Calculate da curve where the Sun is at the horizon as seen from the ISS"""
    global sun, obs
    # R is the earth_radius_km

    # lon and lat are the coordinate of the subsolar points
    # obs.date = time
    # sun.compute(obs)
    # lon = sun.ra - obs.sidereal_time()
    # lat = sun.dec
    
    alt_km = iss.elevation / 1000.0

    angles = np.linspace(0, 2 * np.pi, sunsight_resolution)
    circle_lons, circle_lats = [], []
    
    delta = np.pi/2.0 + np.arctan(R/(R+alt_km))
    for angle in angles:
        # Calculate new latitude/longitude using haversine formula
        # Math to calculate points on a circle on Earth's surface
        circle_lat = np.arcsin(
            np.sin(lat) * np.cos(delta) + 
            np.cos(lat) * np.sin(delta) * np.cos(angle)
        )
        circle_lon = lon + np.arctan2(
            np.sin(angle) * np.sin(delta) * np.cos(lat),
            np.cos(delta) - np.sin(lat) * np.sin(circle_lat)
        )
        circle_lats.append(np.degrees(circle_lat))
        circle_lons.append(np.degrees(circle_lon))
    
    return circle_lons, circle_lats


class Dayshade(cfeature.ShapelyFeature):
    def __init__(self, date=None, delta=0.1, refraction=0.83,
                 color="k", alpha=0.5, **kwargs):
        """
        Shade the darkside of the Earth, accounting for refraction.

        Parameters
        ----------
        date : datetime
            A UTC datetime object used to calculate the position of the sun.
            Default: datetime.datetime.utcnow()
        delta : float
            Stepsize in degrees to determine the resolution of the
            night polygon feature (``npts = 180 / delta``).
        refraction : float
            The adjustment in degrees due to refraction,
            thickness of the solar disc, elevation etc...

        Note
        ----
            Matplotlib keyword arguments can be used when drawing the feature.
            This allows standard Matplotlib control over aspects such as
            'color', 'alpha', etc.

        """
        if date is None:
            date = datetime.datetime.utcnow()

        # make sure date is UTC, or naive with respect to time zones
        if date.utcoffset():
            raise ValueError(
                f'datetime instance must be UTC, not {date.tzname()}')

        # Returns the Greenwich hour angle,
        # need longitude (opposite direction)
        lat, lon = cpyns._solar_position(date)
        # move "solar" position to the opposite side        
        lat = -lat
        lon = ((lon + 360) % 360) - 180.

        pole_lon = lon
        if lat > 0:
            pole_lat = -90 + lat
            central_lon = 180
        else:
            pole_lat = 90 + lat
            central_lon = 0

        rotated_pole = ccrs.RotatedPole(pole_latitude=pole_lat,
                                        pole_longitude=pole_lon,
                                        central_rotated_longitude=central_lon)

        npts = int(180 / delta)
        x = np.empty(npts * 2)
        y = np.empty(npts * 2)

        # Solve the equation for sunrise/sunset:
        # https://en.wikipedia.org/wiki/Sunrise_equation#Generalized_equation
        # NOTE: In the generalized equation on Wikipedia,
        #       delta == 0. in the rotated pole coordinate system.
        #       Therefore, the max/min latitude is +/- (90+refraction)

        # Fill latitudes up and then down
        y[:npts] = np.linspace(-(90 + refraction), 90 + refraction, npts)
        y[npts:] = y[:npts][::-1]

        # Solve the generalized equation for omega0, which is the
        # angle of sunrise/sunset from solar noon
        # We need to clip the input to arccos to [-1, 1] due to floating
        # point precision and arccos creating nans for values outside
        # of the domain
        arccos_tmp = np.clip(np.sin(np.deg2rad(refraction)) /
                             np.cos(np.deg2rad(y)), -1, 1)
        omega0 = np.rad2deg(np.arccos(arccos_tmp))

        # Fill the longitude values from the offset for midnight.
        # This needs to be a closed loop to fill the polygon.
        # Negative longitudes
        x[:npts] = -(180 - omega0[:npts])
        # Positive longitudes
        x[npts:] = 180 - omega0[npts:]

        kwargs.setdefault('facecolor', color)
        kwargs.setdefault('alpha', alpha)

        geom = sgeom.Polygon(np.column_stack((x, y)))
        return super().__init__(
            [geom], rotated_pole, **kwargs)


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

def calculate_visibility_circle(lat, lon, radius_km):
    """Generate points for a circle around (lat, lon) with given radius (great-circle distance)"""
    # R is the earth_radius_km
    angles = np.linspace(0, 2 * np.pi, 100)
    circle_lons, circle_lats = [], []
    
    for angle in angles:
        # Calculate new latitude/longitude using haversine formula
        # Math to calculate points on a circle on Earth's surface
        delta = radius_km / R
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
    # R is the earth_radius_km
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    return R * 2 * np.arcsin(np.sqrt(a))

def straight_line_distance(lat1, lon1, alt1, lat2, lon2, alt2=0):
    """Calculate straight-line distance between two points (one in space) in km"""
    # R is the earth_radius_km
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    x1 = (R + alt1) * np.cos(lat1) * np.cos(lon1)
    y1 = (R + alt1) * np.cos(lat1) * np.sin(lon1)
    z1 = (R + alt1) * np.sin(lat1)
    x2 = (R + alt2) * np.cos(lat2) * np.cos(lon2)
    y2 = (R + alt2) * np.cos(lat2) * np.sin(lon2)
    z2 = (R + alt2) * np.sin(lat2)
    return np.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)

def update_position():
    """Update all map elements"""
    global current_time, obs, sun
    global ax, iss_marker, visibility_circle, target_marker, orbit_path, title, sunsight_curve

    try:
        iss.compute(current_time)
        lon = float(iss.sublong) * 180.0 / ephem.pi
        lat = float(iss.sublat) * 180.0 / ephem.pi
        alt_km = iss.elevation / 1000.0
        
        obs.date = current_time
        sun.compute(obs)
        sun_lon = sun.ra - obs.sidereal_time()
        sun_lat = sun.dec

        # Update ISS marker
        iss_marker.set_data([lon], [lat])
        
        # Update orbit path
        path_lons, path_lats = calculate_orbit_path(iss, current_time, 
                                                 isspath_dt_before, isspath_dt_after, 
                                                 isspath_step)
        orbit_path.set_data(path_lons, path_lats)

        # Update day shading (now showing DAY in yellow)
        for patch in day_patches:
            patch.remove()
        day_patches.clear()
        day_patches.append(ax.add_feature(Dayshade(current_time, alpha=0.7, color='lightyellow')))
        
        # Update visibility circle
        circle_lons, circle_lats = calculate_visibility_circle(lat, lon, ISS_VIEW_RANGE)
        visibility_circle.set_data(circle_lons, circle_lats)

        # Update sunsight curve
        sunsight_lons, sunsight_lats = calculate_sunsight(current_time, sun_lon, sun_lat, iss)
        sunsight_curve.set_data(sunsight_lons, sunsight_lats)
        
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

    # Debug: Uncomment to check key presses in terminal
    # print(f"Key pressed: {event.key}")  
    
    global current_time, obs, sun
    global ax, iss_marker, visibility_circle, target_marker, orbit_path, title, sunsight_curve

    if event.key.lower() in ("right", "shift+right"):
        if "shift" in event.key.lower():
            current_time += long_time_step
            update_position()
        else:
            current_time += time_step
            update_position()
    elif event.key.lower() in ("left", "shift+left"):
        if "shift" in event.key.lower():
            current_time -= long_time_step
            update_position()
        else:
            current_time -= time_step
            update_position()
    elif event.key == 'c':
        obs.date = current_time
        sun.compute(obs)
        sun_lon = sun.ra - obs.sidereal_time()

        # update axes
        ax.remove()
        anti_subsol_lon = sun_lon + np.pi
        if anti_subsol_lon >= np.pi:
            anti_subsol_lon -= 2*np.pi
        ax = plt.axes(projection=ccrs.PlateCarree(central_longitude=np.degrees(anti_subsol_lon)))
        ax.stock_img()
        ax.coastlines()
        ax.add_feature(cfeature.BORDERS)
        iss_marker, = ax.plot([], [], 'ro', markersize=8, label="ISS", transform=ccrs.Geodetic())
        visibility_circle, = ax.plot([], [], '--', color='magenta', linewidth=1, 
                                   label=f"{ISS_VIEW_RANGE} km Visibility", transform=ccrs.Geodetic())
        target_marker, = ax.plot([target_lon], [target_lat], 'b*', markersize=10, 
                                label="Target Location", transform=ccrs.Geodetic())
        orbit_path, = ax.plot([], [], 'g-', linewidth=1, alpha=0.5, 
                             label="ISS Orbit", transform=ccrs.Geodetic())
        # title = ax.set_title("", pad=10)
        title = ax.set_title("")
        sunsight_curve, = ax.plot([], [], '-', color='black', linewidth=2, 
                                   label="Sun visibility", transform=ccrs.Geodetic())
        plt.legend(loc='upper right')
        update_position()
        plt.tight_layout()


# ===== END Subroutine Definition =====

# ===== MAIN CODE =====

# Set backend for Spyder compatibility
plt.switch_backend('Qt5Agg')

# Define Sun
obs = ephem.Observer()
sun = ephem.Sun()

# Load TLE data
name, line1, line2 = fetch_latest_tle()

try:
    iss = ephem.readtle(name, line1, line2)
except ValueError as e:
    print(f"ERROR: Invalid TLE data.\n{e}")
    print("Verify data from:", TLE_URL)
    sys.exit(1)

# Round the initial time down to the nearest minute
current_time = current_time.replace(second=0,microsecond = 0)

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
                     label="ISS Orbit", transform=ccrs.Geodetic())
# title = ax.set_title("", pad=10)
title = ax.set_title("")

# Setup for shading the day side
# For shading the dayside see
# https://stackoverflow.com/questions/75524172/inversing-nightshade-to-shade-daylight
day_patches = []
day_shade = Dayshade(current_time, alpha=0.7, color='lightyellow')
day_patches.append(ax.add_feature(day_shade))

sunsight_curve, = ax.plot([], [], '-', color='black', linewidth=2, 
                           label="Sun visibility", transform=ccrs.Geodetic())

# Connect keyboard events
fig.canvas.mpl_connect('key_press_event', on_key)

# Initial update
plt.legend(loc='upper right')

print("INSTRUCTIONS:")
print("1. Click on the map window to give it focus")
print("2. Use LEFT/RIGHT arrow keys to move through time")
print("   SHIFT + LEFT/RIGHT arrow keys to jump in time")
print("   Press 'c' to center the map on the night hemisphere")
print("3. Close the window to exit")

update_position()
plt.tight_layout()
plt.show()
