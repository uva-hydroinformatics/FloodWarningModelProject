# -*- coding: utf-8 -*-
"""
This program retrieves data from the NOAA NOMADS repository, using the HRRRR model.
The forecasted surface precipitation is obtained asa dataset for the newest available 
UTC hour. Given a latitude and longitude in decimal degrees, an array of surface 
precipitation for the corresponding grid-relative location is printed as a time series
for a specified number of forecast hours.
Author: Gina O'Neil
"""
from pydap.client import open_url
import datetime as dt
from datetime import timedelta
from scipy.io import netcdf
from netCDF4 import Dataset
import matplotlib.dates
import csv

#Get current UTC date and time
dtime_now = dt.datetime.utcnow()
print(dtime_now)

#Get newest available dataset by trying (current date-time - delta time) until
#a dataset is available for that hour. This corrects for inconsistent posting
#of HRRR datasets to repository
def getData(current_dt):
    delta_T = 0
    while True:    
        try:
            dtime_fix = dtime_now - dt.timedelta(hours = delta_T)
            date = dt.datetime.strftime(dtime_fix,"%Y%m%d")
            fc_hour = dt.datetime.strftime(dtime_fix, "%H")            
            hour = str(fc_hour)
            url = 'http://nomads.ncep.noaa.gov:9090/dods/hrrr/hrrr%s/hrrr_sfc_%sz'%(date,hour)
            dataset = open_url(url)
            False
            return(dataset, url, date, hour)
        except:
            delta_T += 1
    
dataset, url, date, hour = getData(dtime_now)
print ("Retrieving forecast data from: %s " %(url))
# 'dataset' is pydap.model.DatasetType    
# dataset keys are all forecast products (variables) and time, lev, lat, lon

# access gridded data for surface precipitation variable with corresponding expression
var = "apcpsfc"
precip = dataset[var] #grid dimensions are time, lat, lon

#convert dimensions to grid points, as per http://nomads.ncdc.noaa.gov/guide/?name=advanced
def gridpt(myVal, initVal, aResVal):
    gridVal = int((myVal-initVal)/aResVal)
    return gridVal

#Miami International Airport coordinates 
Lon1 = -80.2855555556
Lat1 = 25.7941666667


#given in HRRR dataset metadata
initLon = -134.09612700000
aResLon = 0.029 

initLat = 21.14067100000
aResLat = 0.027

#compute grid-relative points
gridLat = gridpt(Lat1,initLat,aResLat)
gridLon = gridpt(Lon1,initLon,aResLon)

#get all available timesteps for forecast data
last_T = len(precip.time[:])

#Select dimensions in dataset
grid = precip[0:last_T,gridLat,gridLon]

#shows precip values only
print(grid.array[:])

#extract precip values and account for missing values
vals_mm = [ v[0][0] if v !=9.999e20 else None for v in grid.array[:] ]
#convert precip depths from mm to in
vals_in = [ v * 0.0393701 for v in vals_mm]

ts = [ t for t in precip.time[:] ]
#convert decimal days to date-time and format
ts_dates = [ matplotlib.dates.num2date(t-1) for t in ts] 
hours = [ dt.datetime.strftime(ts_d, "%Y-%m-%d utc hour: %H") for ts_d in ts_dates]

with open("Precip_Forecast_%s_%sz.csv"%(date, hour), "w") as results:    
    res_csv = csv.writer(results)
    res_csv.writerow(["Date-Time", "Latitude", "Longitude", "Precipitation [mm]", "Precipitation [in]"])
    for j in range(len(vals_mm)):
        res_csv.writerow([hours[j],str(Lat1), str(Lon1), vals_mm[j], vals_in[j]])
results.close() 

"""
w_nc_fid = Dataset('precip_test.nc', 'w', format='NETCDF4')
w_nc_fid.description = "HRRR forecasted surface precipitation at %f latitude %f longitude" %\
                      (Lat1, Lon1)
# Using our previous dimension info, we can create the new time dimension
# Even though we know the size, we are going to set the size to unknown
w_nc_fid.createDimension('time', None)
w_nc_dim = w_nc_fid.createVariable('time', nc_fid.variables['time'].dtype,\
                                   ('time',))
# You can do this step yourself but someone else did the work for us.
for ncattr in nc_fid.variables['time'].ncattrs():
    w_nc_dim.setncattr(ncattr, nc_fid.variables['time'].getncattr(ncattr))
# Assign the dimension data to the new NetCDF file.
w_nc_fid.variables['time'][:] = time
w_nc_var = w_nc_fid.createVariable('air', 'f8', ('time'))
w_nc_var.setncatts({'long_name': u"mean Daily Air temperature",\
                    'units': u"degK", 'level_desc': u'Surface',\
                    'var_desc': u"Air temperature",\
                    'statistic': u'Mean\nM'})
w_nc_fid.variables['air'][:] = air[time_idx, lat_idx, lon_idx]
w_nc_fid.close()  # close the new file
"""
