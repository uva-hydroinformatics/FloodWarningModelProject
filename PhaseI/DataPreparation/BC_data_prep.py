
# -*- coding: utf-8 -*-
"""
This program retrieves data from the NOAA NOMADS repository, using the High-Resolution Rapid Refresh
(HRRR) model (https://rapidrefresh.noaa.gov/hrrr/). The forecasted surface precipitation is obtained
as a dataset for the newest available UTC hour. Given a latitude and longitude in decimal degrees,
a time series of surface precipitation for the corresponding grid-relative location is printed to a CSV file.
Each CSV file is converted to DSS format and loaded into existing HEC-HMS model. Conversion from CSV to DSS is
done by running a cmd file that runs a DSSVue jython script.
*Note* Script must be run with python 2.7 (compatible with pydap)
"""
from pydap.client import open_url
from pydap.exceptions import ServerError
import datetime as dt
import os
from matplotlib import dates
import csv
from dateutil import tz
from subprocess import Popen

"""
Global parameters:
    -path to DSS conversion script
    -desired data product from HRRR (var), apcpsfc = "surface total precipitation" [mm] (http://www.nco.ncep.noaa.gov/pmb/products/hrrr/hrrr.t00z.wrfsfcf00.grib2.shtml)
    -Initial and average resolution values for longitude and latitude,
     needed for grid point conversion (http://nomads.ncep.noaa.gov:9090/dods/hrrr "info" link)
    -centroid locations of sub watersheds   
"""
path_DSS = "C:/Users/CIVIL/Desktop/HEC-HMS_EXAMPLE/HEC-HMS_EXAMPLE/"

var = "apcpsfc"

initLon = -134.09548000000  # modified that to follow the latest values on the website
aResLon = 0.029

initLat = 21.14054700000  # modified that to follow the latest values on the website
aResLat = 0.027

# this values added to the original bounding box made the retrieved data to be
# values were determined by checking http://nomads.ncep.noaa.gov:9090/dods/hrrr/hrrrYYYYMMDD/hrrr_sfc_00z.ascii?apcpsfc[0][GRIDLAT][GRIDLON]
# and subtracting the reported lat/lon (which were consistently too far north/east of true locations) from true locations

lon1_add = -0.462183898 ; lat1_add = -0.141701545
lon2_add = -0.446984841 ; lat2_add = -0.149337909
lon3_add = -0.451586726 ; lat3_add = -0.157756091
lon4_add = -0.4561288 ; lat4_add = -0.143465182 #lon4_add was more effective when replaced with median value of all lon_add values, comapred to manual calculation
lon5_add = -0.458127857 ; lat5_add = -0.145328818	
lon6_add = -0.453148423 ; lat6_add = -0.150628818
lon7_add = -0.454289554 ; lat7_add = -0.134792455
lon8_add = -0.465349366 ; lat8_add = -0.132483364
lon9_add = -0.4561288 ; lat9_add = -0.159056091
lon10_add = -0.448568989 ; lat10_add = -0.141428818
lon11_add = -0.460549366 ; lat11_add = -0.141174273

lat1 = 36.8443
lat2 = 37.0003
lat3 = 37.0737
lat4 = 36.9789
lat5 = 37.1134
lat6 = 36.5081
lat7 = 36.3603
lat8 = 36.4717
lat9 = 37.0724
lat10 = 37.1173
lat11 = 37.1721

lon1 = -78.1241
lon2 = -77.9627
lon3 = -77.6749
lon4 = -77.6016
lon5 = -77.506
lon6 = -77.4133
lon7 = -77.239
lon8 = -77.2793
lon9 = -77.3578
lon10 = -77.321
lon11 = -77.2745

lon1_fix = lon1 + lon1_add ; lat1_fix = lat1 + lat1_add
lon2_fix = lon2 + lon2_add ; lat2_fix = lat2 + lat2_add
lon3_fix = lon3 + lon3_add ; lat3_fix = lat3 + lat3_add
lon4_fix = lon4 + lon4_add ; lat4_fix = lat4 + lat4_add
lon5_fix = lon5 + lon5_add ; lat5_fix = lat5 + lat5_add
lon6_fix = lon6 + lon6_add ; lat6_fix = lat6 + lat6_add
lon7_fix = lon7 + lon7_add ; lat7_fix = lat7 + lat7_add
lon8_fix = lon8 + lon8_add ; lat8_fix = lat8 + lat8_add
lon9_fix = lon9 + lon9_add ; lat9_fix = lat9 + lat9_add
lon10_fix = lon10 + lon10_add ; lat10_fix = lat10 + lat10_add
lon11_fix = lon11 + lon11_add ; lat11_fix = lat11 + lat11_add

#uncomment to read different list of locations from file with columns X,Y
#def get_locations(filename):    
#    Lat=[]
#    Lon=[]
#    f=open(filename,'r')
#    f.readline() #skip the header line
#    for line in f:
#        data=line.rstrip('\r\n').split(',')
#        Lat.append(float(data[1]))
#        Lon.append(float(data[0]))
#    f.close()
#    point_count=len(Lat)
#    print point_count
#    print Lat
#    print Lon
#get_locations(sys.argv[1])

