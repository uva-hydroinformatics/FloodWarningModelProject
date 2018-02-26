import os
from ftplib import FTP
from datetime import datetime, timedelta

# define the NWM main FTP URL.
ftp = FTP("ftpprd.ncep.noaa.gov")
ftp.login()

# create a local folder to store the downloaded data.
destination="./NWM/"
if not os.path.exists(destination):
    os.makedirs(destination)

# data can be downloaded only for the current day and one day older as we are using the official
# website for the NWM.
# "timedelta(days=0)": download the current date
# "timedelta(days=1)": download one day older from the current date
target_date = str(datetime.now().date()- timedelta(days=0)).replace("-","")
if not os.path.exists(destination+"/"+target_date):
    os.makedirs(destination+"/"+target_date)

# get the whole list of the available data for the target day
nwm_data="/pub/data/nccf/com/nwm/prod/nwm."+target_date+"/"
ftp.cwd(nwm_data)

# by default, all the data folder will be downloaded. In case you would like to download a specific
# folder, change the following line to "target_data_folder = ["NAME OF FOLDER"]".
# The currently available folders are ['analysis_assim', 'forcing_analysis_assim',
# 'forcing_medium_range', 'forcing_short_range', 'long_range_mem1', 'long_range_mem2',
# 'long_range_mem3', 'long_range_mem4', 'medium_range', 'short_range', 'usgs_timeslices']
target_data_folder = ftp.nlst()
print target_data_folder

# download the available data for the target date and data folder/s
for data_type in target_data_folder:
    data_type_path = "/pub/data/nccf/com/nwm/prod/nwm."+target_date+"/"+data_type+"/"
    dest_data_path = destination+"/"+target_date+"/"+data_type
    if not os.path.exists(dest_data_path):
        os.makedirs(dest_data_path)
    ftp.cwd(data_type_path)
    filelist=ftp.nlst()
    print filelist

    # download the available files in the target folder/s
    for file in filelist:
        ftp.retrbinary("RETR "+file, open(os.path.join(dest_data_path,file),"wb").write)
        print file + " downloaded"

print "Done downloading the NWM data for the target data!"
