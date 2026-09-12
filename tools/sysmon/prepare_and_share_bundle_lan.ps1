[CmdletBinding()]
param(
    [string]$ApiKey = '',

    [ValidateSet('enterprise_20n', 'small_office_10n', 'cloud_hybrid_30n')]
    [string]$Topology = 'enterprise_20n',

    [string]$Source = 'sysmon_forwarder',
    [string]$TargetNode = 'node_05_app',

    [int]$BackendPort = 8020,

    [switch]$CreateSmbShare,
    [string]$ShareName = 'OnyxBundle',
    [string]$ShareFolder = 'C:\OnyxBundleShare',

    [switch]$Force
)

$ErrorActionPreference = 'Stop'

throw 'This shared bundle workflow is disabled because it can expose reusable credentials. Use an authenticated package channel and per-device enrollment.'

function Write-Stage {
    param([string]$Message)
    Write-Host "[Onyx LAN Prep] $Message"
}

function Test-IsAdministrator {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-PreferredLocalIPv4 {
    $candidates = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notlike '127.*' -and
            $_.IPAddress -notlike '169.254*' -and
            $_.PrefixOrigin -ne 'WellKnown'
        } |
        Sort-Object InterfaceMetric

    return $candidates | Select-Object -First 1 -ExpandProperty IPAddress
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$combinedScript = Join-Path $scriptRoot 'combined_server_client_setup.ps1'
$downloadSetupScript = Join-Path $scriptRoot 'download_and_setup_other_laptop.ps1'
if (-not (Test-Path $combinedScript)) {
    throw "combined_server_client_setup.ps1 not found at $combinedScript"
}
if (-not (Test-Path $downloadSetupScript)) {
    throw "download_and_setup_other_laptop.ps1 not found at $downloadSetupScript"
}

$localIp = Get-PreferredLocalIPv4
if ([string]::IsNullOrWhiteSpace($localIp)) {
    throw 'Could not detect a LAN IPv4 address automatically.'
}

$serverBase = "http://${localIp}:$BackendPort"
Write-Stage "Using LAN server base URL: $serverBase"

$combinedArgs = @{
    Role = 'server'
    PublicServerBaseUrl = $serverBase
    Topology = $Topology
    Source = $Source
    TargetNode = $TargetNode
    StartBackend = $true
}
if (-not [string]::IsNullOrWhiteSpace($ApiKey)) {
    $combinedArgs.ApiKey = $ApiKey
}
if ($Force) {
    $combinedArgs.Force = $true
}

& $combinedScript @combinedArgs

if (Test-IsAdministrator) {
    $ruleName = "Onyx Backend $BackendPort"
    $existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if (-not $existingRule) {
        Write-Stage "Creating firewall rule for TCP $BackendPort"
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $BackendPort | Out-Null
    }
}
else {
    Write-Warning "Run as Administrator to automatically add firewall allow rule for TCP $BackendPort."
}

$bundle = Get-ChildItem -Path (Join-Path $scriptRoot 'dist\OnyxSysmonClientBundle-*.zip') |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $bundle) {
    throw 'No bundle found in dist after setup.'
}

$sharePathShown = $null
$shareScriptPathShown = $null
if ($CreateSmbShare) {
    if (-not (Test-IsAdministrator)) {
        throw 'CreateSmbShare requires an Administrator PowerShell session.'
    }

    New-Item -Path $ShareFolder -ItemType Directory -Force | Out-Null

    $latestFile = Join-Path $ShareFolder 'OnyxSysmonClientBundle-latest.zip'
    Copy-Item -Path $bundle.FullName -Destination $latestFile -Force
    Copy-Item -Path $downloadSetupScript -Destination (Join-Path $ShareFolder 'download_and_setup_other_laptop.ps1') -Force

    $existingShare = Get-SmbShare -Name $ShareName -ErrorAction SilentlyContinue
    if (-not $existingShare) {
        Write-Stage "Creating SMB share: $ShareName -> $ShareFolder"
        New-SmbShare -Name $ShareName -Path $ShareFolder -ReadAccess 'Everyone' | Out-Null
    }

    $sharePathShown = "\\$env:COMPUTERNAME\$ShareName\OnyxSysmonClientBundle-latest.zip"
    $shareScriptPathShown = "\\$env:COMPUTERNAME\$ShareName\download_and_setup_other_laptop.ps1"
}

Write-Host ''
Write-Host '========================================='
Write-Host 'Onyx LAN Ready Summary'
Write-Host '========================================='
Write-Host "Server Base URL : $serverBase"
Write-Host "Backend Docs    : $serverBase/docs"
Write-Host "Latest Bundle   : $($bundle.FullName)"
if ($sharePathShown) {
    Write-Host "Bundle Share    : $sharePathShown"
    Write-Host "Setup Script    : $shareScriptPathShown"
}
Write-Host ''
Write-Host 'Run on each target laptop (Admin PowerShell):'
if ($sharePathShown) {
    Write-Host "powershell -NoProfile -ExecutionPolicy Bypass -File `"$shareScriptPathShown`" -BundleSource `"$sharePathShown`""
}
else {
    Write-Host '1) Copy latest bundle to target laptop'
    Write-Host '2) Copy download_and_setup_other_laptop.ps1 to target laptop'
    Write-Host '3) Run download_and_setup_other_laptop.ps1 with -BundleSource <that_path>'
}
Write-Host '========================================='
Write-Host ''
