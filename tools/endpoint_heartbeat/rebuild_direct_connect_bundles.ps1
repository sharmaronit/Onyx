[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$pythonPath = Join-Path $projectRoot '.runtime-python310\python.exe'
$builderPath = Join-Path $PSScriptRoot 'build_direct_connect_bundles.py'

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Onyx Python runtime was not found at $pythonPath"
}

$addresses = [System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) |
    Where-Object {
        $_.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork -and
        -not $_.IPAddressToString.StartsWith('127.') -and
        -not $_.IPAddressToString.StartsWith('169.254.')
    } |
    ForEach-Object { $_.IPAddressToString }

$serverIp = $addresses |
    Sort-Object @{ Expression = { if ($_ -like '192.168.*' -or $_ -like '10.*') { 0 } else { 1 } } } |
    Select-Object -First 1

if (-not $serverIp) {
    throw 'No usable LAN IPv4 address was found. Connect the server laptop to Wi-Fi and try again.'
}

Write-Host "Detected Onyx server address: $serverIp" -ForegroundColor Cyan
& $pythonPath $builderPath --server-url "http://${serverIp}:8020"
if ($LASTEXITCODE -ne 0) {
    throw "Bundle builder exited with code $LASTEXITCODE"
}

Write-Host ''
Write-Host 'All direct-connect and judge-demo packages were rebuilt for the current network.' -ForegroundColor Green
Write-Host "Output: $PSScriptRoot\dist"
