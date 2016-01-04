__author__ = 'Mohamed Morsy'
import urllib


# point of interest
Lat = 38.99
Long = -77.01


# Build the precipitation data request URL

precipURL = "http://graphical.weather.gov/xml/sample_products/browser_interface/ndfdXMLclient.php?" \
            + "whichClient=NDFDgen&lat=%s&lon=%s"%(Lat, Long) \
            + "&product=time-series&begin=2004-01-01T00%3A00%3A00&end=2020-01-04T00%3A00%3A00&Unit=e&qpf=qpf&Submit=Submit"

precipData = urllib.urlopen(precipURL)
readPrecipData = precipData.read()

# TO DO: extract the desired forecast data from the respond as times series (time (HH:MM) and Value )