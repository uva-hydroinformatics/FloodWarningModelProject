import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import os
import pytz
from datetime import datetime as dt


def utc_to_local(local_tz, utc_dt):
    utc_dt = dt.strptime(utc_dt, '%Y-%m-%dT%H:%M:%SZ')
    local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt).strftime('%Y-%m-%dT%H:%M:%SZ')

def local_to_utc(local_tz, local_dt):
    local_dt = dt.strptime(local_dt, '%Y-%m-%dT%H:%M:%SZ')
    local_dt = local_tz.localize(local_dt)
    utc_dt = local_dt.astimezone (pytz.utc)
    return utc_dt.strftime('%Y-%m-%dT%H:%M:%SZ')


##################################################################################################
# ***************************************** Main Program *****************************************
##################################################################################################


# modelled start and end date/time in the local time zone using the format of %Y-%m-%dT%H:%M:%SZ
start_datetime = "2016-10-07T00:00:00Z"
end_datetime = "2016-10-24T00:00:00Z"
local_tz = pytz.timezone('US/Eastern')

# read the USGS station observations
data_directory = "./Data adjusted to the vertical datum/"

# create empty list to append the filename in the target directory
filename_var = []

# extract the file names and convert them to variable with dataframes include each file info
for filename in os.listdir(data_directory):
    filename_var.append("Gage_Info_"+filename.split(".")[1].split("@")[-1])
    vars()[filename_var[-1]] = pd.read_csv(data_directory+filename, low_memory=False, skiprows=14)
print filename_var

# covert the start and end date/time to UTC
start_datetime_utc = local_to_utc(local_tz, start_datetime)
end_datetime_utc = local_to_utc(local_tz, end_datetime)

print start_datetime_utc, end_datetime_utc

raw_input("TEST")


# # for i in range(len(filename_var)):
# plt.plot( eval(filename_var[0])['Water Level (m)'][:5]) #eval(filename_var[0])['ISO 8601 UTC'][:1000],
# plt.show()







# get index --> eval(filename_var[0]).index[eval(filename_var[0])['ISO 8601 UTC'] == '2003-10-01T05:00:00Z'].tolist()

# extract column value based on another column pandas dataframe --> eval(filename_var[0]).loc[eval(filename_var[0])['ISO 8601 UTC'] == '2003-10-01T05:00:00Z', 'Water Level (m)']

# d= dt.strptime((eval(filename_var[0])['ISO 8601 UTC'][0]), '%Y-%m-%dT%H:%M:%SZ')
# d.strftime('%Y-%m-%d')
# Out[20]: '2003-10-01'

# eval(filename_var[0])[eval(filename_var[0])['ISO 8601 UTC'].astype(str).str.contains('2003-10-01T04:00:00Z')]

# '2003-10-01T04:00:00Z' in eval(filename_var[0]).values