def getData(current_dt):
    delta_T = 0
    while True:
        dtime_fix = current_dt - dt.timedelta(hours=delta_T)
        date = dt.datetime.strftime(dtime_fix, "%Y%m%d")
        fc_hour = dt.datetime.strftime(dtime_fix, "%H")
        hour = str(fc_hour)
        url = 'http://nomads.ncep.noaa.gov:9090/dods/hrrr/hrrr%s/hrrr_sfc_%sz' % (date, hour)
        try:
            dataset = open_url(url)
            if len(dataset.keys()) > 0:
                print ("Dataset open \n")
                break
            else:
                print "Back up method - Failed to open : %s" % url
                delta_T += 1
        except:
            print "Failed to open : %s \n" % url
            delta_T += 1
    return dataset, url, date, hour


def gridpt(myVal, initVal, aResVal):
    gridVal = int((myVal-initVal)/aResVal)
    return gridVal

def CSV2DSS(cwd):
    p = Popen( path_DSS+"run_WriteFromCSV_loop.cmd "+cwd )
    return p

##################################################################################################
# ***************************************** Main Program *****************************************
##################################################################################################

def main():
    print "Beginning boundary condition data processing! \n"
    # Get newest available HRRR dataset by trying (current datetime - delta time) until
    # a dataset is available for that hour. This corrects for inconsistent posting
    # of HRRR datasets to repository    
    utc_datetime = dt.datetime.utcnow()
    print utc_datetime
    print "Opening a connection to HRRR to retrieve forecast rainfall data.............\n"
    dataset, url, date, hour = getData(utc_datetime)
    print ("Retrieving forecast data from: %s \n" % url)

    # select desired forecast product from grid, grid dimensions are time, lat, lon    
    precip = dataset[var]

    # Convert dimensions to grid points, source: http://nomads.ncdc.noaa.gov/guide/?name=advanced    
    lats = [lat1_fix, lat2_fix, lat3_fix, lat4_fix, lat5_fix, lat6_fix, lat7_fix, lat8_fix, lat9_fix, lat10_fix, lat11_fix]
    lons = [lon1_fix, lon2_fix, lon3_fix, lon4_fix, lon5_fix, lon6_fix, lon7_fix, lon8_fix, lon9_fix, lon10_fix, lon11_fix]

    n_points = len(lats)

    grid_lats = [0.]*n_points
    grid_lons = [0.]*n_points

    for n in range(n_points):
        grid_lats[n] = gridpt(lats[n], initLat, aResLat)
        grid_lons[n] = gridpt(lons[n], initLon, aResLon)
                
    # make directory to store rainfall data
    loc_datetime = dt.datetime.now()
    loc_datetime_str = loc_datetime.strftime('%Y%m%d_%H%M%S')
    os.makedirs(loc_datetime_str)

    # The CSV folder includes the forecast precip to use in Hec HMS
    os.makedirs(loc_datetime_str+"/CSV")
    os.chdir(loc_datetime_str+"/CSV")

    # create time series for each location
    n_hrs = len(precip.time[:])
    for n in range(n_points):
        while True:
            try:
                #add precip values to list and convert from mm to in
                ts = precip[0:n_hrs, grid_lats[n], grid_lons[n]]
                precip_mm = [ p[0][0] if p != -9.999e20 else None for p in ts.array[:] ]
                precip_in = [ p * 0.0393701 for p in precip_mm ]
                # precip_prj.fill(hr*10)  # uncomment this line to produce dummy data
               
                #add times to list and convert from UTC decimal days to current time
                times_num = [ t for t in precip.time[:] ]
                times_UTC = [ dates.num2date((t-1), tz = tz.tzutc()) for t in times_num ] #num2date takes number decimals days plus one: https://matplotlib.org/api/dates_api.html#matplotlib.dates.num2date
                times_EST = [ times_UTC[t].astimezone(tz.tzlocal()) for t in range(n_hrs) ]         
                
                #format times for DSSVue
                Hec_Dates = [ dt.datetime.strftime(dts, "%d%b%Y") for dts in times_EST ] 
                Hec_Hours = [ dt.datetime.strftime(hr,"%H%M") for hr in times_EST ]
                
                #write time series to CSV files
                with open(os.getcwd()+"/subwatershed_%d.csv" %(n+1), "wb") as results:    
                    bc_file = csv.writer(results)
                    bc_file.writerow( ["HEC-Date", "Hec-Time", "Precip [in]"] )
                    for p in range( len(precip_mm) ):
                        bc_file.writerow( [ Hec_Dates[p], Hec_Hours[p], precip_in[p] ] )
                results.close()
                break
            except ServerError:
                "There was a server error. Let us try again"
        print ("File for location %d has been written with %d hours of precipitation" % (n+1, n_hrs) )

    #convert time series data to DSS files and load to Project dss
    cwd = os.getcwd()
    CSV2DSS(cwd)

    print "Finished processing boundary condition data!"


if __name__ == "__main__":
    main()
