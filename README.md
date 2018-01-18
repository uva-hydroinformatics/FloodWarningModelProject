# A Cloud-Based Real-time Decision support Modelling System for Flood Impact Warning 
This repository contains code for a prototype cloud based flood warning system. This system provide warnings for flooded transportation infrastructure in coastal virginia, specifically, Hampton Road District. 
The system contains 3 components: A windows server to run the model, a linux webserver to visualize the results in a browser, and a storage bucket for data archival.
## Code Location
### Model Instance
This folder contians the batch file and python scripts located on the model server to pull and pre-process the forecast data, run the model, and post-process and prepare the output for the vizualization purposes.
### Server
This folder contains the python flask application to run on the visualization server.

The Master branch represent the project phase I. The implementation of this phase can be accessed through this link http://54.175.206.52/
Currently, we are working on phase II of this project, GitHub branch "phaseII." This phase can be accessed through this link http://35.196.115.22/
