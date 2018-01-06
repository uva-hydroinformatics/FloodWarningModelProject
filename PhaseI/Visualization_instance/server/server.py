
from flask import Flask, render_template, Response, request
import os
import flask_login, flask
from boto.s3.connection import S3Connection
from datetime import datetime, timedelta
from pydap.client import open_url
from pydap.exceptions import ServerError
import subprocess
import boto.ec2
import datetime as dt
from osgeo import gdal, osr
import numpy as np
import shutil
import xarray
from flask_apscheduler import APScheduler
import urllib2
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email import encoders
import paramiko
from fastkml import kml
from zipfile import ZipFile
from flask_login import login_required
import threading

fromaddr = "uvahydroinformaticslab@gmail.com"
password = "email password"
AWSKEY = "Key"
AWSSECRET = "AWS secret"
InstanceID = "instance ID" # p2.8 ID: "ID", g2.8 ID: "ID"
InstanceUser = "Administrator"
InstancePass = "instance password"
InstanceScriptLocation = "C:/Users/Administrator/Desktop/floodWarningmodelPrototype/runs"
InstanceScript = "run_workflow.bat"
users = {'admin': {'pw': 'password'}} #Login User
alert = 0
lastalertkml = ""
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
conn1 = boto.ec2.connect_to_region("us-east-1", aws_access_key_id=AWSKEY,
                                  aws_secret_access_key=AWSSECRET)

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



def runBatch(filename):
    emails = ['dav3nu@virginia.edu', 'mmm4dh@virginia.edu']
    for email in emails:
	print "Sending alert to " + email
        subject = "Model has been started"
        message = "The model run has been started"
        send_Email(email,subject, message)

    print "Running Script"
    # In case running through the AWS instance uncomment the following lines to start
    # the AWS instance that includes the model
    instance = conn1.start_instances(instance_ids=[InstanceID])[0]
    InstanceIP = ""
    running = False
    while running == False:
        instance.update()
        if instance.state == "running":
            running = True
            InstanceIP = instance.ip_address
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(InstanceIP, username=InstanceUser,password=InstancePass)
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("cd " + InstanceScriptLocation + " & " +
                                                         InstanceScript + " " + filename)
    print ssh_stdout.readlines()
    print ssh_stderr.readlines()
    ssh.close()

def data_monitor():
    #Check latest forecast for flooding every hour
    checkForFlooding()
    global alert
    with open("forecasts.txt") as f:
        ran = f.readlines()
    ran = [x.strip() for x in ran]

    # Get newest available HRRR dataset by trying (current datetime - delta time) until
    # a dataset is available for that hour. This corrects for inconsistent posting
    # of HRRR datasets to repository
    utc_datetime = dt.datetime.utcnow()
    print "Open a connection to HRRR to retrieve forecast rainfall data.............\n"
    # get newest available dataset
    dataset, url, date, hour = getData(utc_datetime, delta_T=0)
    print ("Retrieving forecast data from: %s " % url)

    # Convert time to EST
    if int(hour) >= 4:  # If hour is greater than 4 simply subtract 4
        hour = int(hour) - 4
    else:  # Otherwise UTC is is the next day, so subtract one from the date also
        date = int(date) - 1
        hour = int(hour) - 4 + 24

    filename = str(date) + "-" + str(hour)+"0000"

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
    #if max(max_precip_value) >= 0.0:
    if max(max_precip_value) >= 30.0 and filename not in ran:
        print max_precip_value
        print "Max value", max(max_precip_value)
        # In case running the model locally uncomment the following lines to run the batch file

        f = open('forecasts.txt', 'w')
        f.write(filename + '\n')
        f.close()

        alert = 1

        #In case running through the AWS instance uncomment the following lines to start
        #the AWS instance that includes the model

	runBatch(filename)

        checkForFlooding()




    print "Done running the model at", dt.datetime.now()

def checkForFlooding():
    # Go through static folder and populate list of files
    global lastalertkml
    global alert

    files = []
    for file in os.listdir("static/bridgekmzs"):
        if file.endswith(".kmz"):
            files.append(file)
    files.sort(reverse=True)
    redcount = 0

    if files[0] != lastalertkml:
        lastalertkml = files[0]
        kmz = ZipFile("static/bridgekmzs/" + files[0], 'r')
        doc = kmz.read('doc.kml')
        k = kml.KML()
        k.from_string(doc)
        f = list(k.features())
        for bridge in list(f[0].styles()):
            for b in bridge.styles():
                if b.color == "ff0000ff":
                    redcount += 1
        if redcount >= 3:
            alert = 2
            Email()
        else:
            alert = 0


