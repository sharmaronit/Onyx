[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ProductCode)
$ErrorActionPreference = "Stop"
Start-Process msiexec.exe -ArgumentList "/x $ProductCode /qn" -Wait -NoNewWindow
