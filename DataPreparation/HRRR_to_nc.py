# -*- coding: utf-8 -*-
"""
This program retrieves data from the NOAA NOMADS repository, using the HRRRR model.
The forecasted surface precipitation is obtained as a dataset for the newest available 
UTC hour. Given a latitude and longitude in decimal degrees, an array of surface 
precipitation for the corresponding grid-relative location is printed to a netCDF file
with dimensions of time, latitude, and longitude. TIME IS IN DECIMAL DAYS
*Note* Script must be run with python 2.7 (compatible with pydap)
Author: Gina O'Neil
"""
import numpy as np
from pydap.client import open_url
import netCDF4 as nc4
from netCDF4 import Dataset
import matplotlib.dates
import xray
import datetime as dt
import sys
"""
Global parameters:
    -Study area location (LL and UR corners of TUFLOW model bounds)
    -Initial and average resolution values for longitude and latitude, needed for grid point conversion
    (source: http://nomads.ncep.noaa.gov:9090/dods/hrrr "info" link)
"""

initLon = -134.09548000000 # modified that to follow the latest values on the website
aResLon = 0.029

initLat = 21.14054700000 # modified that to follow the latest values on the website
aResLat = 0.027

# this values added to the original bounding box made the retrieved data to be
lon_lb = (-77.979315-0.4489797462)
lon_ub = (-76.649286-0.455314383)
lat_lb = (36.321159-0.133)
lat_ub = (37.203955-0.122955)
print lon_lb, lon_ub, lat_lb, lat_ub

def getData(current_dt):
    delta_T = 0
    while True:    
        try:
            dtime_fix = current_dt - dt.timedelta(hours = delta_T)
            date = dt.datetime.strftime(dtime_fix,"%Y%m%d")
            fc_hour = dt.datetime.strftime(dtime_fix, "%H")            
            hour = str(fc_hour)
            url = 'http://nomads.ncep.noaa.gov:9090/dods/hrrr/hrrr%s/hrrr_sfc_%sz'%(date,hour)
            dataset = open_url(url)
            if len(dataset.keys()) > 0:
                False
                return(dataset, url, date, hour)
            else:
                print "Back up method - Failed to open : %s"%(url)
                delta_T += 1
                True
        except:
            delta_T += 1
            print "Failed to open : %s"%(url)
            
def gridpt(myVal, initVal, aResVal):
    gridVal = int((myVal-initVal)/aResVal)
    return gridVal
    
def main():
    
    """Get newest available HRRR dataset by trying (current datetime - delta time) until 
    a dataset is available for that hour. This corrects for inconsistent posting
    of HRRR datasets to repository"""
    dtime_now = dt.datetime.utcnow() 
    dataset, url, date, hour = getData(dtime_now) #get newest available dataset
    print ("Retrieving forecast data from: %s " %(url))

    """select desired forecast product from grid, grid dimensions are time, lat, lon
    apcpsfc = "surface total precipitation" [mm]
    source: http://www.nco.ncep.noaa.gov/pmb/products/hrrr/hrrr.t00z.wrfsfcf00.grib2.shtml""" 
    var = "apcpsfc"   
    precip = dataset[var]
    print ("Dataset open")
    
    """Convert dimensions to grid points, source: http://nomads.ncdc.noaa.gov/guide/?name=advanced"""
    grid_lon1 = gridpt(lon_lb, initLon, aResLon) 
    grid_lon2 = gridpt(lon_ub, initLon, aResLon)
    grid_lat1 = gridpt(lat_lb, initLat, aResLat) 
    grid_lat2 = gridpt(lat_ub, initLat, aResLat)
    
    """Convert time steps from decimal days to datetime format, must keep array items as datetime objects"""    
    times = [ matplotlib.dates.num2date(t-1) for t in precip.time[:] ]

    """Slice grid to study area dimensions and create nc file named by datetime and forecast hour - single file
    indices are a range of latitudes and longitudes with a default of the smallest increment available (equal to respective avg. resolution)"""
    grid = precip[0:len(precip.time[:]), grid_lat1:grid_lat2, grid_lon1:grid_lon2]

    """Convert grid into x array Data Array"""
    precip_darray = xray.DataArray(grid.array[:], coords = [ grid.time[:], grid.lat[:], grid.lon[:]], dims = ['time', 'y', 'x'])
    print precip_darray
    """Convert Data Array to Dataset"""
    precip_ds = precip_darray.to_dataset(name='rainfall_depth')
    print precip_ds
    """Convert Dataset to Netcdf"""
    precip_ds.to_netcdf('%s%s.nc'%(date, hour))
  
    print ("Finished writing Netcdf file for %s hour %s, %d forecast hours available." %(date,hour, len(precip.time[:])))
#    times = [ matplotlib.dates.num2date(t-1) for t in precip.time[:] ]
#    times_fmt = [ dt.datetime.strftime(ts_d, "%d%b%Y%H%M") for ts_d in times]
    """Alternative: (Multiple files) For every available forecase hour in dataset, slice grid to study area dimensions and create nc file named by datetime and forecast hour"""
#    for hr in range(len(precip.time[:])):
#        grid = precip[hr, grid_lat1:grid_lat2, grid_lon1:grid_lon2]
#        data_array = xray.DataArray(grid.array[:], coords = [grid.time[:], grid.lat[:], grid.lon[:]], dims = ['time', 'latitude', 'longitude'])
#        precip_ds = data_array.to_dataset(name='%s'%(times_fmt[hr]))
#        precip_ds.to_netcdf('%s.nc'%(times_fmt[hr]))
#        print ("File for hour %d has been written" %(hr))
 
if __name__=="__main__":
   main()
