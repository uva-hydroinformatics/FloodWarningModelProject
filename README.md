# A Cloud-Based Real-time Decision support Modelling System for Flood Impact Warning 
This repository contains code for a prototype cloud based flood warning system. This system provide warnings for flooded transportation infrastructure in coastal virginia, specifically, Hampton Road District. 
The system contains 3 components: A windows server to run the model, a linux webserver to visualize the results in a browser, and a storage bucket for data archival.
## Code Location
In this repo, each Github branch represents a project phase. For an example, Master branch represents project phase I, and phaseII branch represents project phaseII. there are two main folders included in each branch to represent the system implementation in each phase: Model_instance, and Visualization_instance.
### Model_instance
This folder contians the batch file and python scripts located on the model server to pull and pre-process the forecast data, run the model, and post-process and prepare the output for the vizualization purposes.
### Visualization_instance
This folder contains the python flask application to run on the visualization server.All the required libraries can be installed automatically using the provided requirements_Dec2017.txt:

```bash
pip install -r requirements_Dec2017.txt
```

### Powershell Script
Aws.ps1 is a proof of concept script to be run on a users local machine to either trigger the model run from the cloud or run the model locally. It will also install all necessary dependecies for both scenarios. 


The Master branch represents the project phase I. The implementation of this phase can be accessed through this link http://54.175.206.52/

Currently, we are working on phase II of this project, GitHub branch "phaseII." This phase can be accessed through this link http://35.196.115.22/
