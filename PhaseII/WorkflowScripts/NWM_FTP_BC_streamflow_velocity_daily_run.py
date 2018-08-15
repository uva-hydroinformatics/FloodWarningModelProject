import os
from ftplib import FTP
from datetime import datetime, timedelta
from pydap.client import open_url
from pydap.exceptions import ServerError
import xarray as xr
import numpy as np
import time


def write_tuflow_bc_ts1_file(file_name, dictionary, array_name):
    bc_file = open(file_name+'.ts1', 'w')
    bc_file.write("! Forecasted streamflow in m3/s boundary condition from the NWM\n")
    bc_file.write("11,19\n")
    bc_file.write("Start_Index,1,1,1,1,1,1,1,1,1,1,1\n")
    line_number = str(len(array_name))
    bc_file.write("End_Index")
    for dic_item in dictionary:
        bc_file.write(","+line_number)
    bc_file.write("\n")
    bc_file.write("Time (min)")
    for key in dictionary:
        bc_file.write(','+ key)
    bc_file.write("\n")
    hr = 0
    for i in range(len(array_name)):
        bc_file.write(str(hr * 60.0))
        for j in range(len((array_name)[i])):
            bc_file.write(',' + str(array_name[i][j]))
        bc_file.write("\n")
        hr += 1
    bc_file.close()


##################################################################################################
# ***************************************** Main Program *****************************************
##################################################################################################


# define the NWM main FTP URL.
ftp = FTP("ftpprd.ncep.noaa.gov")
ftp.login()

# dictionary to includes the boundary condition feature names and the corresponding Reach ID
# or COMID from the NWM that represent the streamflow for the model boundary
bc_items = {"10_35C":"11583062","11_34C":"11583342","1_42C":"8746119","2_41C":"8745499",
            "3_40C":"8742901","4_39C":"8741071","5_38C":"8725803","6_44C":"8724029",
            "7_37C":"8723783","8_43C":"8723533","9_36C":"8719585"}

ext_data_rt = np.zeros((3,11))  # extracted realtime streamflows from t00, t01, and t02
ext_data_fc = np.zeros((18,11))  # extracted forecasted streamflows from the short range 18 lyrs
ext_data = np.zeros((21,11))  # extracted forecasted streamflows from the short range 18 lyrs
ext_realtime_data = np.zeros((24,11))  # extracted realtime streamflows from previous day
i=0
j=0


# data can be downloaded only for the current day and one day older as we are using the official
# website for the NWM. Date and time are in UTC time zone.
# "timedelta(days=0)": download the current date
# "timedelta(days=1)": download one day older from the current date
target_date_time_utc = datetime.utcnow()
#target_date = str(target_date_time_utc.date()- timedelta(days=0)).replace("-","")

# check the available hrrr forecast rainfall data to retrieve the appropriate boundary condition
# from the NWM
## hour_utc, target_date = get_hrrr_data_info(target_date_time_utc, 0)
date = target_date_time_utc - timedelta(days=1)
target_date = datetime.strftime(date, "%Y%m%d")

# create a local folder to store the downloaded data.
destination = target_date+"/"
if not os.path.exists(destination):
    os.makedirs(destination)

# get the whole list of the available data for the target day
nwm_data="/pub/data/nccf/com/nwm/prod/nwm."+target_date+"/"
ftp.cwd(nwm_data)

# by default, all the data folder will be downloaded. In case you would like to download
# a specific folder, change the following line from "target_data_folder = ftp.nlst()" to
# "target_data_folder = ["NAME OF FOLDER"]".
# The currently available folders are ['analysis_assim', 'forcing_analysis_assim',
# 'forcing_medium_range', 'forcing_short_range', 'long_range_mem1', 'long_range_mem2',
# 'long_range_mem3', 'long_range_mem4', 'medium_range', 'short_range', 'usgs_timeslices']
target_data_folder = ['analysis_assim']

# download the available data for the target date and data folder/s
for data_type in target_data_folder:
    if data_type == 'analysis_assim':
        data_type_path = nwm_data+data_type+"/"
        dest_data_path = destination+data_type
        if not os.path.exists(dest_data_path):
            os.makedirs(dest_data_path)
        ftp.cwd(data_type_path)
        filelist=ftp.nlst()

        # download the available files in the target folder/s
        hr = 0
        for file in filelist:
            file_info = file.split(".")
            if file_info[1] == 't'+str(hr).zfill(2)+'z' and file_info[3] == "channel_rt" \
                    and file_info[4] == "tm00":
                ftp.retrbinary("RETR "+file, open(os.path.join(dest_data_path,file),"wb").write)
                ds = xr.open_dataset(os.path.join(dest_data_path,file))
                df = ds.to_dataframe()
                for val in bc_items.itervalues():
                    x = df.ix[int(val), ['streamflow']]
                    ext_realtime_data[i][j] = str(x).split(" ")[-1]
                    j += 1
                ds.close()
                j = 0
                i += 1
                hr += 1

                print file + " downloaded"

# write the appropriate boundary condition file for the 2D model
write_tuflow_bc_ts1_file(destination+'Realtime_RF_Point', bc_items, ext_realtime_data)
print "Done downloading and preparing the NWM data as boundary condition file for the 2D model for "+target_date+"!"


