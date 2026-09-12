[CmdletBinding()]
param(
    [string]$StatePath = ''
)

$ErrorActionPreference = 'Stop'

function Write-Stage {
    param([string]$Message)
    Write-Host "[Onyx Internet Stop] $Message"
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($StatePath)) {
    $StatePath = Join-Path (Join-Path $scriptRoot 'internet_publish') 'internet_access_state.json'
}

if (-not (Test-Path $StatePath)) {
    throw "State file not found: $StatePath"
}

$state = Get-Content -Path $StatePath -Raw | ConvertFrom-Json

$procIds = @(
    [int]$state.backend_pid,
    [int]$state.backend_tunnel_pid,
    [int]$state.bundle_server_pid,
    [int]$state.bundle_tunnel_pid
) | Where-Object { $_ -gt 0 } | Select-Object -Unique

foreach ($procId in $procIds) {
    try {
        $proc = Get-Process -Id $procId -ErrorAction Stop
        Stop-Process -Id $procId -Force
        Write-Stage "Stopped PID $procId ($($proc.ProcessName))"
    }
    catch {
        Write-Stage "PID $procId was not running."
    }
}

Write-Host ''
Write-Host 'Onyx internet access processes have been stopped.'
Write-Host "State file: $StatePath"
Write-Host ''
