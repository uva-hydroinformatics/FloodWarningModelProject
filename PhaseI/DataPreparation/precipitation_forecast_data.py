__author__ = 'Mohamed Morsy'
import urllib
from xml.etree import ElementTree
from datetime import datetime
import csv



# point of interest
Lat = 38.99
Long = -77.01


# Build the precipitation data request URL

precipURL = "http://graphical.weather.gov/xml/sample_products/browser_interface/ndfdXMLclient.php?" \
            + "whichClient=NDFDgen&lat=%s&lon=%s"%(Lat, Long) \
            + "&product=time-series&begin=2004-01-01T00%3A00%3A00&end=2020-01-04T00%3A00%3A00&Unit=e&qpf=qpf&Submit=Submit"

precipData = urllib.urlopen(precipURL)

#Read the response
readPrecipData = precipData.read()
tree = ElementTree.fromstring(readPrecipData)

# Extract the precipitation data
values = []
for value in tree.getiterator('value'):
    values.append(value.text)

#Extract the precipitation data corresponding date, time and time step
date = []
time = []
dtime = []
timestep = []
n = 0
for dt in tree.getiterator('start-valid-time'):
    date.append(datetime.date(datetime.strptime(dt.text[:-6], '%Y-%m-%dT%H:%M:%S')))
    time.append(datetime.time(datetime.strptime(dt.text[:-6], '%Y-%m-%dT%H:%M:%S')))
    dtime.append(datetime.strptime(dt.text[:-6], '%Y-%m-%dT%H:%M:%S'))
    timestep.append(dtime[n]-dtime[n-1])
    n += 1

#Create CSV file to append the data and create the time series
c = csv.writer(open("precip.csv", "wb"))
c.writerow(["Date","Time","Time Step","Value"])
for i in range(len(values)):
    c.writerow([str(date[i]),str(time[i]),str(timestep[i]),values[i]])