from osgeo import gdal, ogr
from os.path import exists
from os.path import basename
from os.path import splitext
from os import remove
from oauth2client.service_account import ServiceAccountCredentials

import struct
import simplekml
import sys
import csv
import gspread

# Auth for Google Doc
scope = ['https://spreadsheets.google.com/feeds']
credentials = ServiceAccountCredentials.from_json_keyfile_name('R2S2-a63b1dfc219c.json', scope)
gc = gspread.authorize(credentials)
wks = gc.open("R2S2Map").sheet1


gdal.UseExceptions()

print "Extracting the flooded locations.......\n"

# The name and location of the maximum water levels ASCII file generated
# from the TUFLOW model during the whole simulation
asc_filename = './VU_50m_CPU_Sandy_005_h_Max.asc'
# The name and location of the revised VDOT bridge location and data shapefile
shp_filename = './BridgeSurvey.shp'
# The name and location of the extracted flood locations shapefile
out_file = './floodedLocations.shp'
# The name and location of the output CSV file
csv_file = './floodedLocations.csv'
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

# Extract only the flooded bridges from the original shapefile
for feat in lyr:
    value = feat.GetField(feat.GetFieldIndex('FloodedBy'))
    if value != 0.0:
        out_lyr.CreateFeature(feat)

# List of Bridge Objects for CSV
bridges = []
# Create the kmZ file to be visualized on Google maps
kml = simplekml.Kml()
kml.document.name = "Flooded locations"
lyr.ResetReading()

for feat in lyr:
    # Create a dictonary for CSV Writer
    bridgeObj = {}
    # Add metadata to the KMZ file and dictionary
    xcord = feat.GetField(feat.GetFieldIndex(lyr_defn.GetFieldDefn(7).GetName()))
    ycord = feat.GetField(feat.GetFieldIndex(lyr_defn.GetFieldDefn(6).GetName()))
    bridgeObj['Location'] = str(ycord) + "," + str(xcord)
    roadname = feat.GetField(feat.GetFieldIndex(lyr_defn.GetFieldDefn(8).GetName()))
    bridgeObj['RoadName'] = roadname
    stream = feat.GetField(feat.GetFieldIndex(lyr_defn.GetFieldDefn(5).GetName()))
    bridgeObj['Stream'] = stream
    fedid = feat.GetField(feat.GetFieldIndex(lyr_defn.GetFieldDefn(4).GetName()))
    bridgeObj['FeartureID'] = fedid
    roadelev = feat.GetField(feat.GetFieldIndex(lyr_defn.GetFieldDefn(19).GetName()))
    bridgeObj['RoadElevation'] = str(roadelev) +'m'
    floodedby = feat.GetField(feat.GetFieldIndex('FloodedBy'))
    bridgeObj['FloodedBy'] = str(floodedby) + 'm'

    if floodedby > 0.0:
        npo = kml.newpoint(name=roadname, coords=[(xcord, ycord)])
        npo.description = "Located at "+stream
        # Add extended metadata to the KMZ file and dictionary
        npo.extendeddata.newdata("Feature ID", int(fedid))
        npo.extendeddata.newdata("Bridge elevation (m)", "%.2f" % float(roadelev))
        npo.extendeddata.newdata("Flooded by (m)", "%.2f" % float(floodedby))

    if floodedby > 0.30:
        bridgeObj['Color'] = 'red'
    elif 0 < floodedby <= 0.30:
        bridgeObj['Color'] = 'yellow'
    else:
        bridgeObj['Color'] = 'green'

    bridges.append(bridgeObj)

# I am saving kmz not kml as kmz has smaller size (15 KB compared to 249 KB)
kml.savekmz("FloodedLocations.kmz")

# #Save CSV
# with open(csv_file, 'wb') as csvfile:
#     fieldnames = bridges[0].keys()
#     writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
#     writer.writeheader()
#     for bridge in bridges:
#         writer.writerow(bridge)
# Remove Geosheet function so map does not update for every single bridge
wks.update_acell('J1', " ")
cell_list = wks.range("A1:H"+str(len(bridges)+2))
for cell in cell_list:
    cell.value = " "
wks.update_cells(cell_list)

# Plant Headers in Google Doc
cell_list = wks.range('A1:G1')  # Get Range
i = 0
for cell in cell_list:  # For each cell set the value equal to a key
    cell.value = bridges[0].keys()[i]
    i += 1
wks.update_cells(cell_list)
wks.update_acell('H1', "Type")

# Push Data to Google Docs
i = 0  # Cell Counter
j = 0  # Bridge Counter
cell_list = wks.range('A2:G'+str(len(bridges)+1))
for cell in cell_list:  # Populate values
    cell.value = bridges[j][bridges[0].keys()[i % len(bridges[0].keys())]]
    i += 1
    if i % len(bridges[0].keys()) == 0:  # Move to next bridge after 7 cells
        j += 1
wks.update_cells(cell_list)

# Code for rough boundary
wks.update_acell('F'+str(len(bridges)+2), "36.40359, -77.98095|36.99597, -77.58819|37.18298, -76.92714|37.02038," +
                                          " -76.70701|36.60316, -76.65605|36.3759, -77.05706|36.40359, -77.98095")
wks.update_acell('H'+str(len(bridges)+2), "line")

# Code for boundary. DOES NOT WORK DUE TO POINT LIMITATIONS
# lines = ""
# with open('Boundary.csv', 'rb') as csvfile:
#     spamreader = csv.reader(csvfile, delimiter=' ', quotechar='|')
#     for row in spamreader:
#         lines += row[0].split(",")[1] + ',' + row[0].split(",")[0] + '|'
#
# wks.update_acell('F'+str(len(bridges)+2), lines)
# wks.update_acell('H'+str(len(bridges)+2), "line")

# Add Geosheet Function
wks.update_acell('J1', '=GEO_MAP(A1:H' + str(len(bridges)+2) + ',"Currrent Flooded Bridges in The Hampton Roads District")')

# Close the shapefiles and ASCII file
ds = None
out_ds = None
src_ds = None
