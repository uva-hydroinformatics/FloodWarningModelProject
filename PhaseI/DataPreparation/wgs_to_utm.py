import utm
import numpy as np
from netCDF4 import Dataset


def convert_to_utm(coords):
    utm_coords = []
    for point in coords:
        for lat, lon in point:
            utm_result = utm.from_latlon(lat, lon)
            utm_point = utm_result[0], utm_result[1]
            utm_coords.append(utm_point)
    return utm_coords

n = Dataset('2016102515.nc', 'r')
lons = n.variables['x'][:]
lats = n.variables['y'][:]
lat_0 = lats.mean()
lon_0 = lons.mean()
prcips = n.variables['rainfall_depth'][:]
n.close()

# get just the bottom row and the right column coordinates
right_col_coords = np.dstack((lats, np.repeat(lons.min(), len(lats))))
bottom_row_coords = np.dstack((np.repeat(lats.min(), len(lons)), lons))

# convert to utm
right_col_utms = convert_to_utm(right_col_coords)
bottom_row_utms = convert_to_utm(bottom_row_coords)

projected_ys = np.array([a[1] for a in right_col_utms])
projected_xs = np.array([a[0] for a in bottom_row_utms])

