from osgeo import gdal,ogr
import struct
import shapefile
import simplekml
from os.path import exists
from os.path import basename
from os.path import splitext
from os import remove
import sys

asc_filename = 'VU_50m_CPU_Sandy_005_h_Max.asc'
shp_filename = 'test_append_V_test.shp'
out_file = 'testoutput.shp'

# Open ASCII file
src_ds=gdal.Open(asc_filename)
gt=src_ds.GetGeoTransform()
rb=src_ds.GetRasterBand(1)

#Open Shapefile
ds=ogr.Open(shp_filename,1)
lyr=ds.GetLayerByName( splitext(basename(shp_filename))[0] ) #it was lyr=ds.GetLayerByIndex(0)
# name=lyr.GetName()

#Define new Field to append Max WL --> need more work
if lyr.GetFeatureCount() != 493:
    raise Exception(lyr.GetFeatureCount(), 'Not equal to number of the bridges'
                                           ' in the study area, 493 bridges')
lyr_defn = lyr.GetLayerDefn()
try:
    lyr_defn.GetFieldIndex('MaxWL')
    lyr.DeleteField(lyr_defn.GetFieldIndex('MaxWL'))
except:
    pass
fieldDefn = ogr.FieldDefn('MaxWL', ogr.OFTReal)
fieldDefn.SetWidth(14)
fieldDefn.SetPrecision(6)
lyr.CreateField(fieldDefn)
#
#
for feat in lyr:
    geom = feat.GetGeometryRef()
    fedid=feat.GetField('FedID')
    lyr.SetFeature(feat)
    mx,my=geom.GetX(), geom.GetY()  #coord in map units
    #Convert from map to pixel coordinates.
    #Only works for geotransforms with no rotation.
    px = int((mx - gt[0]) / gt[1]) #x pixel
    py = int((my - gt[3]) / gt[5]) #y pixel

    structval=rb.ReadRaster(px,py,1,1,buf_type=gdal.GDT_Float64) #Assumes 16 bit int aka 'short'
    maxwlval = struct.unpack('d', structval) #use the 'short' format code (2 bytes) not int (4 bytes)
    feat.SetField('MaxWL', maxwlval[0])
    lyr.SetFeature(feat)
    maxwl=feat.GetField('MaxWL')

    # if maxwl <= 0:
    #     fid=feat.GetFID()
    #     print fid,
    #     lyr.DeleteFeature(lyr_defn.GetFeatureIndex(feat))
    # print fedid, geom, maxwlval[0] #intval is a tuple, length=1 as we only asked for 1 pixel value

# create the kml file
kml = simplekml.Kml(open=1)
pfol = kml.newfolder(name="title")
kml.save("test.kml")

# ds.Destroy()


##########################
driver_name = "ESRI Shapefile"
drv = ogr.GetDriverByName( driver_name )
out_ds = drv.CreateDataSource( out_file )
proj = lyr.GetSpatialRef()
out_lyr = out_ds.CreateLayer(splitext(basename(out_file))[0], proj, ogr.wkbPoint )
for i in range(lyr_defn.GetFieldCount()):
    out_lyr.CreateField ( lyr_defn.GetFieldDefn(i) )

lyr.ResetReading()

for feat in lyr:
    value = feat.GetField(feat.GetFieldIndex('MaxWL'))
    if value > 0.0:
        out_lyr.CreateFeature(feat)