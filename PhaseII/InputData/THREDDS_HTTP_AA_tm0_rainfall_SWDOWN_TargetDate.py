import os
import zipfile
import urllib
from ftplib import FTP
from datetime import datetime, timedelta
from pydap.client import open_url
from pydap.exceptions import ServerError
import shutil
import xarray as xr
import numpy as np
import time
import pandas as pd
from osgeo import gdal, osr


def zero_pad(inte):
    return '{:02d}'.format(inte)


def make_wgs_raster(lats, lons, precip_array, hr, directory):
    xres = lons[1] - lons[0]
    yres = lats[1] - lats[0]
    ysize = len(lats)
    xsize = len(lons)
    ulx = lons[0] - (xres / 2.)
    uly = lats[0] - (yres / 2.)
    driver = gdal.GetDriverByName('GTiff')
    srs = osr.SpatialReference()
    prj4_str = "+proj=lcc +a=6370000.0 +f=0.0 +pm=0.0  +x_0=0.0 +y_0=0.0 +lon_0=-97.0 +lat_1=30.0 +lat_2=60.0 +lat_0=40.0000076294 +units=m +axis=enu +no_defs"
    srs.ImportFromProj4(prj4_str)
    projected_srs = osr.SpatialReference()
    projected_srs.ImportFromEPSG(4269)
    projected_srs.SetUTM(18, True)
    gt = [ulx, xres, 0, uly, 0, yres]
    precip_array = np.asarray(precip_array[0], dtype=np.float64)
    latlonfile = '%s/%s.tif' % (directory, hr)
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
    print ("Projecting file for hour {} from WSG84 to NAD83 UTM ZONE 18N".format(hr))
    # Added -tr to fix the output raster resoltuion to match with the one projected in ArcMap
    os.system('gdalwarp %s %s -t_srs "+proj=utm +zone=18 +datum=NAD83" -tr 500 500' %
              (wgs_raster_name, outfilename))
    return outfilename


def tif_to_asc(projected_tif, hr, directory, shapefile):
    outclippedtif = "%s/clipped_%s.tif" % (directory, hr)
    os.system('gdalwarp -cutline %s -crop_to_cutline %s %s' % (shapefile, projected_tif,
                                                               outclippedtif))
    outascfile = "%s/%s.asc" % (directory, hr)
    os.system('gdal_translate -co force_cellsize=true  -of AAIGrid %s %s' % (outclippedtif,
                                                                             outascfile))


def get_projected_array(lats, lons, precip, hr, directory, shapefile):
    wgs_file = make_wgs_raster(lats, lons, precip, hr, directory)
    projected_file_name = project_to_utm(wgs_file, hr, directory)
    tif_to_asc(projected_file_name, hr, directory, shapefile)
    ds = gdal.Open(projected_file_name)
    precip = ds.ReadAsArray()
    # uncomment the following line to generate dummy rainfall data for testing
    # precip_flip = np.mgrid[0:37, 0:44][0]*10 + np.arange(0, 44, 1)
    ny, nx = np.shape(precip)
    b = ds.GetGeoTransform()  # bbox, interval
    x = np.arange(nx) * b[1] + (b[0] + b[1]/2.0)
    y = np.arange(ny) * b[5] + (b[3] + b[5]/2.0)
    y = np.flipud(y)  # This step to arrange Y values from smallest to largest
    # Flip the precipitation values to match up with Y values
    precip = np.flipud(precip)
    return x, y, precip


##################################################################################################
# ***************************************** Main Program *****************************************
##################################################################################################


# define the NWM main FTP URL.
ftp = FTP("ftpprd.ncep.noaa.gov")
ftp.login()

# shapefile for the study area
shp_filename = '..\scripts_shapefiles\Hampton_Roads_model.shp'


# data can be downloaded only for the current day and one day older as we are using the official
# website for the NWM. Date and time are in UTC time zone.
# "timedelta(days=0)": download the current date
# "timedelta(days=1)": download one day older from the current date
target_date_time_utc = datetime.utcnow()
#target_date = str(target_date_time_utc.date()- timedelta(days=0)).replace("-","")

# check the available hrrr forecast rainfall data to retrieve the appropriate boundary condition
# from the NWM
##hour_utc, target_date = get_hrrr_data_info(target_date_time_utc, 0)


target_date = "20180728"

# create a local folder to store the downloaded data.
destination = target_date
if not os.path.exists(destination):
    os.makedirs(destination)


# by default, all the data folder will be downloaded. In case you would like to download
# a specific folder, change the following line from "target_data_folder = ftp.nlst()" to
# "target_data_folder = ["NAME OF FOLDER"]".
# The currently available folders are ['analysis_assim', 'forcing_analysis_assim',
# 'forcing_medium_range', 'forcing_short_range', 'long_range_mem1', 'long_range_mem2',
# 'long_range_mem3', 'long_range_mem4', 'medium_range', 'short_range', 'usgs_timeslices']
target_data_type = 'forcing_analysis_assim'

dest_data_path = destination+"/"+target_data_type+"/realtime_rainfall/"
if not os.path.exists(dest_data_path):
    os.makedirs(dest_data_path)


rain_layers = []
for i in range(24):

    # download the available files in the target folder/s

    file_name = 'nwm.'+target_date+'.t'+str(i).zfill(2)+'z.analysis_assim.forcing.tm00.conus.nc'

    urllib.urlretrieve('http://tds.renci.org:8080/thredds/fileServer/nwm/forcing_analysis_assim/'+file_name,
        dest_data_path+file_name)

    dataset = xr.open_dataset(os.path.join(dest_data_path, file_name))
    var = dataset['RAINRATE']
    precp = var
    precp_hr = [x * 3600.0 for x in precp]
    lats = np.array(dataset['y'[:]])
    lons = np.array(dataset['x'[:]])
    name_item = file_name.split(".")[:-2]
    name_select = (name_item[1], name_item[2], "rain", name_item[5])
    gen_file_name = ".".join(name_select)
    rain_layers.append(gen_file_name)

    x, y, precip_proj = get_projected_array(
        lats, lons, precp_hr, gen_file_name, dest_data_path, shp_filename)
    dataset.close()
    os.remove(os.path.join(dest_data_path, 'nwm.20180820.t23z.analysis_assim.forcing.tm00.conus.nc'))
    os.remove(os.path.join(dest_data_path, gen_file_name+".tif"))
    os.remove(os.path.join(dest_data_path, "projected"+gen_file_name+".tif"))
    os.remove(os.path.join(dest_data_path, "clipped_"+gen_file_name+".tif"))

rainfall_realtime = open(dest_data_path+"/rainfall_realtime.csv", 'w')
for i in range(len(rain_layers)):
    rainfall_realtime.write(str(i)+","+rain_layers[i]+".asc\n")
rainfall_realtime.close()
# Zip the rainfall data folder to send to AWS S3 then delete the original folder
shutil.make_archive(target_date, 'zip', target_date)
#shutil.rmtree(target_date)
print "Done Archiving the NWM realtime rainfall data for "+target_date+" from THREDDS!"