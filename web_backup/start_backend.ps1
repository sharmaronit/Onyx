[CmdletBinding()]
param(
    [string]$ApiKey = '',
    [string]$PythonExe = 'd:/Ronit Sharma/vs code/ML Models/.conda/python.exe',
    [string]$BindHost = '0.0.0.0',
    [int]$Port = 8020,
    [switch]$KeepExistingPortProcess
)

$ErrorActionPreference = 'Stop'

function Write-Stage {
    param([string]$Message)
    Write-Host "[Onyx Backend] $Message"
}

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not [string]::IsNullOrWhiteSpace($ApiKey)) {
    $env:ONYX_TELEMETRY_INGEST_API_KEY = $ApiKey
    Write-Stage 'Telemetry ingest API key loaded into environment.'
}
elseif ([string]::IsNullOrWhiteSpace($env:ONYX_TELEMETRY_INGEST_API_KEY)) {
    Write-Warning 'ONYX_TELEMETRY_INGEST_API_KEY is empty. Telemetry ingest auth will be disabled.'
}

if (-not (Test-Path $PythonExe)) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $PythonExe = $pythonCmd.Source
        Write-Stage "Configured python not found. Falling back to: $PythonExe"
    }
    else {
        throw "Python executable not found: $PythonExe"
    }
}

if (-not $KeepExistingPortProcess) {
    $ownerIds = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique

    foreach ($ownerId in $ownerIds) {
        Stop-Process -Id $ownerId -Force -ErrorAction SilentlyContinue
    }

    if ($ownerIds) {
        Write-Stage "Freed port $Port by stopping process IDs: $($ownerIds -join ', ')"
    }
}

Write-Stage "Starting uvicorn on http://${BindHost}:$Port"
Write-Stage "App directory: $appDir"

& $PythonExe -m uvicorn backend.server:app --app-dir $appDir --host $BindHost --port "$Port"
