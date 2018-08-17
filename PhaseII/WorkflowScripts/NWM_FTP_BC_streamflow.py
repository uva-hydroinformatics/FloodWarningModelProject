import os
from ftplib import FTP
from datetime import datetime, timedelta
from pydap.client import open_url
from pydap.exceptions import ServerError
import xarray as xr
import numpy as np
import time


def get_hrrr_data_info(current_date_utc, delta_time):
    dtime_fix = current_date_utc - timedelta(hours=delta_time)
    date = datetime.strftime(dtime_fix, "%Y%m%d")
    fc_hour = datetime.strftime(dtime_fix, "%H")
    hour = str(fc_hour)
    url = 'http://nomads.ncep.noaa.gov:9090/dods/hrrr/hrrr%s/hrrr_sfc.t%sz' % (date, hour)
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


def write_tuflow_bc_ts1_file(file_name, dictionary, array_name):
    bc_file = open(file_name + '.ts1', 'w')
    bc_file.write("! Forecasted streamflow in m3/s boundary condition from the NWM\n")
    bc_file.write("11,19\n")
    bc_file.write("Start_Index,1,1,1,1,1,1,1,1,1,1,1\n")
    bc_file.write("End_Index,19,19,19,19,19,19,19,19,19,19,19\n")
    bc_file.write("Time (min)")
    for key in dictionary:
        bc_file.write(',' + key)
    bc_file.write("\n")
    hr = 0
    bc_file.write(str(hr * 60.0))
    for j in range(len((array_name)[0])):
        bc_file.write(',' + str(array_name[0][j]))
    bc_file.write("\n")
    hr += 1
    for i in range(3, len(array_name)):
        bc_file.write(str(hr * 60.0))
        for j in range(len((array_name)[i])):
            bc_file.write(',' + str(array_name[i][j]))
        bc_file.write("\n")
        hr += 1
    bc_file.close()


##################################################################################################
# ***************************************** Main Program *****************************************
##################################################################################################

def main():
    # define the NWM main FTP URL.
    ftp = FTP("ftpprd.ncep.noaa.gov")
    ftp.login()

    # dictionary to includes the boundary condition feature names and the corresponding Reach ID
    # or COMID from the NWM that represent the streamflow for the model boundary
    bc_items = {"10_35C": "11583062", "11_34C": "11583342", "1_42C": "8746119", "2_41C": "8745499",
                "3_40C": "8742901", "4_39C": "8741071", "5_38C": "8725803", "6_44C": "8724029",
                "7_37C": "8723783", "8_43C": "8723533", "9_36C": "8719585"}

    ext_data_rt = np.zeros((3, 11))  # extracted realtime streamflows from t00, t01, and t02
    ext_data_fc = np.zeros((18, 11))  # extracted forecasted streamflows from the short range 18 lyrs
    ext_data = np.zeros((21, 11))  # extracted forecasted streamflows from the short range 18 lyrs
    i = 0
    j = 0

    # create a local folder to store the downloaded data.
    destination = "../bc_dbase/NWM/"
    if not os.path.exists(destination):
        os.makedirs(destination)

    # data can be downloaded only for the current day and one day older as we are using the official
    # website for the NWM. Date and time are in UTC time zone.
    # "timedelta(days=0)": download the current date
    # "timedelta(days=1)": download one day older from the current date
    target_date_time_utc = datetime.utcnow()
    target_date = str(target_date_time_utc.date() - timedelta(days=0)).replace("-", "")

    if not os.path.exists(destination + "/" + target_date):
        os.makedirs(destination + "/" + target_date)

    # get the whole list of the available data for the target day
    nwm_data = "/pub/data/nccf/com/nwm/prod/nwm." + target_date + "/"
    ftp.cwd(nwm_data)

    # check the available hrrr forecast rainfall data to retrieve the appropriate boundary condition
    # from the NWM
    hour_utc = get_hrrr_data_info(target_date_time_utc, 0)

    # by default, all the data folder will be downloaded. In case you would like to download
    # a specific folder, change the following line from "target_data_folder = ftp.nlst()" to
    # "target_data_folder = ["NAME OF FOLDER"]".
    # The currently available folders are ['analysis_assim', 'forcing_analysis_assim',
    # 'forcing_medium_range', 'forcing_short_range', 'long_range_mem1', 'long_range_mem2',
    # 'long_range_mem3', 'long_range_mem4', 'medium_range', 'short_range', 'usgs_timeslices']
    target_data_folder = ['analysis_assim', 'short_range']

    # download the available data for the target date and data folder/s
    for data_type in target_data_folder:
        data_type_path = nwm_data + data_type + "/"
        dest_data_path = destination + "/" + target_date + "/" + data_type
        if not os.path.exists(dest_data_path):
            os.makedirs(dest_data_path)
        ftp.cwd(data_type_path)
        filelist = ftp.nlst()

        # check at least one file is available for the specific hour in hour_utc
        if data_type == 'analysis_assim':
            while not "nwm.t" + str(hour_utc) + "z.analysis_assim.channel_rt.tm00.conus.nc" in filelist:
                print "Waiting for the updated data in analysis_assim"
                time.sleep(30)
                filelist = ftp.nlst()

        if data_type == 'short_range':
            while not "nwm.t" + str(hour_utc) + "z.short_range.channel_rt.f001.conus.nc" in filelist:
                print "Waiting for the updated data in short_range"
                time.sleep(30)
                filelist = ftp.nlst()

        # download the available files in the target folder/s
        for file in filelist:
            file_info = file.split(".")
            if file_info[1] == 't' + str(hour_utc) + 'z' and file_info[3] == "channel_rt":
                ftp.retrbinary("RETR " + file, open(os.path.join(dest_data_path, file), "wb").write)
                ds = xr.open_dataset(os.path.join(dest_data_path, file))
                df = ds.to_dataframe()
                for val in bc_items.itervalues():
                    x = df.ix[int(val), ['streamflow']]
                    ext_data[i][j] = str(x).split(" ")[-1]
                    j += 1
                j = 0
                i += 1

                print file + " downloaded"

    # write the appropriate boundary condition file for the 2D model
    write_tuflow_bc_ts1_file(destination + 'Forecast_RF_Point', bc_items, ext_data)
    print "Done downloading and preparing the NWM data as boundary condition file for the 2D model!"


if __name__ == "__main__":
    main()
