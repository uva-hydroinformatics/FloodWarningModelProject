# -*- coding: utf-8 -*-
"""
This program retrieves data from the TRMM repository
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

def zero_pad(inte):
    return '{:02d}'.format(inte)


def get_trmm_data(start_date, end_date, dty):
    lon_lb = (-78.54 - 0.2489797462 / 2)
    lon_ub = (-76.649286 + 0.455314383 / 2)
    lat_lb = 36.247
    lat_ub = 37.257
    st_date = dt.datetime.strptime(start_date, "%Y-%m-%d")
    ed_date = dt.datetime.strptime(end_date, "%Y-%m-%d")
    date_range = pd.date_range(st_date, ed_date, freq='3H')
    precip_list = []
    for d in date_range:
        print 'getting trmm data for {}'.format(d)
        doy = d.timetuple().tm_yday
        if d.hour == 0:
            doy -= 1
        url = 'https://disc2.gesdisc.eosdis.nasa.gov:443/opendap/TRMM_RT/TRMM_3B42RT.7/{yr}/{doy}/3B42RT.{yr}{mth}{dy}{hr}.7.nc4'.format(
            yr=d.year, mth=zero_pad(d.month), dy=zero_pad(d.day), hr=zero_pad(d.hour), doy=doy)
        print url
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
                                           lon_filt, p, '{}{}{}_{}'.format(d.year, zero_pad(d.month), zero_pad(d.day), zero_pad(d.hour)), dty)
        precip_list.append(precip_proj)
    return x, y, precip_list

def get_projected_array(lats, lons, precip, hr, directory):
    wgs_file = make_wgs_raster(lats, lons, precip, hr, directory)
    projected_file_name = project_to_utm(wgs_file, hr, directory)
    tif_to_asc(projected_file_name, hr, directory)
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
    latlonfile = '%s/TIF/%s.tif' % (directory, hr)
    print hr
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
    os.system('gdalwarp %s %s -t_srs "+proj=utm +zone=18 +datum=NAD83" -tr 500 500' % (wgs_raster_name,
                                                                           outfilename))
    return outfilename

def tif_to_asc(projected_tif, hr, directory):
    outascfile = "%s/ASC/%s.asc" % (directory, hr)
    os.system('gdal_translate -co force_cellsize=true  -of AAIGrid %s %s' % (projected_tif, outascfile))

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
    start_date_time_str = "2016-10-23"
    end_date_time_str = "2016-10-24"


    # make directory to store rainfall data
    direct = './TRMM_Archive_'+start_date_time_str+'_'+end_date_time_str
    os.makedirs(direct)
    # The TIF folder includes the original and projected rainfall data in TIF format
    os.makedirs(direct+"/TIF")
    # The ASC includes the projected rainfall in ASCII format
    # to be used as gridded rainfall with TUFLOW
    os.makedirs(direct+"/ASC")

    x, y, precips = get_trmm_data(start_date_time_str, end_date_time_str, direct)
    make_nc_file(x[:], y[:], precips, start_date_time_str)
    print 'kj'


if __name__ == "__main__":
    main()
