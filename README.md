# A Cloud-Based Real-time Decision support Modelling System for Flood Impact Warning

This repository contains code for a prototype cloud based flood warning system. This system provide warnings for flooded transportation infrastructure in coastal virginia, specifically, Hampton Road District. The system contains 3 components: A windows server to run the model, a linux webserver to visualize the results in a browser, and a storage bucket for data archival.

The Master branch represents the project phase I. The implementation of this phase can be accessed through this link http://vfis-aws.uvahydroinformatics.org/

Currently, we are working on phase II of this project, GitHub branch "phaseII." This phase can be accessed through this link http://vfis.uvahydroinformatics.org/

## Deployment
There are three main parts to our cloud based workflow: A visualization instance, a model instance, and a storage bucket. Below are instructions for reproducing the model and visualization instances. 

### Model Instance Creation
The model instance is a windows machine with a powerful GPU to run the tuflow model. These instructions assume that the TUFLOW Model has been installed and is running. The source code required for the model instance is located in the [Model Instance](https://github.com/uva-hydroinformatics/FloodWarningModelProject/tree/master/PhaseI/Model_instance) folder. 

Along with the model the instance must also have a cloud CLI. If using AWS the instructions to install and configure it are located [here](https://docs.aws.amazon.com/cli/latest/userguide/installing.html). 

Python and the dependencies in requirements.txt must be installed. The [batch file](https://github.com/uva-hydroinformatics/FloodWarningModelProject/blob/master/PhaseI/Model_instance/run_workflow.bat) must also be edited to point to the correct file paths and cloud resources.

Lastly the batch file is triggered over SSH which is not yet standard on Windows Server Machines. SSH can be used on windows machines by:
* Open Power shell and install chocolatey package manager
    ```Powershell
    Set-ExecutionPolicy Bypass
	iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))```
* Install the openSSH Server with this command
    ```Powershell
    choco install openssh -params '"/SSHServerFeature"'
    ```
### Visualization Instance Creation
The visualization displays all of the model run results to the end user from a web browser. It runs on a linux webserver. 
Clone the [server](https://github.com/uva-hydroinformatics/FloodWarningModelProject/tree/master/PhaseI/Visualization_instance/server) folder onto your webserver. 
Install the python requirements with 
```
pip install -r requirements_Dec2017.txt
```
To run the python flask webserver program we use two other pieces of software: [NGINX](https://www.nginx.com/) and [pm2](https://github.com/Unitech/pm2). NGINX handles all web requests from the users. PM2 monitors our pyhton process and keeps it running in the background with logs.
To install NGINX:
* ```shell
    sudo apt-get update 
    sudo apt-get install -y nginx
    ```
*   ```shell
    sudo /etc/init.d/nginx start
    sudo rm /etc/nginx/sites-enabled/default
    sudo touch /etc/nginx/sites-available/app
    sudo ln -s /etc/nginx/sites-available/app /etc/nginx/sites-enabled/app
    sudo vim /etc/nginx/sites-available/app
    ```
    and the copy and paste the following configuration into the new file
    ```NGINX
    server {
        location / {
            proxy_pass http://localhost:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        location /static {
            alias  /home/ubuntu/server/static/;
        }
    }
    ```
* Restart NGINX
  ```bash
  sudo /etc/init.d/nginx restart
  ```
  
To install pm2:
* First install nodejs using the correct [instructions](https://nodejs.org/en/download/package-manager/) for your system.
* Run
    ```bash
     npm install pm2 -g
     ```
* Then run the following command to start the python server.
    ```bash
    pm2 start server/server.py
    ```

### Powershell Script
[Aws.ps1](https://github.com/uva-hydroinformatics/FloodWarningModelProject/blob/master/PhaseI/AWS.ps1) is a proof of concept script to be run on a users local machine to either trigger the model run from the cloud or run the model locally. It will also install all necessary dependecies for both scenarios.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

