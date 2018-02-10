
$choice = Read-Host -Prompt 'Enter 1 to run the workflow on AWS and 2 to Run it Locally'

If ($choice -eq 1) {
Write-Output "Downloading AWS Command Line Interface"
$url = "https://s3.amazonaws.com/aws-cli/AWSCLI32.msi"
$output = "$PSScriptRoot\AWSCLI32.msi"
$start_time = Get-Date

Invoke-WebRequest -Uri $url -OutFile $output
Write-Output "Time taken: $((Get-Date).Subtract($start_time).Seconds) second(s)"

Start-Process -FilePath "$PSScriptRoot\AWSCLI32.msi" -Wait

$ACCESS = Read-Host -Prompt "Please Enter the AWS Access Key"
$SECRET = Read-Host -Prompt "Please Enter the AWS Secret Access Key"

[Environment]::SetEnvironmentVariable("AWS_ACCESS_KEY_ID", $ACCESS, "User")
[Environment]::SetEnvironmentVariable("AWS_SECRET_ACCESS_KEY", $SECRET, "User")
[Environment]::SetEnvironmentVariable("AWS_DEFAULT_REGION", "us-east-1", "User")

#iex "aws ec2 start-instances --instance-ids i-0748cd25c688abd5d"
}
Else
{
Write-Output "Downloading Anaconda"
$url = "https://repo.continuum.io/archive/Anaconda2-4.4.0-Windows-x86_64.exe"
$output = "$PSScriptRoot\Anaconda2-4.4.0-Windows-x86_64.exe"
$start_time = Get-Date

Invoke-WebRequest -Uri $url -OutFile $output
Write-Output "Time taken: $((Get-Date).Subtract($start_time).Seconds) second(s)"

Start-Process -FilePath "$PSScriptRoot\Anaconda2-4.4.0-Windows-x86_64.exe" -Wait

iex "pip install -i https://pypi.anaconda.org/pypi/simple pydap"
iex "conda install -c conda-forge gdal"
iex "pip install -i https://pypi.anaconda.org/pypi/simple simplekml"
[Environment]::SetEnvironmentVariable("GDAL_DATA", "ANACONDA2FOLDER\Library\share\gdal", "User")

iex runworkflow.bat
}
