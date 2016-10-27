import utm
import numpy as np
from netCDF4 import Dataset

def convert_to_utm(lon, lat):
    wgs_coords = np.stack((lat, lon), axis=-1)
    utm_coords = []
    for point in wgs_coords:
        for lat, lon in point:
            utm_result = utm.from_latlon(lat, lon)
            utm_point = utm_result[0], utm_result[1]
            utm_coords.append(utm_point)
    return utm_coords

n = Dataset('2016102418.nc', 'r+')
lons = n.variables['longitude'][:]
lats = n.variables['latitude'][:]
lat_0 = lats.mean()
lon_0 = lons.mean()
prcips = n.variables['precipitation'][:]
n.close()


# convert to utm
lon, lat = np.meshgrid(lons, lats)
utms = convert_to_utm(lon, lat)
