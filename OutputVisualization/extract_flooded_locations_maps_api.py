from osgeo import gdal, ogr
from os.path import exists
from os.path import basename
from os.path import splitext
from os import remove
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email import encoders
import time
import struct
import simplekml
import sys

#INSERT EMAIL CREDENTIALS HERE
#The sender must 'allow less secure apps' by using this link https://www.google.com/settings/security/lesssecureapps
toaddr = ""
fromaddr = ""
password = ""

msg = MIMEMultipart()

msg['From'] = fromaddr
msg['To'] = toaddr
msg['Subject'] = "KMZ Email Test"

body = "This is a test."

msg.attach(MIMEText(body, 'plain'))


gdal.UseExceptions()

print "Extracting the bridges.......\n"

# The name and location of the maximum water levels ASCII file generated
# from the TUFLOW model during the whole simulation
asc_filename = './VU_50m_CPU_Sandy_005_h_Max.asc'
# The name and location of the revised VDOT bridge location and data shapefile
shp_filename = './BridgeSurvey.shp'
# The name and location of the extracted flood locations shapefile
out_file = './floodedLocations.shp'

# Open the ASCII file
src_ds = gdal.Open(asc_filename)
if src_ds is None:
        print "Failed to open the maximum water levels raster.\n"
        sys.exit(1)
gt = src_ds.GetGeoTransform()
rb = src_ds.GetRasterBand(1)

# Open the shapefile
ds = ogr.Open(shp_filename, 1)
if src_ds is None:
        print "Failed to open the study area bridges shapefile.\n"
        sys.exit(1)
lyr = ds.GetLayerByName(splitext(basename(shp_filename))[0])
if lyr is None:
        print "Error opening the shapefile layer"
        sys.exit(1)

# Check that all the 493 bridges are exist
if lyr.GetFeatureCount() != 493:
    raise Exception(lyr.GetFeatureCount(), 'Not equal to number of the bridges'
                                           ' in the study area, 493 bridges')

# For each new run delete the flooded depth field if exist
# Get the input layer's feature definition
lyr_defn = lyr.GetLayerDefn()
try:
    lyr_defn.GetFieldIndex('FloodedBy')
    lyr.DeleteField(lyr_defn.GetFieldIndex('FloodedBy'))
except:
    pass

# Define new Field to the bridge locations and data shapefile to append flooded depth
fieldDefn = ogr.FieldDefn('FloodedBy', ogr.OFTReal)
fieldDefn.SetWidth(14)
fieldDefn.SetPrecision(6)
lyr.CreateField(fieldDefn)

# Extract the data from the ASCII file and compute the flooded depth for each location if exist
for feat in lyr:
    geom = feat.GetGeometryRef()
    # Extract the coordinates for each feature in the shapefile
    mx, my = geom.GetX(), geom.GetY()
    # Convert from map to pixel coordinates. That takes less memory size and less computation time.
    # Only works for geo-transforms with no rotation.
    # x pixel
    px = int((mx - gt[0]) / gt[1])
    # y pixel
    py = int((my - gt[3]) / gt[5])
    # Using the Struct library to unpack the return value for each pixel
    structval = rb.ReadRaster(px, py, 1, 1, buf_type=gdal.GDT_Float64)
    maxwlval = struct.unpack('d', structval)
    bridge_elev = feat.GetField(feat.GetFieldIndex('RoadElev_m'))
    if maxwlval[0] > bridge_elev:
        feat.SetField('FloodedBy', maxwlval[0] - bridge_elev)
    else:
        feat.SetField('FloodedBy', 0.0)
    lyr.SetFeature(feat)

# Create new shapefile with flooded bridge locations and data
if exists(out_file):
        remove(out_file)
driver_name = "ESRI Shapefile"
drv = ogr.GetDriverByName(driver_name)
if drv is None:
        print "%s driver not available.\n" % driver_name
        sys.exit(1)
out_ds = drv.CreateDataSource(out_file)
if out_ds is None:
        print "Creation of output shapefile failed.\n"
        sys.exit(1)
proj = lyr.GetSpatialRef()
out_lyr = out_ds.CreateLayer(splitext(basename(out_file))[0], proj, ogr.wkbPoint)
for i in range(lyr_defn.GetFieldCount()):
    out_lyr.CreateField(lyr_defn.GetFieldDefn(i))
lyr.ResetReading()

for feat in lyr:
    out_lyr.CreateFeature(feat)

# Create the kmZ file to be visualized on Google maps
kml = simplekml.Kml()
kml.document.name = "Bridge locations"
lyr.ResetReading()
for feat in lyr:
    # Add metadata to the KMZ file and dictionary
    xcord = feat.GetField(feat.GetFieldIndex(lyr_defn.GetFieldDefn(7).GetName()))
    ycord = feat.GetField(feat.GetFieldIndex(lyr_defn.GetFieldDefn(6).GetName()))
    roadname = feat.GetField(feat.GetFieldIndex(lyr_defn.GetFieldDefn(8).GetName()))
    stream = feat.GetField(feat.GetFieldIndex(lyr_defn.GetFieldDefn(5).GetName()))
    fedid = feat.GetField(feat.GetFieldIndex(lyr_defn.GetFieldDefn(4).GetName()))
    roadelev = feat.GetField(feat.GetFieldIndex(lyr_defn.GetFieldDefn(19).GetName()))
    floodedby = feat.GetField(feat.GetFieldIndex('FloodedBy'))

    npo = kml.newpoint(name=roadname, coords=[(xcord, ycord)])
    npo.description = "<![CDATA[<table><tr><td>Located at: </td><td>" + stream + "</td></tr><tr><td>Feature ID:</td><td>" + str(
        fedid) + "</td></tr><tr><td>Bridge Elevation: </td><td>" + str(
        roadelev) + "</td></tr><tr><td>Flooded By:</td><td>" + str(floodedby) + '</td></tr></table> <img src="http://34.207.240.31/static/area_graph.png" height="100" width="300">]]>'
    npo.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'

    if floodedby > 0.3:
        npo.style.iconstyle.color = simplekml.Color.red
    elif 0 < floodedby <= 0.30:
        npo.style.iconstyle.color = simplekml.Color.yellow
    else:
        npo.style.iconstyle.color = simplekml.Color.green

kml.savekmz("bridges"+time.strftime("%Y%m%d-%H%M%S")+".kmz")


# # Close the shapefiles and ASCII file
# ds = None
# out_ds = None
# src_ds = None
#
# filename = "bridges.kmz"
# attachment = open("bridges.kmz", "rb")
#
# part = MIMEBase('application', 'octet-stream')
# part.set_payload((attachment).read())
# encoders.encode_base64(part)
# part.add_header('Content-Disposition', "attachment; filename= %s" % filename)
#
# msg.attach(part)
#
# server = smtplib.SMTP('smtp.gmail.com', 587)
# server.starttls()
# server.login(fromaddr, password)
# text = msg.as_string()
# server.sendmail(fromaddr, toaddr, text)
# server.quit()