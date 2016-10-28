# coding: utf-8
from netCDF4 import Dataset
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.basemap import Basemap



def plot_nc(lons, lats, precips):
    m = Basemap(width=200000, height=200000, projection='stere',
                lat_0=lat_0, lon_0=lon_0)
    lon, lat = np.meshgrid(lons, lats)
    xi, yi = m(lon, lat)
    cs = m.pcolor(xi, yi, precips[0])
    m.drawstates()
    m.drawcounties()
    cbar = m.colorbar(cs, location='bottom', pad='10%')
    plt.show()

# get data
n = Dataset('2016102418.nc', 'r+')
lons = n.variables['longitude'][:]
lats = n.variables['latitude'][:]
lat_0 = lats.mean()
lon_0 = lons.mean()
prcips = n.variables['precipitation'][:]
n.close()

# plot
plot_nc(lons, lats, prcips)


