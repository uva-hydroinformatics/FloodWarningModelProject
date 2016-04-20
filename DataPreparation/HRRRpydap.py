# -*- coding: utf-8 -*-
"""
Created on Mon Mar 21 19:49:13 2016

@author: Gina
"""

from pydap.client import open_url
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib


dtime_now=datetime.utcnow()
date=datetime.strftime(dtime_now,"%Y%m%d")
UTC_hour=int(datetime.strftime(dtime_now, "%H"))-4
print(dtime_now)
print(UTC_hour)
#need to go back 4 hours need to monitor 
def getData(date,UTC_hour):
    try:
        dataset=open_url('http://nomads.ncep.noaa.gov:9090/dods/hrrr/hrrr%s/hrrr_sfc_%sz'%(date,str(UTC_hour)))
        return (dataset)
    except:
        last_hour=UTC_hour-1
        dataset=open_url('http://nomads.ncep.noaa.gov:9090/dods/hrrr/hrrr%s/hrrr_sfc_%sz'%(date,str(last_hour)))
        return (dataset) 
#add print of which hour is used
    
dataset=getData(date,UTC_hour)

print(type(dataset)) 
"""pydap.model.DatasetType """

print("dataset keys: ")
print(dataset.keys()) 
"""list of vars, time, lev, lat, lon"""

var="apcpsfc"
precip=dataset[var]
#print(type(precip)) 
"""pydap.model.GridType"""

print(precip.dimensions) 
"""dimensions are 'time','lat','lon'"""

"""convert dimensions to grid points, as per http://nomads.ncdc.noaa.gov/guide/?name=advanced"""
def gridpt(myVal, initVal, aResVal):
    gridVal=int((myVal-initVal)/aResVal)
    return gridVal


Lon1=-78.507
Lat1=38.033
#location of Central California, rain forecasted here 4/8/16

initLon=-134.09612700000
aResLon= 0.029 

initLat=21.14067100000
aResLat=0.027

gridLat=gridpt(Lat1,initLat,aResLat)
gridLon=gridpt(Lon1,initLon,aResLon)

print(precip.time)
"""time is an array of shape 16,0 and dtype=float64"""
#change first time to 0
#try to make time steps dynamic incase HRRR is ever able to forecast further
grid=precip[0:16,gridLat,gridLon]
print(grid)
"""shows precip values and axes (time [decimal days])"""

print(grid.array[:])
"""shows precip values only"""

"""precip.time[:] returns a list of times in decimal days"""
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