class Config(object):
    JOBS = [
        {
            'id': 'data_monitor',
            'func': 'server:data_monitor',
            'trigger': 'interval',
            'minutes': 60
        }
    ]

    SCHEDULER_API_ENABLED = True


#Set Up Flask Constants and Login
app = Flask(__name__)
app.config.from_object(Config())
app.debug = False
app.secret_key = 'jkhfajkhdajfhajkhdfaiuy'
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

#Connection to AWS
conn = S3Connection(AWSKEY,AWSSECRET)
bucket = conn.get_bucket('floodwarningmodeldata')

#Class for User
class User(flask_login.UserMixin):
    pass

#Load the User
@login_manager.user_loader
def user_loader(email):
    if email not in users:
        return
    user = User()
    user.id = email
    return user

#Load the Password
@login_manager.request_loader
def request_loader(request):
    email = request.form.get('email')
    if email not in users:
        return
    user = User()
    user.id = email
    user.is_authenticated = request.form['pw'] == users[email]['pw']
    return user

#Login Method
@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'GET': #If Webpage is visited Directly then load the login screen
        return render_template('login.html')

    email = flask.request.form['email'] #If webpage is called after a POST request from the form,
    # login in user or reject credentials
    if flask.request.form['pw'] == users[email]['pw']:
        user = User()
        user.id = email
        flask_login.login_user(user)
        return flask.redirect(flask.url_for('index'))

    return 'Bad login'

#logout User
@app.route('/logout')
def logout():
    flask_login.logout_user()
    return flask.redirect(flask.url_for('index'))

#Deal with Unauthorized user
@login_manager.unauthorized_handler
def unauthorized_handler():
    return 'Unauthorized'

@app.route("/register" , methods=['GET','POST'])
def register():
    email = request.form['email']
    emailConn = sqlite3.connect("/home/ubuntu/server/emails.db")
    c = emailConn.cursor()
    c.execute("INSERT INTO EMAILS VALUES (?);", (email,))
    emailConn.commit()
    emailConn.close()
    return flask.redirect(flask.url_for('index'))

@app.route("/unregister")
def unregister():
    email = request.args.get('email')
    emailConn = sqlite3.connect("/home/ubuntu/server/emails.db")
    c = emailConn.cursor()
    c.execute("DELETE FROM EMAILS WHERE Email=?", (email,))
    emailConn.commit()
    emailConn.close()
    return email + " Has been removed from our Email list."

def Email():
    emailConn = sqlite3.connect("/home/ubuntu/server/emails.db")
    emailConn.row_factory = lambda cursor, row: row[0]
    c = emailConn.cursor()
    emails = c.execute('SELECT Email FROM emails').fetchall()
    emails = list(set(emails))
    for email in emails:
        subject = "Flood Alert Email"
        message = "The latest forecast shows the possibility of flooding in the Hampton Roads " \
                  "District, VA.\n" \
                   "Please go to http://52.87.240.121/ to see more information.\n" \
                   "To unregister visit http://ec2-52-87-240-121.compute-1.amazonaws.com/" \
                  "unregister?email=" + email
        send_Email(email,subject, message)

    emailConn.close()

def send_Email(toaddr, subject, message):
    try:
        msg = MIMEMultipart()
        msg['From'] = fromaddr
        msg['To'] = toaddr
        msg['Subject'] = subject
        body = message

        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(fromaddr, password)
        text = msg.as_string()
        server.sendmail(fromaddr, toaddr, text)
        server.quit()
    except:
        pass

def populateNavbar():
    #Go through S3 and populate list of files
    archivedList = []
    for key in bucket.list():
        name = key.name.encode('utf-8')
        if len(name.split('/')[1]) > 1 and name.split('/')[0] == 'bridgekmzs':
             archivedList.append(name.split('/')[1])
    archivedList.sort( reverse=True)

    archivedTimes = []
    for file in archivedList:
        time = filter(type(file).isdigit, file)
        time = datetime.strptime(time,'%Y%m%d%H%M%S')
        archivedTimes.append(time - timedelta(minutes=time.minute, seconds = time.second,
                                              microseconds = time.microsecond) )
    archivedTimes.sort(reverse=True)

    archivedItems = []
    for i in range(0,len(archivedTimes)):
        newItem = {}
        newItem['time'] = archivedTimes[i]
        newItem['file'] = archivedList[i]
        archivedItems.append(newItem)

    #Go through static folder and populate list of files

    items = []
    for file in os.listdir("static/bridgekmzs"):
        if file.endswith(".kmz"):
 		time = filter(type(file).isdigit, file)
        	time = datetime.strptime(time,'%Y%m%d%H%M%S')
        	time = time - timedelta(minutes=time.minute, seconds = time.second,
                                    microseconds = time.microsecond)
	        newItem = {}
        	newItem['time'] = time
        	newItem['file'] = file
        	items.append(newItem)
    items.sort(key=lambda x: x['time'], reverse=True)

    
    #If there are more than 5 files in static delete the oldest
    if len(items) > 5:
        for i in range (5,len(items)):
            os.remove("static/bridgekmzs/" + items[i]['file'])


    return items, archivedItems


