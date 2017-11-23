@echo off
SETLOCAL

REM change filepath to Jython exe and to DSSVue script

start C:\"Program Files (x86)\HEC\HEC-DSSVue-v2.6.00.59\HEC-DSSVue-v2.6.00.59\Jython.exe"  C:\Users\CIVIL\AppData\Roaming\HEC\HEC-DSSVue\scripts\WriteFromCSV_loop.py %1 exit

ENDLOCAL