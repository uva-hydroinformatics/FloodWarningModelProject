# -*- coding: utf-8 -*-
"""
This program retrieves data from the NOAA NOMADS repository, using the HRRRR model.
The forecasted surface precipitation is obtained as a dataset for the newest available 
UTC hour. Given a latitude and longitude in decimal degrees, an array of surface 
precipitation for the corresponding grid-relative location is printed to a netCDF file
with dimensions of time, latitude, and longitude. TIME IS IN DECIMAL DAYS
*Note* Script must be run with python 2.7 (compatible with pydap)
Authors: Gina O'Neil, Mohamed Morsy, Jeff Sadler
"""
import numpy as np
from pydap.client import open_url
import matplotlib.dates
import xray
import datetime as dt
import sys
import utm
from osgeo import gdal, osr, ogr
import numpy as np
import os

"""
Global parameters:
    -Study area location (LL and UR corners of TUFLOW model bounds)
    -Initial and average resolution values for longitude and latitude,
     needed for grid point conversion
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
    
    # Get newest available HRRR dataset by trying (current datetime - delta time) until
    # a dataset is available for that hour. This corrects for inconsistent posting
    # of HRRR datasets to repository
    dtime_now = dt.datetime.utcnow()
    print "Open a connection to HRRR to retrieve forecast rainfall data.............\n"
    #get newest available dataset
    dataset, url, date, hour = getData(dtime_now)
    print ("Retrieving forecast data from: %s " %(url))

    # select desired forecast product from grid, grid dimensions are time, lat, lon
    # apcpsfc = "surface total precipitation" [mm]
    # source: http://www.nco.ncep.noaa.gov/pmb/products/hrrr/hrrr.t00z.wrfsfcf00.grib2.shtml
    var = "apcpsfc"   
    precip = dataset[var]
    print ("Dataset open")
    
    # Convert dimensions to grid points, source: http://nomads.ncdc.noaa.gov/guide/?name=advanced
    grid_lon1 = gridpt(lon_lb, initLon, aResLon)
    grid_lon2 = gridpt(lon_ub, initLon, aResLon)
    grid_lat1 = gridpt(lat_lb, initLat, aResLat) 
    grid_lat2 = gridpt(lat_ub, initLat, aResLat)
    
    # Convert time steps from decimal days to datetime format
    #  must keep array items as datetime objects
    #times = [ matplotlib.dates.num2date(t-1) for t in precip.time[:] ]
    # hours = []
    # for t in times:
    #   hours.append(int(dt.datetime.strftime(times[t], "%H")))
    grid = precip[0, grid_lat1:grid_lat2, grid_lon1:grid_lon2]
    xres = grid.lon[1] - grid.lon[0]
    yres = grid.lat[1] - grid.lat[0]
    ysize = len(grid.lat)
    xsize = len(grid.lon)
    ulx = grid.lon[0] - (xres / 2.)
    uly = grid.lat[0] - (yres / 2.)
    driver = gdal.GetDriverByName('GTiff')
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    projected_srs = osr.SpatialReference()
    projected_srs.ImportFromEPSG(4269)
    projected_srs.SetUTM(18, True)
    gt = [ulx, xres, 0, uly, 0, yres]

    for hr in range(len(precip.time[:])):
        grid = precip[hr, grid_lat1:grid_lat2, grid_lon1:grid_lon2]
        precip_array = grid.apcpsfc.data[0]
        precip_array = precip_array.astype(np.float64)
        latlonfile = 'latlon{}.tif'.format(hr)
        ds = driver.Create(latlonfile, xsize, ysize, 1, gdal.GDT_Float64, )
        ds.SetProjection(srs.ExportToWkt())
        ds.SetGeoTransform(gt)
        outband=ds.GetRasterBand(1)
        outband.SetStatistics(np.min(precip_array),
                              np.max(precip_array),
                              np.average(precip_array),
                              np.std(precip_array))
        outband.WriteArray(precip_array)
        ds = None
        outfilename = "projected{}.tif".format(hr)
        os.system('gdalwarp {} {} -t_srs "+proj=utm +zone=18 +datum=NAD83"'.format(latlonfile, outfilename))
        print ("File for hour %d has been written" %(hr))


if __name__=="__main__":
   main()