# -*- coding: utf-8 -*-
"""
This program retrieves data from the NOAA NOMADS repository, using the High-Resolution Rapid Refresh
(HRRR) model (https://rapidrefresh.noaa.gov/hrrr/). The forecasted surface precipitation is obtained
as a dataset for the newest available UTC hour. Given a latitude and longitude in decimal degrees,
an array of surface precipitation for the corresponding grid-relative location is printed to TIF,
ASCII, and netCDF file formats. TIME IS IN DECIMAL DAYS.
*Note* Script must be run with python 2.7 (compatible with pydap)
"""
from pydap.client import open_url
from pydap.exceptions import ServerError
import datetime as dt
from osgeo import gdal, osr
import numpy as np
import os
import shutil
import xarray
from pydap.cas.urs import setup_session
import pandas as pd


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


def zero_pad(inte):
    return '{:02d}'.format(inte)


def get_trmm_data(start_date, end_date, dty):
    lon_lb = (-77.979315 - 0.2489797462 / 2)
    lon_ub = (-76.649286 + 0.455314383 / 2)
    lat_lb = 36.321159
    lat_ub = 37.203955
    st_date = dt.datetime.strptime(start_date, "%Y-%m-%d")
    ed_date = dt.datetime.strptime(end_date, "%Y-%m-%d")
    date_range = pd.date_range(st_date, ed_date, freq='3H')
    precip_list = []
    for d in date_range:
        print 'getting trmm data for {}'.format(d)
        doy = d.timetuple().tm_yday
        if d.hour == 0:
            doy -= 1
        url = 'https://disc2.gesdisc.eosdis.nasa.gov:443/opendap/TRMM_RT/TRMM_3B42RT.7/{yr}/{doy}/3B42RT.{yr}{mth}{dy}{hr}.7R2.nc4'.format(
            yr=d.year, mth=zero_pad(d.month), dy=zero_pad(d.day), hr=zero_pad(d.hour), doy=doy)
        session = setup_session('jsadler2', 'UVa2017!', check_url=url)
        dataset = open_url(url, session=session)
        var = dataset['precipitation']
        precp = var[:, :]
        lats = np.array(dataset['lat'[:]])
        lons = np.array(dataset['lon'[:]])
        lon_mask = (lons > lon_lb) & (lons < lon_ub)
        lon_filt = lons[lon_mask]
        lat_mask = (lats > lat_lb) & (lats < lat_ub)
        lat_filt = lats[lat_mask]
        prcep_place = precp[lat_mask]
        precp_m = prcep_place.T[lon_mask]
        p = precp_m.T

        x, y, precip_proj = get_projected_array(lat_filt,
                                           lon_filt, p, '{}{}'.format(d.day, d.hour), dty)
        precip_list.append(precip_proj)
    return x, y, precip_list


def get_hrrr_data():
    pass


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
    except:
        print "Failed to open : %s" % url
        return getData(current_dt, delta_T - 1)


def gridpt(myVal, initVal, aResVal):
    gridVal = int((myVal-initVal)/aResVal)
    return gridVal


def make_wgs_raster(lats, lons, precip_array, hr, directory):
    xres = lons[1] - lons[0]
    yres = lats[1] - lats[0]
    ysize = len(lats)
    xsize = len(lons)
    ulx = lons[0] - (xres / 2.)
    uly = lats[0] - (yres / 2.)
    driver = gdal.GetDriverByName('GTiff')
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    projected_srs = osr.SpatialReference()
    projected_srs.ImportFromEPSG(4269)
    projected_srs.SetUTM(18, True)
    gt = [ulx, xres, 0, uly, 0, yres]
    precip_array = precip_array.astype(np.float64)
    latlonfile = '%s/TIF/latlon%s.tif' % (directory, hr)
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
    outfilename = "%s/TIF/projected%s.tif" % (directory, hr)
    print ("Projecting file for hour {} from WSG84 to NAD83 UTM ZONE 18N".format(hr))
    # Added -tr to fix the output raster resoltuion to match with the one projected in ArcMap
    os.system('gdalwarp %s %s -t_srs "+proj=utm +zone=18 +datum=NAD83" -tr 25478.02331 25478.02331' % (wgs_raster_name,
                                                                           outfilename))
    return outfilename


def get_projected_array(lats, lons, precip, hr, directory):
    wgs_file = make_wgs_raster(lats, lons, precip, hr, directory)
    projected_file_name = project_to_utm(wgs_file, hr, directory)
    ds = gdal.Open(projected_file_name)
    precip = ds.ReadAsArray()
    # uncomment the following line to generate dummy rainfall data for testing
    # precip_flip = np.mgrid[0:37, 0:44][0]*10 + np.arange(0, 44, 1)
    ny, nx = np.shape(precip)
    b = ds.GetGeoTransform()  # bbox, interval
    x = np.arange(nx) * b[1] + (b[0] + b[1]/2.0)
    y = np.arange(ny) * b[5] + (b[3] + b[5]/2.0)
    y = np.flipud(y)  # This step to arrange Y values from smallest to largest
    precip = np.flipud(precip)  # Flip the precipitation values to match up with Y values
    return x, y, precip


