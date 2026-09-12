[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

function Write-Stage {
    param([string]$Message)
    Write-Host "[Onyx One-Click] $Message"
}

function Test-IsAdministrator {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$defaultsPath = Join-Path $scriptRoot 'installer_defaults.json'
$setupPath = Join-Path $scriptRoot 'setup_other_laptop.ps1'

if (-not (Test-Path $setupPath)) {
    throw "setup_other_laptop.ps1 not found at $setupPath"
}

if (-not (Test-IsAdministrator)) {
    Write-Host 'Requesting administrator privileges...'
    $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"{0}"' -f $MyInvocation.MyCommand.Path))
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $argList | Out-Null
    exit 0
}

if (-not (Test-Path $defaultsPath)) {
    throw "installer_defaults.json not found at $defaultsPath"
}

$defaults = Get-Content -Path $defaultsPath -Raw | ConvertFrom-Json
$ingestUrl = [string]($defaults.ingest_url)
if ([string]::IsNullOrWhiteSpace($ingestUrl) -or $ingestUrl -match 'YOUR-SERVER-DOMAIN') {
    throw 'installer_defaults.json is not configured. Set ingest_url before running one-click setup.'
}

$setupArgs = @{
    IngestUrl = $ingestUrl
    ApiKey = [string]($defaults.api_key)
    Topology = [string]($defaults.topology)
    Source = [string]($defaults.source)
    TargetNode = [string]($defaults.target_node)
    PollSeconds = [int]($defaults.poll_seconds)
    BatchSize = [int]($defaults.batch_size)
    ProtectedPorts = [string]($defaults.protected_ports)
}

if (-not [string]::IsNullOrWhiteSpace([string]($defaults.source_node))) {
    $setupArgs.SourceNode = [string]($defaults.source_node)
}

if ([bool]($defaults.install_python_if_missing)) {
    $setupArgs.InstallPythonIfMissing = $true
}
if ([bool]($defaults.install_sysmon)) {
    $setupArgs.InstallSysmon = $true
}
if ([bool]($defaults.start_task)) {
    $setupArgs.StartTask = $true
}
if ([bool]($defaults.skip_task_registration)) {
    $setupArgs.SkipTaskRegistration = $true
}
if ([bool]($defaults.skip_dependency_install)) {
    $setupArgs.SkipDependencyInstall = $true
}

Write-Stage 'Starting setup_other_laptop.ps1 with prefilled configuration...'
& $setupPath @setupArgs

Write-Host ''
Write-Host 'One-click setup completed.'
Write-Host "Config used: $defaultsPath"
Write-Host ''
