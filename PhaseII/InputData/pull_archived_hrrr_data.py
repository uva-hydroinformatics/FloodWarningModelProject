"""
This script downloads data for a actual rainfall data (layer f00) with a specified date and time from the Utah HRRR archive using cURL.
Using 'APCP' as the variable gets the real hourly precipitation amount for each day.
Utah Archive web page: http://home.chpc.utah.edu/~u0553130/Brian_Blaylock/hrrr_FAQ.html

Steps:
    1) Read the lines from the Metadata .idx file
    2) Identify the byte range for the variable of interest
    3) Download the byte range using cURL.

Reference:
Ben Bowes: https://github.com/uva-hydroinformatics-lab/Norfolk_Groundwater_Model/blob/master/
Preprocess/HRRR_Archive_single_variable.py
"""

import re
from datetime import date, datetime, timedelta
import os
import sys
import struct
import urllib2, ssl
from osgeo import gdal, ogr
from os.path import basename
from os.path import splitext
import numpy as np

# =============================================================================
#     Modify these
# =============================================================================
start_date_time_str = datetime(2016, 9, 20)
end_date_time_str = datetime(2016, 10, 24)

shp_filename = './2d_code_05_R.shp'

step_date_time=start_date_time_str



print "done"

DATE = date(2016, 9, 20)    # Model run date YYYY,MM,DD
hour = 3                # Model initialization hour
fxx = range(1)            # Forecast hour range (Right now there 18 hours forecast including hour
                           # which indicates the current condition of that hour. So the range for
                           # the data should be range(19). But as we are looking for the actual that
                           # at each hour so we will use only range(1) to get f00.
                           # Note: Valid Time is the Date and Hour plus fxx.

model_name = 'hrrr'        # ['hrrr' this is the operational HRRR and collected from NOMADS server,
                           # 'hrrrX' this is the experimental HRRR and collected from NOAA ESRL,
                           # 'hrrrAK' this is HRRR Alaska and collected from NOAA ESRL]

field = 'sfc'              # ['sfc', 'prs']

var_to_match = 'APCP'      # must be part of a line in the .idx file
                           # Check this URL for a sample of variable names you can match:
                           # https://api.mesowest.utah.edu/archive/HRRR//oper/sfc/20170725/hrrr.t01z.wrfsfcf00.grib2.idx
# =============================================================================
# =============================================================================
#create directories to store data
direct = './HRRR_Archive_'+start_date_time_str.strftime('%Y%m%d')+'_'+end_date_time_str.strftime('%Y%m%d')
os.makedirs(direct)
os.makedirs(direct+"/GRIB2")
os.makedirs(direct+"/TIF")
os.makedirs(direct+"/ASC")


while step_date_time <= end_date_time_str:
    print step_date_time






    for i in fxx:
        # Rename the file based on the info from above (e.g. 20170310_h00_f00_TMP_2_m_above_ground.grib2)
        outfile_grib = direct + '/GRIB2/%s_h%02d_f%02d_%s.grib2' % (step_date_time.strftime('%Y%m%d'), step_date_time.hour, i, var_to_match.replace(':', '_').replace(' ', '_'))
        outfile_tif = direct + '/TIF/%s_h%02d_f%02d_%s.tif' % (step_date_time.strftime('%Y%m%d'), step_date_time.hour, i, var_to_match.replace(':', '_').replace(' ', '_'))
        outfile_tif_prj = direct + '/TIF/%s_h%02d_f%02d_%s_projected.tif' % (step_date_time.strftime('%Y%m%d'), step_date_time.hour, i, var_to_match.replace(':', '_').replace(' ', '_'))
        outfile_study_area_tif = direct + '/TIF/%s_%02d.tif' % (step_date_time.strftime('%Y%m%d'), step_date_time.hour)
        outfile_study_area_ASC = direct + '/ASC/%s_%02d.asc' % (step_date_time.strftime('%Y%m%d'), step_date_time.hour)

        # Model file names are different than model directory names.
        if model_name == 'hrrr':
            model_dir = 'oper'
        elif model_name == 'hrrrX':
            model_dir = 'exp'
        elif model_name == 'hrrrAK':
            model_dir = 'alaska'

        # This is the URL with the Grib2 file metadata. The metadata contains the byte
        # range for each variable. We will identify the byte range in step 2.
        sfile = 'https://api.mesowest.utah.edu/archive/HRRR/%s/%s/%s/%s.t%02dz.wrf%sf%02d.grib2.idx' \
                 % (model_dir, field, step_date_time.strftime('%Y%m%d'), model_name, step_date_time.hour, field, i)
        # This is the URL to download the full GRIB2 file. We will use the cURL command
        # to download the variable of interest from the byte range in step 3.
        pandofile = 'https://pando-rgw01.chpc.utah.edu/HRRR/%s/%s/%s/%s.t%02dz.wrf%sf%02d.grib2' \
                 % (model_dir, field, step_date_time.strftime('%Y%m%d'), model_name, step_date_time.hour, field, i)


        # 1) Open the Metadata URL and read the lines

        request = urllib2.Request(sfile)
        response = urllib2.urlopen(request, context = ssl._create_unverified_context())
        # idxpage = urllib2.urlopen(sfile) #certificates are not validating correctly
        lines = response.readlines()

        # 2) Find the byte range for the variable. First find where the
        #    variable is located. Keep a count (gcnt) so we can get the end
        #    byte range from the next line.
        gcnt = 0
        for g in lines:
            expr = re.compile(var_to_match)
            if expr.search(g):
                parts = g.split(':')
                rangestart = parts[1]
                parts = lines[gcnt+1].split(':')
                rangeend = int(parts[1])-1
                print 'range:', rangestart, rangeend
                byte_range = str(rangestart) + '-' + str(rangeend)

                # 3) When the byte range is discovered, use cURL to download.
                os.system('curl -s -o %s --range %s %s' % (outfile_grib, byte_range, pandofile))
                os.system('curl -s -o %s --range %s %s' % (outfile_tif, byte_range, pandofile))
                print 'downloaded', outfile_tif


            gcnt += 1

        # project the tiff file to the desired projection using Gdalwarp
        os.system('gdalwarp %s %s -t_srs "+proj=utm +zone=18 +datum=NAD83" -tr 500 500' % (outfile_tif, outfile_tif_prj))

        # extract the required information for the study area using Gdalwarp
        os.system('gdalwarp -cutline %s -crop_to_cutline %s %s' % (shp_filename, outfile_tif_prj, outfile_study_area_tif)) # removed "-dstalpha" as it produced 2 Band dataset

        # convert the tiff
        os.system('gdal_translate -co force_cellsize=true  -of AAIGrid %s %s' % (outfile_study_area_tif, outfile_study_area_ASC))

    step_date_time = step_date_time + timedelta(hours=1)







