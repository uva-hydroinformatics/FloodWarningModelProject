import os
from ftplib import FTP
from datetime import datetime, timedelta
from pydap.client import open_url
from pydap.exceptions import ServerError
import xarray as xr
import numpy as np
import time
import pandas as pd
from osgeo import gdal, osr

def zero_pad(inte):
    return '{:02d}'.format(inte)

def get_hrrr_data_info(current_date_utc, delta_time):
    dtime_fix = current_date_utc - timedelta(hours=delta_time)
    date = datetime.strftime(dtime_fix, "%Y%m%d")
    fc_hour = datetime.strftime(dtime_fix, "%H")
    hour = str(fc_hour)
    url = 'http://nomads.ncep.noaa.gov:9090/dods/hrrr/hrrr%s/hrrr_sfc_%sz' % (date, hour)
    try:
        dataset = open_url(url)
        if len(dataset.keys()) > 0:
            print "Succeeded to open : %s" % url
            return hour, date
        else:
            print "Back up method - Failed to open : %s" % url
            return get_hrrr_data_info(current_date_utc, delta_time + 1)
    except ServerError:
        print "Failed to open : %s" % url
        return get_hrrr_data_info(current_date_utc, delta_time + 1)


def make_wgs_raster(lats, lons, precip_array, hr, directory):
    xres = lons[1] - lons[0]
    yres = lats[1] - lats[0]
    ysize = len(lats)
    xsize = len(lons)
    ulx = lons[0] - (xres / 2.)
    uly = lats[0] - (yres / 2.)
    driver = gdal.GetDriverByName('GTiff')
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(102009)
    projected_srs = osr.SpatialReference()
    projected_srs.ImportFromEPSG(4269)
    projected_srs.SetUTM(18, True)
    gt = [ulx, xres, 0, uly, 0, yres]
    print precip_array

    # raw_input("TEST")
    #precip_array = precip_array.astype(np.float64)
    precip_array = np.array(precip_array, dtype=np.float64)
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


def tif_to_asc(projected_tif, hr, directory, shapefile):
    outclippedtif = "%s/TIF/clipped_%s.tif" % (directory, hr)
    os.system('gdalwarp -cutline %s -crop_to_cutline %s %s' % (shapefile, projected_tif, outclippedtif))
    outascfile = "%s/ASC/%s.asc" % (directory, hr)
    os.system('gdal_translate -co force_cellsize=true  -of AAIGrid %s %s' % (outclippedtif, outascfile))


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
    precip = np.flipud(precip)  # Flip the precipitation values to match up with Y values
    return x, y, precip


##################################################################################################
# ***************************************** Main Program *****************************************
##################################################################################################


# define the NWM main FTP URL.
ftp = FTP("ftpprd.ncep.noaa.gov")
ftp.login()

# create a local folder to store the downloaded data.
destination = "../bc_dbase/forecast_rainfall/"
if not os.path.exists(destination):
    os.makedirs(destination)

# data can be downloaded only for the current day and one day older as we are using the official
# website for the NWM. Date and time are in UTC time zone.
# "timedelta(days=0)": download the current date
# "timedelta(days=1)": download one day older from the current date
target_date_time_utc = datetime.utcnow()
#target_date = str(target_date_time_utc.date()- timedelta(days=0)).replace("-","")

# check the available hrrr forecast rainfall data to retrieve the appropriate boundary condition
# from the NWM
hour_utc, target_date = get_hrrr_data_info(target_date_time_utc, 0)

if not os.path.exists(destination+"/"+target_date):
    os.makedirs(destination+"/"+target_date)

# get the whole list of the available data for the target day
nwm_data="/pub/data/nccf/com/nwm/prod/nwm."+target_date+"/"
ftp.cwd(nwm_data)

# by default, all the data folder will be downloaded. In case you would like to download
# a specific folder, change the following line from "target_data_folder = ftp.nlst()" to
# "target_data_folder = ["NAME OF FOLDER"]".
# The currently available folders are ['analysis_assim', 'forcing_analysis_assim',
# 'forcing_medium_range', 'forcing_short_range', 'long_range_mem1', 'long_range_mem2',
# 'long_range_mem3', 'long_range_mem4', 'medium_range', 'short_range', 'usgs_timeslices']
target_data_folder = ['forcing_analysis_assim']

# download the available data for the target date and data folder/s
for data_type in target_data_folder:
    data_type_path = nwm_data+data_type+"/"
    dest_data_path = destination+"/"+target_date+"/"+data_type
    if not os.path.exists(dest_data_path):
        os.makedirs(dest_data_path)
    ftp.cwd(data_type_path)
    filelist=ftp.nlst()

    # check at least one file is available for the specific hour in hour_utc
    if data_type == 'forcing_analysis_assim':
        while not "nwm.t"+str(hour_utc)+"z.analysis_assim.forcing.tm00.conus.nc" in filelist:
            print "Waiting for the updated data in analysis_assim"
            time.sleep(30)
            filelist=ftp.nlst()

    # download the available files in the target folder/s
    for file in filelist:
        file_info = file.split(".")
        if file_info[1] == 't'+str(hour_utc)+'z' and file_info[4] == "tm00":
            ftp.retrbinary("RETR "+file, open(os.path.join(dest_data_path,file),"wb").write)
            dataset = xr.open_dataset(os.path.join(dest_data_path,file))
            var = dataset['RAINRATE']
            precp = var
            precp_hr = [x * 3600.0 for x in precp]
            #precp_hr=precp_hr[0].tolist()
            lats = np.array(dataset['y'[:]])
            lons = np.array(dataset['x'[:]])
            #lons_mask = (lons == lons)
            #lats_mask = (lats == lats)


            shp_filename = '../InputData/Hampton_Roads_model.shp'
            x, y, precip_proj = get_projected_array(lats, lons, precp_hr, 't0', data_type_path, shp_filename)
