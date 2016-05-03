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

#Get current UTC date and time
dtime_now = dt.datetime.utcnow()
#correct for lag time in dataset posting to HRRR repository
lag_hr = 1
dtime_fix = dtime_now - dt.timedelta(hours = lag_hr)
date=dt.datetime.strftime(dtime_fix,"%Y%m%d")
fc_hour=dt.datetime.strftime(dtime_fix, "%H")

#open newest available dataset
def getData(date,fc_hour):
    try:
        url = 'http://nomads.ncep.noaa.gov:9090/dods/hrrr/hrrr%s/hrrr_sfc_%sz'%(date,str(fc_hour))
        dataset=open_url(url)
        return(dataset, url)
    except:
        old_hour = fc_hour - 1
        url = 'http://nomads.ncep.noaa.gov:9090/dods/hrrr/hrrr%s/hrrr_sfc_%sz'%(date,str(old_hour))
        dataset=open_url(url)
        return (dataset, url)    
    
dataset, url=getData(date,fc_hour)
print ("Retrieving forecast data from: %s " %(url))
# 'dataset' is pydap.model.DatasetType    
# dataset keys are all forecast products (variables) and time, lev, lat, lon

# access gridded data for surface precipitation variable with corresponding expression
var="apcpsfc"
precip=dataset[var] #grid dimensions are time, lat, lon

#convert dimensions to grid points, as per http://nomads.ncdc.noaa.gov/guide/?name=advanced
def gridpt(myVal, initVal, aResVal):
    gridVal=int((myVal-initVal)/aResVal)
    return gridVal

Lon1=-78.507
Lat1=38.033
#Charlottesville

#given in HRRR dataset metadata
initLon=-134.09612700000
aResLon= 0.029 

initLat=21.14067100000
aResLat=0.027

gridLat=gridpt(Lat1,initLat,aResLat)
gridLon=gridpt(Lon1,initLon,aResLon)

#get all available timesteps for forecast data
last_T=len(precip.time[:])

grid=precip[0:last_T,gridLat,gridLon]
print(grid)
# grid shows precip values and axes of time [decimal days]

print(grid.array[:])
#shows precip values only

"""attempt to change time steps from decimal days to datetime format and create list of precip values

ts=[]
values=[]
timeseries=[]
for time in range(len(grid.array[:])):
    for lat in range(len(grid.array[time][:])):
        for lon in range(len(grid.array[time][lat][:])):
            val=grid.array[time][lat][lon]
            values.append(val)
for t in precip.time[:]:
    ts.append(t)
for i in range(len(ts)):
    fix=matplotlib.dates.num2date(ts[i]) 
    timeseries.append(fix)
print(values)
print(ts)
print(grid.time) #still don't know how to format into datetime
fixed=matplotlib.dates.num2date(precip.time[:])
print(grid.apcpsfc)

"""
