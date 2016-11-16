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
from pydap.client import open_url
from pydap.exceptions import ServerError
import datetime as dt
from osgeo import gdal, osr
import numpy as np
import os
from netCDF4 import Dataset
import shutil
import xarray

"""
Global parameters:
    -Study area location (LL and UR corners of TUFLOW model bounds)
    -Initial and average resolution values for longitude and latitude,
     needed for grid point conversion
    (source: http://nomads.ncep.noaa.gov:9090/dods/hrrr "info" link)
"""

initLon = -134.09548000000  # modified that to follow the latest values on the website
aResLon = 0.029

initLat = 21.14054700000  # modified that to follow the latest values on the website
aResLat = 0.027

# this values added to the original bounding box made the retrieved data to be
lon_lb = (-77.979315-0.4489797462)
lon_ub = (-76.649286-0.455314383)
lat_lb = (36.321159-0.133)
lat_ub = (37.203955-0.122955)


def getData(current_dt, delta_T):
    dtime_fix = current_dt + dt.timedelta(hours=delta_T)
    date = dt.datetime.strftime(dtime_fix, "%Y%m%d")
    fc_hour = dt.datetime.strftime(dtime_fix, "%H")
    hour = str(fc_hour)
    url = 'http://nomads.ncep.noaa.gov:9090/dods/hrrr/hrrr%s/hrrr_sfc_%sz' % (date, hour)
    try:
        dataset = open_url(url)
        if len(dataset.keys()) > 0:
            return dataset, url, date, hour
        else:
            print "Back up method - Failed to open : %s" % url
            return getData(current_dt, delta_T - 1)
    except ServerError:
        print "Failed to open : %s" % url
        return getData(current_dt, delta_T - 1)


def gridpt(myVal, initVal, aResVal):
    gridVal = int((myVal-initVal)/aResVal)
    return gridVal


def make_wgs_raster(grid, hr, directory):
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
    precip_array = grid.apcpsfc.data[0]
    precip_array = precip_array.astype(np.float64)
    latlonfile = '%s/latlon%s.tif' % (directory, hr)
    ds = driver.Create(latlonfile, xsize, ysize, 1, gdal.GDT_Float64, )
    ds.SetProjection(srs.ExportToWkt())
    ds.SetGeoTransform(gt)
    outband = ds.GetRasterBand(1)
    outband.SetStatistics(np.min(precip_array),
                          np.max(precip_array),
                          np.average(precip_array),
                          np.std(precip_array))
    outband.WriteArray(precip_array)
    ds = None
    return latlonfile


def project_to_utm(wgs_raster_name, hr, directory):
    outfilename = "%s/projected%s.tif" % (directory, hr)
    os.system('gdalwarp %s %s -t_srs "+proj=utm +zone=18 +datum=NAD83"' % (wgs_raster_name,
                                                                           outfilename))
    return outfilename


def get_projected_array(grid, hr, directory):
    wgs_file = make_wgs_raster(grid, hr, directory)
    projected_file_name = project_to_utm(wgs_file, hr, directory)
    ds = gdal.Open(projected_file_name)
    precip = ds.ReadAsArray()
    ny, nx = np.shape(precip)
    b = ds.GetGeoTransform()  # bbox, interval
    x = np.arange(nx) * b[1] + (b[0] + b[1]/2.0)
    y = np.arange(ny) * b[5] + (b[3] + b[5]/2.0)
    return x, y, precip


def main():
    # remove any rasters in the current directory
    # Get newest available HRRR dataset by trying (current datetime - delta time) until
    # a dataset is available for that hour. This corrects for inconsistent posting
    # of HRRR datasets to repository
    utc_datetime = dt.datetime.utcnow()
    print "Open a connection to HRRR to retrieve forecast rainfall data.............\n"
    # get newest available dataset
    dataset, url, date, hour = getData(utc_datetime, delta_T=0)
    print ("Retrieving forecast data from: %s " % url)

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
    
    # make netcdf file ##
    # make directory to store rainfall data
    loc_datetime = dt.datetime.now().strftime('%Y%m%d.%H%M')
    os.makedirs(loc_datetime)

    # get projected coordinates to make netcdf
    grid = precip[0, grid_lat1:grid_lat2, grid_lon1:grid_lon2]
    x, y, precip_prj = get_projected_array(grid, 0, loc_datetime)
    nc_file_name = '%s/%s.nc' % (loc_datetime, loc_datetime)
    nco = Dataset(nc_file_name, mode='w')
    nco.createDimension('X', len(x))
    nco.createDimension('Y', len(y))
    nco.createDimension('time', None)

    x_var = nco.createVariable('X', 'f8', ('X',))
    y_var = nco.createVariable('Y', 'f8', ('Y',))
    rain = nco.createVariable('rainfall_depth', 'f4', ('time', 'X', 'Y'))

    y_var.standard_name = 'projection_y_coordinate'
    x_var.standard_name = 'projection_x_coordinate'
    y_var.long_name = 'y-coordinate in cartesian system'
    x_var.long_name = 'x-coordinate in cartesian system'

    y_var.units = 'm'
    x_var.units = 'm'

    x_var[:] = x
    y_var[:] = y

    # add rain values to .nc file for each time step
    precip_list = []
    for hr in range(len(precip.time[:])):
        grid = precip[hr, grid_lat1:grid_lat2, grid_lon1:grid_lon2]
        x, y, precip_prj = get_projected_array(grid, hr, loc_datetime)
        precip_list.append(precip_prj)
        precip_prj = np.transpose(precip_prj)
        rain[hr, :, :] = precip_prj
        print ("File for hour %d has been written" % hr)

    precip_array = np.array(precip_list)
    precip_xarray = xarray.DataArray(precip_array,
                                     coords=[
                                         np.float64(range(len(precip_array))),
                                         y[:],
                                         x[:]],
                                     dims=['time', 'Y', 'X'])
    precip_xarray.Y.attrs['standard_name'] = "projection_y_coordinate"
    precip_xarray.X.attrs['standard_name'] = "projection_x_coordinate"
    precip_xarray.Y.attrs['units'] = "m"
    precip_xarray.X.attrs['units'] = "m"
    print precip_xarray[0]
    """Convert Data Array to Dataset"""
    precip_ds = precip_xarray.to_dataset(name='rainfall_depth')
    print precip_ds
    """Convert Dataset to Netcdf"""
    precip_ds.to_netcdf('test.nc')

    nco.close()
    shutil.copy2(nc_file_name, "rainfall_forecast.nc")

if __name__ == "__main__":
    main()
