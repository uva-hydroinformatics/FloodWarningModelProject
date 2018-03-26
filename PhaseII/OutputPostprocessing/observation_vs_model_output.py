import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import os
import pytz
from datetime import datetime as dt, timedelta


def utc_to_local(local_tz, utc_dt):
    utc_dt = dt.strptime(utc_dt, '%Y-%m-%dT%H:%M:%SZ')
    local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt).strftime('%Y-%m-%dT%H:%M:%SZ')


def local_to_utc(local_tz, local_dt):
    local_dt = dt.strptime(local_dt, '%Y-%m-%dT%H:%M:%SZ')
    local_dt = local_tz.localize(local_dt)
    utc_dt = local_dt.astimezone (pytz.utc)
    return utc_dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def plot_obs_vs_mod_output(x, y, x_output, y_output, x_output_original, y_output_original, gage_id, start_data_utc,
                           end_data_utc, directory, grid_res, run_version):
    matplotlib.rcParams.update({'font.size': 8})
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(x, y, '.', label='Observation')
    ax.plot(x_output, y_output, color='r', label='Simulation '+grid_res+' version:'+run_version)
    ax.plot(x_output_original, y_output_original, color='g', label='Simulation '+grid_res+' version:Original Model')
    ax.set_xlim(x.values[0], x.values[-1])
    ax.set_xlabel("Date/Time in UTC", fontweight='bold')
    ax.set_ylabel("Water Elevation (m)", fontweight='bold')
    ax.set_title("USGS Gage "+gage_id+" ("+start_data_utc+" - "+end_data_utc+")",
         fontweight='bold', fontsize=10)
    plt.legend()
    plt.xticks(rotation=90)
    fig.tight_layout()
    plt.show()
    fig.savefig(directory+'/'+gage_id+'.png')


###################################################################################################
# ***************************************** Main Program *****************************************#
###################################################################################################
# modelled start and end date/time in the local time zone using the format of %Y-%m-%dT%H:%M:%SZ
start_datetime = "2016-10-07T00:00:00Z"
end_datetime = "2016-10-24T00:00:00Z"
local_tz = pytz.timezone('US/Eastern')

# locate the USGS station observations
data_directory = "./Data adjusted to the vertical datum/"

# locate the model output time series file
output_file = "VU_30m_HPC_GPU_Nicole_2016_013_PO.csv"
grid_res = output_file.split('_')[1]
run_version = output_file.split('_')[6]

# locate the old model version output
output_file_original = "VU_30m_HPC_GPU_Nicole_2016_010_PO.csv"


# plots directory
destination = output_file.split(".")[0]
if not os.path.exists(destination):
    os.makedirs(destination)


# create empty list to append the filename in the target USGS observation data directory
filename_var = []

# extract the file names and convert them to variable with dataframes include each file info
for filename in os.listdir(data_directory):
    filename_var.append("Gage_Info_"+filename.split(".")[1].split("@")[-1])
    vars()[filename_var[-1]] = pd.read_csv(data_directory+filename, low_memory=False, skiprows=14)

# convert the start and end date/time to UTC
start_datetime_utc = local_to_utc(local_tz, start_datetime)
end_datetime_utc = local_to_utc(local_tz, end_datetime)

# convert the model output to variable with dataframes and convert the hours to date/time
output_timeseries = pd.read_csv(output_file, low_memory=False, usecols=range(1,20))
output_timeseries_original = pd.read_csv(output_file_original, low_memory=False, usecols=range(1,20))
x_output = []
x_output_original = []
for hours in output_timeseries[[0]].values[1:]:
    x_output.append(dt.strptime(start_datetime_utc, '%Y-%m-%dT%H:%M:%SZ') +
                    timedelta(hours=float(hours)))

for hours in output_timeseries_original[[0]].values[1:]:
    x_output_original.append(dt.strptime(start_datetime_utc, '%Y-%m-%dT%H:%M:%SZ') +
                    timedelta(hours=float(hours)))

# get the index for the start and end data from the observation dataset to retrieve
# the corresponding water elevation.

# loop through all of the available USGS station and create the plots
for station in filename_var:
    if start_datetime_utc in eval(station).values and \
            end_datetime_utc in eval(station).values:
        start_datetime_index = int(
            eval(station).index[eval(station)
                                        ['ISO 8601 UTC'] == start_datetime_utc].tolist()[0])


        end_datetime_index = int(
            eval(station).index[eval(station)
                                        ['ISO 8601 UTC'] == end_datetime_utc].tolist()[0])


        eval(station)['ISO 8601 UTC'] = pd.to_datetime(eval(station)['ISO 8601 UTC'],
                                                                format='%Y-%m-%dT%H:%M:%SZ')
        x = eval(station)['ISO 8601 UTC'][(start_datetime_index):(end_datetime_index)]
        y = eval(station)['Water Level (m)'][(start_datetime_index):(end_datetime_index)]
        gage_id = station.split("_")[2]
        start_data_utc = str(x.values[0]).split("T")[0]
        end_data_utc = str(x.values[-1]).split("T")[0]

        # list to include the USGS stations that do not have modeled timeseries by the model
        station_wo_modeled_wl = []

        # change the range to range(1,10) for the new version of the model i.e. 013 and up
        for i in range(1,10):
            if '0'+str(int(output_timeseries[[i]].values[0])) == gage_id:
                y_output = []
                for wl_val in output_timeseries[[i]].values[1:]:
                    y_output.append(float(wl_val))

        for i in range(1,10):
            if '0'+str(int(output_timeseries_original[[i]].values[0])) == gage_id:
                y_output_original = []
                for wl_val in output_timeseries_original[[i]].values[1:]:
                    y_output_original.append(float(wl_val))

                plot_obs_vs_mod_output(x, y, x_output, y_output, x_output_original, y_output_original, gage_id,
                                       start_data_utc, end_data_utc, destination, grid_res, run_version)
            else:
                if gage_id not in station_wo_modeled_wl:
                    print 'No modeled water elevation timeseries for USGS station No.'+gage_id
                    station_wo_modeled_wl.append(gage_id)
    else:
        print "No observation available for the given start and end dates at USGS No."+\
              station.split("_")[-1]