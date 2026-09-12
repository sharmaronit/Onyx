[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('server', 'client')]
    [string]$Role,

    [string]$PublicServerBaseUrl = '',
    [string]$ApiKey = '',
    [ValidateSet('enterprise_20n', 'small_office_10n', 'cloud_hybrid_30n')]
    [string]$Topology = 'enterprise_20n',
    [string]$Source = 'sysmon_forwarder',
    [string]$TargetNode = 'node_05_app',

    [switch]$StartBackend,
    [string]$BackendPython = 'd:/Ronit Sharma/vs code/ML Models/.conda/python.exe',
    [string]$BackendWorkingDir = 'D:/dehradun/web',
    [int]$BackendPort = 8020,

    [string]$OutputDir = '',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

function Write-Stage {
    param([string]$Message)
    Write-Host "[Onyx Combined Setup] $Message"
}

function Normalize-ServerBaseUrl {
    param([string]$Url)

    $value = ($Url | ForEach-Object { $_.Trim() })
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw 'PublicServerBaseUrl is required in server mode. Example: https://api.yourdomain.com'
    }

    if (-not ($value.StartsWith('http://') -or $value.StartsWith('https://'))) {
        throw 'PublicServerBaseUrl must start with http:// or https://'
    }

    return $value.TrimEnd('/')
}

function New-ApiKeyValue {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return [Convert]::ToBase64String($bytes)
}

if ($Role -eq 'client') {
    $oneClickPath = Join-Path $PSScriptRoot 'one_click_setup.ps1'
    if (-not (Test-Path $oneClickPath)) {
        throw "one_click_setup.ps1 not found at $oneClickPath"
    }

    Write-Stage 'Running one-click client installer...'
    & $oneClickPath
    exit $LASTEXITCODE
}

$serverBase = Normalize-ServerBaseUrl -Url $PublicServerBaseUrl
$ingestUrl = "$serverBase/api/telemetry/ingest"
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = New-ApiKeyValue
    Write-Stage 'Generated new API key for telemetry ingest.'
}

$env:ONYX_TELEMETRY_INGEST_API_KEY = $ApiKey
Write-Stage 'Applied ONYX_TELEMETRY_INGEST_API_KEY to current PowerShell process.'

if ($StartBackend) {
    Write-Stage "Starting backend on 0.0.0.0:$BackendPort"

    $ownerPids = Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $ownerPids) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }

    if (-not (Test-Path $BackendPython)) {
        throw "Backend python executable not found: $BackendPython"
    }
    if (-not (Test-Path $BackendWorkingDir)) {
        throw "Backend working directory not found: $BackendWorkingDir"
    }

    Start-Process -FilePath $BackendPython `
        -ArgumentList @('-m', 'uvicorn', 'backend.server:app', '--host', '0.0.0.0', '--port', "$BackendPort") `
        -WorkingDirectory $BackendWorkingDir | Out-Null
}

$bundleBuilder = Join-Path $PSScriptRoot 'build_client_bundle.ps1'
if (-not (Test-Path $bundleBuilder)) {
    throw "build_client_bundle.ps1 not found at $bundleBuilder"
}

$buildArgs = @{
    PresetIngestUrl = $ingestUrl
    PresetApiKey = $ApiKey
    PresetTopology = $Topology
    PresetSource = $Source
    PresetTargetNode = $TargetNode
}

if (-not [string]::IsNullOrWhiteSpace($OutputDir)) {
    $buildArgs.OutputDir = $OutputDir
}
if ($Force) {
    $buildArgs.Force = $true
}

Write-Stage 'Building prefilled client bundle...'
& $bundleBuilder @buildArgs

$resolvedOutputDir = if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    Join-Path $PSScriptRoot 'dist'
} else {
    $OutputDir
}

$bundle = Get-ChildItem -Path (Join-Path $resolvedOutputDir 'OnyxSysmonClientBundle-*.zip') |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $bundle) {
    throw 'Bundle generation succeeded but no bundle file was found.'
}

Write-Host ''
Write-Host '========================================='
Write-Host 'Onyx Multi-Laptop Setup Summary'
Write-Host '========================================='
Write-Host "Server Base URL : $serverBase"
Write-Host "Ingest URL      : $ingestUrl"
Write-Host "API Key         : $ApiKey"
Write-Host "Bundle Path     : $($bundle.FullName)"
Write-Host ''
Write-Host 'Next on each target laptop:'
Write-Host '1) Copy and extract the bundle'
Write-Host '2) Right-click RUN_SETUP_AS_ADMIN.cmd -> Run as administrator'
Write-Host '========================================='
Write-Host ''
