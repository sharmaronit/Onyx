# Onyx web stack launcher
# Starts the backend and frontend, then keeps a live status bar visible.
# Usage: powershell -ExecutionPolicy Bypass -File .\run.ps1

[CmdletBinding()]
param(
    [int]$BackendPort = 8020,
    [int]$FrontendPort = 5183,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$WebRoot = Join-Path $ProjectRoot "web"
$PythonExe = Join-Path $ProjectRoot ".runtime-python310\python.exe"
$SecretsFile = Join-Path $ProjectRoot ".onyx-secrets.cmd"

function Write-Section([string]$Message) {
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Test-TcpPort([string]$HostName, [int]$Port) {
    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        $connected = $async.AsyncWaitHandle.WaitOne(350)
        if ($connected -and $client.Connected) { $client.EndConnect($async) }
        $result = ($connected -and $client.Connected)
        $client.Close()
        return $result
    } catch { return $false }
}

function Test-BackendHealth {
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/health" -TimeoutSec 1
        return ($response.status -eq "ok" -or $response.status -eq "healthy")
    } catch { return $false }
}

function Read-SecretFile {
    if (-not (Test-Path -LiteralPath $SecretsFile)) {
        $ingest = ([guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N"))
        $response = ([guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N"))
        @("set ONYX_TELEMETRY_INGEST_API_KEY=$ingest", "set ONYX_RESPONSE_API_KEY=$response") |
            Set-Content -LiteralPath $SecretsFile -Encoding ascii
        Write-Host "[OK] Generated local API credentials" -ForegroundColor Green
    }

    foreach ($line in Get-Content -LiteralPath $SecretsFile) {
        if ($line -match '^set\s+([^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], "Process")
        }
    }
}

if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Backend Python runtime not found: $PythonExe"
}
if (-not (Test-Path -LiteralPath (Join-Path $WebRoot "node_modules\vite\bin\vite.js"))) {
    throw "Frontend dependencies not found. Run npm install in $WebRoot first."
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js is not available on PATH."
}

Set-Location $ProjectRoot
Read-SecretFile
Write-Section "Starting Onyx"

$backendUp = Test-TcpPort "127.0.0.1" $BackendPort
$frontendUp = Test-TcpPort "127.0.0.1" $FrontendPort

if (-not $backendUp) {
    Start-Process powershell.exe -ArgumentList @(
        "-NoLogo", "-NoExit", "-ExecutionPolicy", "Bypass", "-Command",
        "Set-Location -LiteralPath '$WebRoot'; & '$PythonExe' -m uvicorn backend.server:app --host 0.0.0.0 --port $BackendPort --reload"
    ) -WorkingDirectory $WebRoot -WindowStyle Normal | Out-Null
    Write-Host "[STARTED] Backend window" -ForegroundColor Yellow
} else { Write-Host "[FOUND] Backend already listening on port $BackendPort" -ForegroundColor Green }

if (-not $frontendUp) {
    Start-Process powershell.exe -ArgumentList @(
        "-NoLogo", "-NoExit", "-ExecutionPolicy", "Bypass", "-Command",
        "`$env:ONYX_BACKEND_URL='http://127.0.0.1:$BackendPort'; Set-Location -LiteralPath '$WebRoot'; & node node_modules/vite/bin/vite.js --host 0.0.0.0 --port $FrontendPort"
    ) -WorkingDirectory $WebRoot -WindowStyle Normal | Out-Null
    Write-Host "[STARTED] Frontend window" -ForegroundColor Yellow
} else { Write-Host "[FOUND] Frontend already listening on port $FrontendPort" -ForegroundColor Green }

if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$FrontendPort/" }

Write-Host "`nPress Ctrl+C to stop monitoring. Service windows remain open.`n" -ForegroundColor DarkGray
try {
    while ($true) {
        $backendHealthy = Test-BackendHealth
        $frontendHealthy = Test-TcpPort "127.0.0.1" $FrontendPort
        $backendLabel = if ($backendHealthy) { "RUNNING" } else { "NOT RUNNING" }
        $frontendLabel = if ($frontendHealthy) { "RUNNING" } else { "NOT RUNNING" }
        Write-Host ("`r[{0:HH:mm:ss}]  BACKEND  {1,-11} :{2}   |   FRONTEND  {3,-11} :{4}   " -f (Get-Date), $backendLabel, $BackendPort, $frontendLabel, $FrontendPort) -NoNewline
        Start-Sleep -Seconds 2
        [Console]::Write("`r")
    }
} finally {
    Write-Host "`nMonitoring stopped." -ForegroundColor DarkGray
}
