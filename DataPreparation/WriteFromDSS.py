# name=WriteFromDSS
# displayinmenu=true
# displaytouser=true
# displayinselector=true
from hec.script import *
from hec.script.Constants import TRUE, FALSE
from hec.heclib.dss import *
import java
from hec.dataTable import *

storm_st = "27OCT2012 0800" 
storm_end = "05NOV2012 0800"
output_loc = "C:/Users/CIVIL/Desktop/HEC-HMS_EXAMPLE/HEC-HMS_EXAMPLE/outflows"

outlets_list = ["32B", "31B", "30B", "29B", "28B", "27B", "26B", "25B", "24B", "23B", "21B"]
data_type = "FLOW-DIRECT"
time_int = "15MIN"
run_name = "Run 1"

print "Opening Hec-HMS Results"

try:  
#open project dss file
	dssFile = HecDss.open("C:/Users/CIVIL/Desktop/HEC-HMS_EXAMPLE/HEC-HMS_EXAMPLE/SandyUpdate28th/SandyUpdate28th.dss","%s, %s" %(storm_st, storm_end ) )

	#loop through specified outlets in basin model
	for outlet in outlets_list:
	#format: variable = dssFile.get("/part a/part b/part c/part d/part e/part f/")
	#leave path d  blank to get entire record 
  		outflow = dssFile.get("//%s/%s//%s/RUN:%s/" %(outlet, data_type, time_int,  run_name) )
	#check for values
	  	if outflow.numberValues == 0:
	      		MessageBox.showError("No Data", "Error")
	  	else:
			#  Add Data to excel
			dataset = java.util.Vector()
			dataset.add(outflow)
			table = HecDataTableToExcel.newTable()
			table.createExcelFile(dataset,output_loc+"/%s_outflow.xls" %( outlet ) )
			print "Outflows written to XLS for element: %s" %( outlet )

	#release dss file
	HecDss.done(dssFile) 
  
except java.lang.Exception, e :
	MessageBox.showError(e.getMessage(), "Error reading data")

print "All results written to: %s" %(output_loc)
