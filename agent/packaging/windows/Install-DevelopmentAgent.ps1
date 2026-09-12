[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$MsiPath)
$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $MsiPath)) { throw "MSI file not found: $MsiPath" }
Start-Process msiexec.exe -ArgumentList "/i `"$MsiPath`" /qn" -Wait -NoNewWindow
Write-Host "Installed. Run 'onyx-agent enroll --server-url https://your-api-hostname' from an elevated terminal."
