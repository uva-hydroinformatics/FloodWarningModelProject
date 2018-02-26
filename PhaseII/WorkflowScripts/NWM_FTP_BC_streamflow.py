import os
from ftplib import FTP
from datetime import datetime, timedelta
from pydap.client import open_url
from pydap.exceptions import ServerError


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
            return hour
        else:
            print "Back up method - Failed to open : %s" % url
            return get_hrrr_data_info(current_date_utc, delta_time + 1)
    except ServerError:
        print "Failed to open : %s" % url
        return get_hrrr_data_info(current_date_utc, delta_time + 1)

##################################################################################################
# ***************************************** Main Program *****************************************
##################################################################################################

def main():
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

    # check the available hrrr forecast rainfall data to retrieve the appropriate boundary condition
    # from the NWM
    target_date_time_utc = datetime.utcnow()
    hour_utc = get_hrrr_data_info(target_date_time_utc, 0)

    # by default, all the data folder will be downloaded. In case you would like to download a specific
    # folder, change the following line to "target_data_folder = ["NAME OF FOLDER"]".
    # The currently available folders are ['analysis_assim', 'forcing_analysis_assim',
    # 'forcing_medium_range', 'forcing_short_range', 'long_range_mem1', 'long_range_mem2',
    # 'long_range_mem3', 'long_range_mem4', 'medium_range', 'short_range', 'usgs_timeslices']
    target_data_folder = ['analysis_assim', 'short_range']

    # download the available data for the target date and data folder/s
    for data_type in target_data_folder:
        data_type_path = "/pub/data/nccf/com/nwm/prod/nwm."+target_date+"/"+data_type+"/"
        dest_data_path = destination+"/"+target_date+"/"+data_type
        if not os.path.exists(dest_data_path):
            os.makedirs(dest_data_path)
        ftp.cwd(data_type_path)
        filelist=ftp.nlst()

        # download the available files in the target folder/s
        for file in filelist:
            file_info = file.split(".")
            if file_info[1] == 't'+str(hour_utc)+'z' and file_info[3] == "channel_rt":
                ftp.retrbinary("RETR "+file, open(os.path.join(dest_data_path,file),"wb").write)
                print file + " downloaded"

    print "Done downloading the NWM data for the target data!"

if __name__ == "__main__":
    main()
