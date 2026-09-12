[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BundleSource,

    [string]$WorkDir = "$env:ProgramData\Onyx\LaptopBootstrap",

    [string]$IngestUrl = '',
    [string]$ApiKey = '',

    [ValidateSet('enterprise_20n', 'small_office_10n', 'cloud_hybrid_30n')]
    [string]$Topology = '',

    [string]$Source = '',
    [string]$SourceNode = '',
    [string]$TargetNode = '',

    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'

function Write-Stage {
    param([string]$Message)
    Write-Host "[Onyx Download+Setup] $Message"
}

function Test-IsAdministrator {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdministrator)) {
    throw 'Run this script in an Administrator PowerShell window.'
}

New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
$bundlePath = Join-Path $WorkDir 'OnyxSysmonClientBundle.zip'
$extractPath = Join-Path $WorkDir 'bundle'

if ($BundleSource.StartsWith('http://') -or $BundleSource.StartsWith('https://')) {
    Write-Stage "Downloading bundle from URL: $BundleSource"
    Invoke-WebRequest -Uri $BundleSource -OutFile $bundlePath -UseBasicParsing
}
else {
    if (-not (Test-Path $BundleSource)) {
        throw "Bundle source not found: $BundleSource"
    }

    Write-Stage "Copying bundle from path: $BundleSource"
    Copy-Item -Path $BundleSource -Destination $bundlePath -Force
}

if (Test-Path $extractPath) {
    Remove-Item -Path $extractPath -Recurse -Force
}

Write-Stage 'Extracting client bundle...'
Expand-Archive -Path $bundlePath -DestinationPath $extractPath -Force

$clientDir = Join-Path $extractPath 'OnyxSysmonClient'
if (-not (Test-Path $clientDir)) {
    throw "Client folder not found after extraction: $clientDir"
}

$defaultsPath = Join-Path $clientDir 'installer_defaults.json'
$defaultsExamplePath = Join-Path $clientDir 'installer_defaults.example.json'
if (-not (Test-Path $defaultsPath)) {
    if (Test-Path $defaultsExamplePath) {
        Copy-Item -Path $defaultsExamplePath -Destination $defaultsPath -Force
    }
    else {
        throw "installer_defaults.json and installer_defaults.example.json are both missing in $clientDir"
    }
}

$defaults = Get-Content -Path $defaultsPath -Raw | ConvertFrom-Json

if (-not [string]::IsNullOrWhiteSpace($IngestUrl)) {
    $defaults.ingest_url = $IngestUrl
}
if (-not [string]::IsNullOrWhiteSpace($ApiKey)) {
    $defaults.api_key = $ApiKey
}
if (-not [string]::IsNullOrWhiteSpace($Topology)) {
    $defaults.topology = $Topology
}
if (-not [string]::IsNullOrWhiteSpace($Source)) {
    $defaults.source = $Source
}
if (-not [string]::IsNullOrWhiteSpace($SourceNode)) {
    $defaults.source_node = $SourceNode
}
if (-not [string]::IsNullOrWhiteSpace($TargetNode)) {
    $defaults.target_node = $TargetNode
}

$defaults | ConvertTo-Json -Depth 6 | Set-Content -Path $defaultsPath -Encoding UTF8

if (-not $SkipInstall) {
    $combinedSetup = Join-Path $clientDir 'combined_server_client_setup.ps1'
    $oneClick = Join-Path $clientDir 'one_click_setup.ps1'

    if (Test-Path $combinedSetup) {
        Write-Stage 'Running client installation...'
        Set-Location $clientDir
        & $combinedSetup -Role client
    }
    elseif (Test-Path $oneClick) {
        Write-Stage 'Running one-click installation...'
        Set-Location $clientDir
        & $oneClick
    }
    else {
        throw "No client installer script found in $clientDir"
    }
}

Write-Host ''
Write-Host 'Onyx download + setup finished.'
Write-Host "WorkDir: $WorkDir"
Write-Host "ClientDir: $clientDir"
Write-Host "Defaults: $defaultsPath"
if ($SkipInstall) {
    Write-Host 'Install step skipped. Run combined_server_client_setup.ps1 -Role client from ClientDir when ready.'
}
Write-Host ''
