from pydap.client import open_url
from pydap.exceptions import ServerError
import subprocess
import boto.ec2
import datetime as dt
import numpy as np
from apscheduler.schedulers.blocking import BlockingScheduler

"""
Global parameters:
    -Study area location (LL and UR corners of TUFLOW model bounds)
    -Initial and average resolution values for longitude and latitude,
     needed for grid point conversion
    (source: http://nomads.ncep.noaa.gov:9090/dods/hrrr "info" link)
"""

initLon = -134.09548000000  # modified that to follow the latest values on the website
aResLon = 0.029

initLat = 21.14054700000  # modified that to follow the latest values on the website
aResLat = 0.027

# this values added to the original bounding box made the retrieved data to be
lon_lb = (-77.979315-0.4489797462)
lon_ub = (-76.649286-0.455314383)
lat_lb = (36.321159-0.133)
lat_ub = (37.203955-0.122955)

#  Connection to AWS
conn = boto.ec2.connect_to_region("us-east-1", aws_access_key_id="<aws_access_key_id>",
                                  aws_secret_access_key="<aws_secret_access_key>")

def getData(current_dt, delta_T):
    dtime_fix = current_dt + dt.timedelta(hours=delta_T)
    date = dt.datetime.strftime(dtime_fix, "%Y%m%d")
    fc_hour = dt.datetime.strftime(dtime_fix, "%H")
    hour = str(fc_hour)
    url = 'http://nomads.ncep.noaa.gov:9090/dods/hrrr/hrrr%s/hrrr_sfc_%sz' % (date, hour)
    try:
        dataset = open_url(url)
        if len(dataset.keys()) > 0:
            return dataset, url, date, hour
        else:
            print "Back up method - Failed to open : %s" % url
            return getData(current_dt, delta_T - 1)
    except ServerError:
        print "Failed to open : %s" % url
        return getData(current_dt, delta_T - 1)


def gridpt(myVal, initVal, aResVal):
    gridVal = int((myVal-initVal)/aResVal)
    return gridVal


def data_monitor():
    # Get newest available HRRR dataset by trying (current datetime - delta time) until
    # a dataset is available for that hour. This corrects for inconsistent posting
    # of HRRR datasets to repository
    utc_datetime = dt.datetime.utcnow()
    print "Open a connection to HRRR to retrieve forecast rainfall data.............\n"
    # get newest available dataset
    dataset, url, date, hour = getData(utc_datetime, delta_T=0)
    print ("Retrieving forecast data from: %s " % url)
    var = "apcpsfc"
    precip = dataset[var]
    print ("Dataset open")

    # Convert dimensions to grid points, source: http://nomads.ncdc.noaa.gov/guide/?name=advanced
    grid_lon1 = gridpt(lon_lb, initLon, aResLon)
    grid_lon2 = gridpt(lon_ub, initLon, aResLon)
    grid_lat1 = gridpt(lat_lb, initLat, aResLat)
    grid_lat2 = gridpt(lat_ub, initLat, aResLat)

    max_precip_value = []
    for hr in range(len(precip.time[:])):
        while True:
            try:
                grid = precip[hr, grid_lat1:grid_lat2, grid_lon1:grid_lon2]
                max_precip_value.append(np.amax(grid.array[:]))
                break
            except ServerError:
                'There was a server error. Let us try again'

    if max(max_precip_value) >= 2.0:
        print max_precip_value
        print "Max value", max(max_precip_value)
        # In case running the model locally uncomment the following lines to run the batch file
        filepath="C:/Users/Morsy/Desktop/floodWarningmodelPrototype/runs/run_workflow.bat"
        p = subprocess.Popen(filepath, shell=True, stdout = subprocess.PIPE)
        stdout, stderr = p.communicate()
        print p.returncode

        # In case running through the AWS instance uncomment the following lines to start
        # the AWS instance that includes the model
        ## conn.start_instances(instance_ids=['<instance_ids>'])

    print "Done running the model at", dt.datetime.now()


##################################################################################################
# ***************************************** Main Program *****************************************
##################################################################################################


def main():
    scheduler = BlockingScheduler()
    scheduler.add_job(data_monitor, 'interval', hours=1)
    scheduler.start()
    data_monitor()


if __name__ == "__main__":
    main()