def generate_gridded_rainfall_data(x, y, precip_list, directory):
    for data in range(len(precip_list)):
        f = open(directory+'/t'+ str(data)+'.asc', 'w')
        f.write('ncols '+str(len(x))+'\n')
        f.write('nrows '+str(len(y))+'\n')
        f.write('xllcorner '+str(x[0]- (x[1]-x[0])/2.0)+'\n')  # xllcorner 230832.744572
        f.write('yllcorner '+str(y[0]- (y[1]-y[0])/2.0)+'\n')  # yllcorner 4021153.35743
        f.write('cellsize '+str(x[1]-x[0])+'\n')  # cellsize 2759.32949
        f.write('NODATA_value -999.0\n')  # TUFLOW No Data value = -999.0
        precip_data=np.flipud(precip_list[data])
        for i in range(len(precip_data)-1):
            for j in range (len(precip_data[i])):
                f.write(str(precip_data[i][j])+' ')
            f.write('\n')
        for j in range (len(precip_data[-1])):
            f.write(str(precip_data[-1][j])+' ')
        f.close()


def make_nc_file(x, y, precip_array, start_date_time):
    precip_xarray = xarray.DataArray(precip_array,
                                     coords=[
                                         np.float64(range(len(precip_array))),
                                         y,
                                         x],
                                     dims=['time', 'y', 'x'])
    precip_xarray.y.attrs['standard_name'] = 'projection_y_coordinate'
    precip_xarray.y.attrs['long_name'] = 'y-coordinate in cartesian system'
    precip_xarray.y.attrs['units'] = 'm'
    precip_xarray.y.attrs['axis'] = 'Y'
    precip_xarray.x.attrs['standard_name'] = 'projection_x_coordinate'
    precip_xarray.x.attrs['long_name'] = 'x-coordinate in cartesian system'
    precip_xarray.x.attrs['units'] = 'm'
    precip_xarray.x.attrs['axis'] = 'X'
    precip_xarray.time.attrs['standard_name'] = 'time'
    precip_xarray.time.attrs['long_name'] = 'time'
    precip_xarray.time.attrs['units'] = 'hours since %s' % start_date_time
    precip_xarray.time.attrs['axis'] = 'T'
    # Convert Data Array to Dataset
    precip_ds = precip_xarray.to_dataset(name='rainfall_depth')
    print "Generated NetCDF file information:"
    print precip_ds

    # Convert Dataset to Netcdf
    nc_file_name = '%s/%s.nc' % (start_date_time, start_date_time)
    precip_ds.to_netcdf(nc_file_name)
    return nc_file_name


##################################################################################################
# ***************************************** Main Program *****************************************
##################################################################################################

def main():
    # Get newest available HRRR dataset by trying (current datetime - delta time) until
    # a dataset is available for that hour. This corrects for inconsistent posting
    # of HRRR datasets to repository
    # get newest available dataset
    observation = True
    if observation:
        start_date_time_str = "2012-10-28"
        end_date_time_str = "2012-11-01"
    else:
        pass
        # loc_datetime = dt.datetime.now()
        # start_date_time_str = loc_datetime.strftime('%Y%m%d-%H%M%S')
        #
        # dataset, url, date, hour = getData(utc_datetime, delta_T=0)
        #
        # precip = dataset[var]


    # make directory to store rainfall data

    os.makedirs(start_date_time_str)
    # The TIF folder includes the original and projected rainfall data in TIF format
    os.makedirs(start_date_time_str+"/TIF")
    # The ASC includes the projected rainfall in ASCII format
    # to be used as gridded rainfall with TUFLOW
    os.makedirs(start_date_time_str+"/ASC")

    drcty = "C:/Users/Jeff/Documents/research/morsy_3rd/FloodWarningModelProject/DataPreparation"
    x, y, precips = get_trmm_data(start_date_time_str, end_date_time_str, start_date_time_str)
    make_nc_file(x[:], y[:], precips, start_date_time_str)
    print 'kj'
    # add rain values to data array file for each time step
    # # precip_list = []
    # # for hr in range(len(precip.time[:])):
    # #     while True:
    # #         try:
    # #             grid = precip[hr, grid_lat1:grid_lat2, grid_lon1:grid_lon2]
    # #             x, y, precip_prj = get_projected_array(grid, hr, start_date_time_str)
    # #             # precip_prj.fill(hr*10)  # uncomment this line to produce dummy data
    # #             precip_list.append(precip_prj)
    # #             print ("File for hour %d has been written" % hr)
    # #             break
    # #         except ServerError:
    # #             'There was a server error. Let us try again'
    #
    # # Write gridded forecast rainfall data as ASCII files
    # generate_gridded_rainfall_data(x, y, precip_list, start_date_time_str+'/ASC')
    #
    # # Build dataset to create a NetCDF for forecast rainfall data
    # precip_array = np.array(precip_list)
    # nc_file_name = make_nc_file(x[:], y[:], precip_array, start_date_time_str)
    #
    # # Send the NetCDF to the bc_dbase directory for TUFLOW to run
    # if not os.path.exists('../bc_dbase/forecast_rainfall'):
    #     os.makedirs('../bc_dbase/forecast_rainfall')
    # shutil.copy2(nc_file_name, "../bc_dbase/forecast_rainfall/rainfall_forecast.nc")
    #
    # # Zip the rainfall data folder to send to AWS S3 then delete the original folder
    # shutil.make_archive('zip', '../bc_dbase/forecast_rainfall/'+start_date_time_str, start_date_time_str)
    # shutil.rmtree(start_date_time_str)
    # print "Done with the forecast rainfall data pre-processing!"

if __name__ == "__main__":
    main()
