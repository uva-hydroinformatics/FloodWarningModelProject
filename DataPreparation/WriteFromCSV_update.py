# name=WriteFromCSV_update
# displayinmenu=true
# displaytouser=true
# displayinselector=true
from hec.script import *
from hec.heclib.dss import *
from hec.heclib.util import *
from hec.io import *
import java

print "beginning script execution"

precip = [ ]
times = [ ]
dates = []

filename = "subwatershed_1"
fin = open("C:\Users\CIVIL\Desktop\HEC-HMS_EXAMPLE\HEC-HMS_EXAMPLE/%s.csv" %(filename), 'r')
fin.readline()
for line in fin:
	vals = line.rstrip('\r\n').split(',')
	dates.append(vals[0])
	times.append(vals[1])
	precip.append(float(vals[2]))
fin.close()
print precip
print times
print dates
try:
    try:
	myDss = HecDss.open("C:\Users\CIVIL\Desktop\HEC-HMS_EXAMPLE\HEC-HMS_EXAMPLE/%s.dss" %(filename))
	tsc = TimeSeriesContainer()
	tsc.fullName = "/BASIN/LOC/PRECIP-INC/ /1HOUR/OBS/"
	start = HecTime(dates[0], times[0])
	tsc.interval = 60
	hec_times = [ ]
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
    print "script complete"
    myDss.close()

#file = test.csv
#fin = open(file, 'r')
#fin.readline()
#values = np.array([])


#precip in inches
#for line in fin:
#    data = line.rstrip('\r\n').split(',')
 #   values = np.append(values, float(data[4]))
