[CmdletBinding()]
param(
    [string]$OutputDir = '',
    [string]$BundleBaseName = 'OnyxSysmonClientBundle',
    [string]$PresetIngestUrl = '',
    [string]$PresetApiKey = '',
    [ValidateSet('enterprise_20n', 'small_office_10n', 'cloud_hybrid_30n')]
    [string]$PresetTopology = 'enterprise_20n',
    [string]$PresetSource = 'sysmon_forwarder',
    [string]$PresetSourceNode = '',
    [string]$PresetTargetNode = 'node_05_app',
    [int]$PresetPollSeconds = 5,
    [int]$PresetBatchSize = 25,
    [string]$PresetProtectedPorts = '22,80,443,445,3389,5432',
    [switch]$NoTimestamp,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $scriptRootResolved = Split-Path -Parent $MyInvocation.MyCommand.Path
    $OutputDir = Join-Path $scriptRootResolved 'dist'
}

function Write-Stage {
    param([string]$Message)
    Write-Host "[Onyx Bundle] $Message"
}

$requiredFiles = @(
    'setup_other_laptop.ps1',
    'combined_server_client_setup.ps1',
    'one_click_setup.ps1',
    'RUN_SETUP_AS_ADMIN.cmd',
    'forwarder.py',
    'forwarder.env.example',
    'installer_defaults.example.json',
    'client_requirements.txt',
    'sysmonconfig.xml',
    'SETUP_OTHER_LAPTOP.md'
)

foreach ($fileName in $requiredFiles) {
    $sourcePath = Join-Path $PSScriptRoot $fileName
    if (-not (Test-Path $sourcePath)) {
        throw "Missing required file: $sourcePath"
    }
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$timestampSuffix = if ($NoTimestamp) { '' } else { '-' + (Get-Date -Format 'yyyyMMdd-HHmmss') }
$bundleFileName = "$BundleBaseName$timestampSuffix.zip"
$bundlePath = Join-Path $OutputDir $bundleFileName

if ((Test-Path $bundlePath) -and -not $Force) {
    throw "Bundle already exists: $bundlePath (use -Force to overwrite)"
}

$stagingRoot = Join-Path $env:TEMP ("OnyxSysmonBundle_" + [Guid]::NewGuid().ToString('N'))
$bundleRoot = Join-Path $stagingRoot 'OnyxSysmonClient'

Write-Stage "Creating staging folder: $bundleRoot"
New-Item -ItemType Directory -Path $bundleRoot -Force | Out-Null

Write-Stage 'Copying client setup files...'
foreach ($fileName in $requiredFiles) {
    $sourcePath = Join-Path $PSScriptRoot $fileName
    $destPath = Join-Path $bundleRoot $fileName
    Copy-Item -Path $sourcePath -Destination $destPath -Force
}

$defaultsPath = Join-Path $bundleRoot 'installer_defaults.json'
$defaults = [ordered]@{
    ingest_url = if ([string]::IsNullOrWhiteSpace($PresetIngestUrl)) { 'https://YOUR-SERVER-DOMAIN/api/telemetry/ingest' } else { $PresetIngestUrl }
    api_key = $PresetApiKey
    topology = $PresetTopology
    source = if ([string]::IsNullOrWhiteSpace($PresetSource)) { 'sysmon_forwarder' } else { $PresetSource }
    source_node = $PresetSourceNode
    target_node = if ([string]::IsNullOrWhiteSpace($PresetTargetNode)) { 'node_05_app' } else { $PresetTargetNode }
    poll_seconds = [Math]::Max(1, $PresetPollSeconds)
    batch_size = [Math]::Max(1, $PresetBatchSize)
    protected_ports = $PresetProtectedPorts
    install_python_if_missing = $true
    install_sysmon = $true
    start_task = $true
    skip_task_registration = $false
    skip_dependency_install = $false
}
$defaults | ConvertTo-Json -Depth 4 | Set-Content -Path $defaultsPath -Encoding UTF8

$quickStartPath = Join-Path $bundleRoot 'QUICKSTART.txt'
$quickStartText = @"
Onyx Sysmon Client Bundle

1) Extract this zip on the target laptop.
2) Open installer_defaults.json and confirm ingest_url/api_key are correct.
3) Right-click RUN_SETUP_AS_ADMIN.cmd and select "Run as administrator".
4) Verify on server:
   GET /api/telemetry/status?topology=enterprise_20n

For full details, see SETUP_OTHER_LAPTOP.md.
"@
Set-Content -Path $quickStartPath -Value $quickStartText -Encoding UTF8

$manifest = @()
foreach ($fileName in $requiredFiles) {
    $sourcePath = Join-Path $PSScriptRoot $fileName
    $hash = (Get-FileHash -Path $sourcePath -Algorithm SHA256).Hash
    $size = (Get-Item $sourcePath).Length
    $manifest += [pscustomobject]@{
        file = $fileName
        sha256 = $hash
        size_bytes = $size
    }
}
$manifest += [pscustomobject]@{
    file = 'installer_defaults.json'
    sha256 = (Get-FileHash -Path $defaultsPath -Algorithm SHA256).Hash
    size_bytes = (Get-Item $defaultsPath).Length
}
$manifestPath = Join-Path $bundleRoot 'manifest.json'
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Path $manifestPath -Encoding UTF8

if (Test-Path $bundlePath) {
    Remove-Item -Path $bundlePath -Force
}

Write-Stage "Creating bundle: $bundlePath"
Compress-Archive -Path $bundleRoot -DestinationPath $bundlePath -CompressionLevel Optimal -Force

Write-Stage 'Cleaning staging files...'
Remove-Item -Path $stagingRoot -Recurse -Force

Write-Host ''
Write-Host 'Onyx client bundle created successfully.'
Write-Host "Bundle: $bundlePath"
Write-Host 'Contents root folder: OnyxSysmonClient'
Write-Host ''
