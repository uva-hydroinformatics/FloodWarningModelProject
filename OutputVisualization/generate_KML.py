from osgeo import gdal,ogr
import struct
import shapefile
import simplekml

asc_filename = 'VU_50m_CPU_Sandy_005_h_Max.asc'
shp_filename = 'test_append_V.shp'

# Open ASCII file
src_ds=gdal.Open(asc_filename)
gt=src_ds.GetGeoTransform()
rb=src_ds.GetRasterBand(1)

#Open Shapefile
ds=ogr.Open(shp_filename,1)
lyr=ds.GetLayerByIndex(0)
# name=lyr.GetName()

#Define new Field to append Max WL --> need more work
fieldDefn = ogr.FieldDefn('MaxWL', ogr.OFTReal)
fieldDefn.SetWidth(14)
fieldDefn.SetPrecision(6)
lyr.CreateField(fieldDefn)
valuesss = 233
for feat in lyr:
    # print feat
    # a = raw_input("hi")
    geom = feat.GetGeometryRef()
    fedid=feat.GetField("FedID")
    mx,my=geom.GetX(), geom.GetY()  #coord in map units

    #Convert from map to pixel coordinates.
    #Only works for geotransforms with no rotation.
    px = int((mx - gt[0]) / gt[1]) #x pixel
    py = int((my - gt[3]) / gt[5]) #y pixel

    structval=rb.ReadRaster(px,py,1,1,buf_type=gdal.GDT_Float64) #Assumes 16 bit int aka 'short'
    maxwlval = struct.unpack('d', structval) #use the 'short' format code (2 bytes) not int (4 bytes)
    feat.SetField("MaxWL", maxwlval[0])
    lyr.SetFeature(feat)

    print fedid, geom, maxwlval[0] #intval is a tuple, length=1 as we only asked for 1 pixel value