@app.route('/')
def index():

    archived = False
    items, archivedItems = populateNavbar()


    # Display the newest file
    kmz = "bridgekmzs/" + items[0]['file']
    logfile = items[0]['file'].split(".")[0] + ".txt"
    title = items[0]['time']

    #if the file is old, display an initial condition of no flooding
    if (datetime.now() - timedelta(hours=4) - title) > timedelta(hours=1):
        title = datetime.now() - timedelta(hours=4)
        kmz = "bridges-no-flood-condition.kmz"
        logfile = "bridges-no-flood-condition.txt"

    return render_template('index.html', title= title.strftime("%B %d %Y at %I %p %Z EDT"),
                           kmz = kmz, items=items, logfile = logfile, archived = archived,
                           archivedItems = archivedItems, alert = alert)

@app.route('/view/<kmz>')
def view(kmz):
    archived = False

    items, archivedItems = populateNavbar()

    logfile = str(kmz).split(".")[0] + ".txt"

    #If the KMZ selected is not in the static folder then it must be pulled from S3
    if len(filter(lambda file: file['file'] == kmz, items)) == 0:
        archived = True

    title = filter(type(kmz).isdigit, kmz)
    date = datetime.strptime(title,'%Y%m%d%H%M%S')
    title = date
    title = title - timedelta(minutes=title.minute, seconds = title.second,
                              microseconds = title.microsecond)

    return render_template('index.html', title= title.strftime("%B %d %Y at %I %p %Z EDT"),
                           kmz = str("bridgekmzs/" +kmz), items = items, logfile = logfile,
                           archived = archived, archivedItems = archivedItems, alert = alert)


@app.route('/log/<logfile>')
def log(logfile):
    archived = False

    items, archivedItems = populateNavbar()

    #Go through static folder and populate list of files
    LogFiles = []
    for file in os.listdir("static/logs"):
        if file.endswith(".txt"):
            LogFiles.append(file)
    LogFiles.sort(reverse=True)

    #If there are more than 5 files in static delete the oldest
    if len(LogFiles) > 5:
        for i in range (5,len(LogFiles)):
            os.remove("static/logs/" + LogFiles[i])


    content = ""
    #If the logfile selected is not in the static folder then it must be pulled from S3 or
    # it is the initial condition
    if logfile not in LogFiles:
        if logfile == "bridges-no-flood-condition.txt":
            with open("static/" + logfile, "r") as f:
                content = f.read()
                return render_template('log.html', noData = True, content = content, items = items,
                                       logfile = logfile, archived = archived,
                                       archivedItems = archivedItems, alert = alert)

        else:
            data = urllib2.urlopen("https://s3.amazonaws.com/floodwarningmodeldata/logs/" +logfile)
            for line in data:
                content += line
    else:
        with open("static/logs/" + logfile, "r") as f:
            content = f.read()


    title = filter(type(logfile).isdigit, logfile)
    date = datetime.strptime(title,'%Y%m%d%H%M%S')
    title = date
    title = title - timedelta(minutes=title.minute, seconds = title.second,
                              microseconds = title.microsecond)

    return render_template('log.html', title= title.strftime("%B %d %Y at %I %p %Z EDT"),
                           content = content, items = items, logfile = logfile, archived = archived,
                           archivedItems = archivedItems, alert = alert)




@app.route('/run')
@login_required
def runModel():
    utc_datetime = dt.datetime.utcnow()

    dtime_fix = utc_datetime + dt.timedelta(hours=0)
    date = dt.datetime.strftime(dtime_fix, "%Y%m%d")
    fc_hour = dt.datetime.strftime(dtime_fix, "%H")
    hour = str(fc_hour)

    # Convert time to EST
    if int(hour) >= 4:  # If hour is greater than 4 simply subtract 4
        hour = int(hour) - 4
    else:  # Otherwise UTC is is the next day, so subtract one from the date also
        date = int(date) - 1
        hour = int(hour) - 4 + 24

    filename = str(date) + "-" + str(hour)+"0000"
    t1 = threading.Thread(target=runBatch, args=[filename])
    t1.start()

    return "Model is being run!"

if __name__ == "__main__":
    app.run()
