from hec.script import *
from hec.heclib.dss import *
from hec.heclib.util import *
from hec.io import TimeSeriesContainer
import java
import os
import sys


print "beginning script execution"
dates = [ ]
times = [ ]
precip = [ ]


#csv_dir = "C:/Users/CIVIL/Desktop/HEC-HMS_EXAMPLE/HEC-HMS_EXAMPLE/20170522_0000/CSV//"
csv_dir = sys.argv[1]
os.chdir(csv_dir)

#find all csv files in directory
for f in os.listdir(csv_dir):
	if f.endswith(".csv"):
		print f
		#fin = open ( "C:\Users\CIVIL\Desktop\HEC-HMS_EXAMPLE\HEC-HMS_EXAMPLE\BC_latest\CSV/%s" %( f) , 'r')
		fin = open(f, 'r')
		fin.readline()

		#create lists of date, times, and precip vals
		for line in fin:
			vals = line.rstrip('\r\n').split(',')
			dates.append(vals[0])
			times.append(vals[1])
			precip.append(float(vals[2]))
		fin.close()

		try:
		    try:
			myDss = HecDss.open( "C:/Users/CIVIL/Desktop/HEC-HMS_EXAMPLE/HEC-HMS_EXAMPLE/SandyUpdate28th/SandyUpdate28th.dss")
			tsc = TimeSeriesContainer()
			tsc.fullName = "//%s/PRECIP-INC/%s /1HOUR/OBS/" %( f[:-4],times[0]) 
			start = HecTime(dates[0], times[0])
			tsc.interval = int(times[1]) - int( times[0])
			hec_times = [   ]
			for t in times :
			    hec_times.append(start.value() )
			    start.add(tsc.interval)
			tsc.times = hec_times
			tsc.values = precip
			tsc.numberValues = len(precip)
			tsc.units = "INCHES"
			tsc.type = "PER-CUM"
			myDss.put(tsc)
		
		    except Exception, e:
		        MessageBox.showError(' '.join(e.args), "Python Error")
		    except java.lang.Exception, e:
		        MessageBox.showError(e.getMessage(), "Error")
		finally:
		    print "DSS created for %s!" %(fin.name)
		    HecDss.done(myDss)
