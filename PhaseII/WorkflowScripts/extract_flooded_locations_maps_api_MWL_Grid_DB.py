from osgeo import gdal, ogr
from os.path import exists
from os.path import basename
from os.path import splitext
from os import remove
from datetime import datetime, timedelta
import smtplib
import time
import struct
import sys
import os
import psycopg2
from psycopg2.extensions import AsIs

conn = psycopg2.connect(database='', user='', password='',
                        host='', port='')
cur = conn.cursor()

gdal.UseExceptions()

print "Extracting the bridges.......\n"

# The name and location of the maximum water levels ASCII file generated
# from the TUFLOW model during the whole simulation
asc_filename = '../results/grids/VU_50m_HPC_GPU_Forecast_013_h_Max.asc'
# The name and location of the revised VDOT bridge location and data shapefile
shp_filename = '../model/gis/BridgeSurvey.shp'
# The name and location of the extracted flood locations shapefile
if not exists('../results/flooded_locations'):
    os.makedirs('../results/flooded_locations')
out_file = '../results/flooded_locations/floodedLocations.shp'

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

# For each new run delete the maximum water level and flooded depth fields if exist
# Get the input layer's feature definition
lyr_defn = lyr.GetLayerDefn()
try:
    lyr_defn.GetFieldIndex('MaxWL')
    lyr.DeleteField(lyr_defn.GetFieldIndex('MaxWL'))
except:
    pass

lyr_defn = lyr.GetLayerDefn()
try:
    lyr_defn.GetFieldIndex('FloodedBy')
    lyr.DeleteField(lyr_defn.GetFieldIndex('FloodedBy'))
except:
    pass

# Define new Fields to the bridge locations and data shapefile to append maximum water level and
# flooded depth at each location
fieldDefn = ogr.FieldDefn('MaxWL', ogr.OFTReal)
fieldDefn.SetWidth(14)
fieldDefn.SetPrecision(6)
lyr.CreateField(fieldDefn)

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
    feat.SetField('MaxWL', float("{0:.2f}".format(maxwlval[0])))
    if maxwlval[0] != -999:
        if maxwlval[0] > bridge_elev:
            feat.SetField('FloodedBy', float("{0:.2f}".format(maxwlval[0] - bridge_elev)))
        else:
            feat.SetField('FloodedBy', 0.0)
    else:
        feat.SetField('FloodedBy', 0.0)
    lyr.SetFeature(feat)

# Create new shapefile with flooded bridge locations and data
# In case running th script through AWS instances, comment the following line for Create the new
# shapefile for saving space on the AWS instance
if exists(out_file):
        remove(out_file)
# driver_name = "ESRI Shapefile"
# drv = ogr.GetDriverByName(driver_name)
# if drv is None:
#         print "%s driver not available.\n" % driver_name
#         sys.exit(1)
# out_ds = drv.CreateDataSource(out_file)
# if out_ds is None:
#         print "Creation of output shapefile failed.\n"
#         sys.exit(1)
# proj = lyr.GetSpatialRef()
# out_lyr = out_ds.CreateLayer(splitext(basename(out_file))[0], proj, ogr.wkbPoint)
# for i in range(lyr_defn.GetFieldCount()):
#     out_lyr.CreateField(lyr_defn.GetFieldDefn(i))
# lyr.ResetReading()
# for feat in lyr:
#     out_lyr.CreateFeature(feat)

run_date = str(sys.argv[1])



lyr.ResetReading()
for feat in lyr:
    newBridge = {}
    newBridge['xcord'] = feat.GetField(feat.GetFieldIndex(lyr_defn.GetFieldDefn(7).GetName()))
    newBridge['ycord'] = feat.GetField(feat.GetFieldIndex(lyr_defn.GetFieldDefn(6).GetName()))
    newBridge['roadname'] = feat.GetField(feat.GetFieldIndex(lyr_defn.GetFieldDefn(8).GetName()))
    newBridge['stream']= feat.GetField(feat.GetFieldIndex(lyr_defn.GetFieldDefn(5).GetName()))
    newBridge['fedid'] = feat.GetField(feat.GetFieldIndex(lyr_defn.GetFieldDefn(4).GetName()))
    newBridge['roadelev'] = feat.GetField(feat.GetFieldIndex(lyr_defn.GetFieldDefn(19).GetName()))
    newBridge['maxwl'] = feat.GetField(feat.GetFieldIndex('MaxWL'))
    newBridge['floodedby'] = feat.GetField(feat.GetFieldIndex('FloodedBy'))
    newBridge['starttime'] ="Coming Soon"
    newBridge['endtime']= "Coming Soon"
    newBridge['date'] = run_date

    if newBridge['maxwl'] == -999.0:
        newBridge['maxwl'] = 0.0

    columns = newBridge.keys()
    values = [newBridge[column] for column in columns]

    insert_statement = 'insert into bridges (%s) values %s'
    cur.execute(insert_statement, (AsIs(', '.join(columns)), tuple(values)))
    conn.commit()

cur.close()
conn.close()
       


