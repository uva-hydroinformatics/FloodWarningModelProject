@echo off
SETLOCAL
SET log=..\runs\TempLog.txt
set file=%1

REM run the forecast script to retrieve the forecast rainfall data
(
echo %file%

:Forecast
"python" "..\scripts\HRRR_to_nc_UTM_projection.py"
if not exist ..\bc_dbase\forecast_rainfall\rainfall_forecast.nc (
GOTO Forecast
)
REM Run TUFLOW model to generate maximum water levels
:Model
"C:\TUFLOW\Releases\2017-09-AC\TUFLOW_iSP_w64.exe" -b -x -s1 50m  -s2 GPU  -el Forecast "..\runs\VU_~s1~_~s2~_~e1~_008.tcf"
if not exist ..\results\grids\VU_50m_GPU_Forecast_008_h_Max.asc (
GOTO Model
)

REM run the post processing script to generate the KMZ file for flooded
REM bridge locations for the TUFLOW output
:KMZ
"python" "..\scripts\extract_flooded_locations_maps_api_MWL_Grid.py" %file%

if not exist ..\results\flooded_locations\bridges%file%.kmz (
GOTO KMZ
)

echo The run was successfully done!
)>%log%

timeout 5
REM Send the KMZ file to the visualization AWS instance (server)
CALL gcloud  compute scp ..\results\flooded_locations\*.kmz root@visualization:/home/uvahydroinformaticslab/server/static/bridgekmzs/

REM Archiving the KMZ file in AWS S3 Bucket
REM aws s3 cp ..\results\flooded_locations\ s3://floodwarningmodeldata/bridgekmzs --recursive
CALL gsutil cp  ..\results\flooded_locations\bridges%file%.kmz gs://flood-warning-archive/bridgekmzs



REM Archiving the Forecast rainfall data with different format as zipped folder in AWS S3 Bucket
REM aws s3 cp ..\bc_dbase\forecast_rainfall\ s3://floodwarningmodeldata/forecast_rainfall --recursive --exclude "*.nc"
CALL gsutil cp   ..\bc_dbase\forecast_rainfall\*.zip gs://flood-warning-archive/forecast_rainfall

REM Delete the generated data and folders from running the workflow for not using space on the AWS instance
REM This lines could be commented in case running the workflow on local works
rmdir ..\results\flooded_locations /s /q
rmdir ..\results\grids /s /q
rmdir ..\bc_dbase\forecast_rainfall\ /s /q


REN %log% bridges%file%.txt
timeout 5

REM Send the log file to the visualization AWS instance (server)
CALL gcloud  compute scp ..\runs\bridges%file%.txt root@visualization:/home/uvahydroinformaticslab/server/static/logs/

timeout 5

CALL gsutil cp ..\runs\bridges%file%.txt gs://flood-warning-archive/logs
del ..\runs\bridges%file%.txt
REM CALL gsutil iam ch allUsers:objectViewer gs://flood-warning-archive
shutdown.exe /s /t 00
ENDLOCAL
