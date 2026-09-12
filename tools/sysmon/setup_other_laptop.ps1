[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$IngestUrl,

    [string]$ApiKey = '',

    [ValidateSet('enterprise_20n', 'small_office_10n', 'cloud_hybrid_30n')]
    [string]$Topology = 'enterprise_20n',

    [string]$Source = 'sysmon_forwarder',
    [string]$SourceNode = '',
    [string]$TargetNode = 'node_05_app',

    [int]$PollSeconds = 5,
    [int]$BatchSize = 25,
    [string]$ProtectedPorts = '22,80,443,445,3389,5432',

    [string]$InstallDir = "$env:ProgramData\\Onyx\\SysmonForwarder",
    [string]$TaskName = 'OnyxSysmonForwarder',

    [switch]$InstallSysmon,
    [switch]$InstallPythonIfMissing,
    [switch]$SkipDependencyInstall,
    [switch]$SkipTaskRegistration,
    [switch]$StartTask
)

$ErrorActionPreference = 'Stop'

function Write-Stage {
    param([string]$Message)
    Write-Host "[Onyx Setup] $Message"
}

function Test-IsAdministrator {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Resolve-PythonPath {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return $pythonCmd.Source
    }

    if ($InstallPythonIfMissing) {
        $wingetCmd = Get-Command winget -ErrorAction SilentlyContinue
        if (-not $wingetCmd) {
            throw 'Python is missing and winget is not available. Install Python 3.11+ manually, then rerun.'
        }

        Write-Stage 'Python not found. Installing Python 3.11 via winget...'
        & winget install -e --id Python.Python.3.11 --accept-source-agreements --accept-package-agreements | Out-Null
        $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
        if ($pythonCmd) {
            return $pythonCmd.Source
        }
        throw 'Python installation completed but python command is still not available. Reopen PowerShell and rerun.'
    }

    throw 'Python 3.11+ is required. Install it or rerun with -InstallPythonIfMissing.'
}

function Write-ForwarderEnv {
    param(
        [string]$EnvPath,
        [string]$EnvIngestUrl,
        [string]$EnvApiKey,
        [string]$EnvTopology,
        [string]$EnvSource,
        [string]$EnvSourceNode,
        [string]$EnvTargetNode,
        [int]$EnvPollSeconds,
        [int]$EnvBatchSize,
        [string]$EnvProtectedPorts,
        [string]$StatePath,
        [string]$IpMapPath
    )

    $lines = @(
        "ONYX_INGEST_URL=$EnvIngestUrl",
        "ONYX_INGEST_API_KEY=$EnvApiKey",
        "ONYX_TOPOLOGY=$EnvTopology",
        "ONYX_SOURCE=$EnvSource",
        "ONYX_SOURCE_NODE=$EnvSourceNode",
        "ONYX_TARGET_NODE=$EnvTargetNode",
        "ONYX_POLL_SECONDS=$EnvPollSeconds",
        "ONYX_BATCH_SIZE=$EnvBatchSize",
        "ONYX_PROTECTED_PORTS=$EnvProtectedPorts",
        "ONYX_STATE_PATH=$StatePath",
        "ONYX_IP_NODE_MAP_PATH=$IpMapPath"
    )

    Set-Content -Path $EnvPath -Value $lines -Encoding UTF8
}

function Create-RunnerScript {
    param(
        [string]$RunnerPath,
        [string]$EnvPath,
        [string]$PythonPath,
        [string]$ForwarderPath
    )

    $safeEnvPath = $EnvPath.Replace("'", "''")
    $safePythonPath = $PythonPath.Replace("'", "''")
    $safeForwarderPath = $ForwarderPath.Replace("'", "''")

    $content = @"
`$ErrorActionPreference = 'Stop'
`$envFile = '$safeEnvPath'
if (-not (Test-Path `$envFile)) {
    throw "forwarder.env not found at `$envFile"
}

foreach (`$line in Get-Content `$envFile) {
    if ([string]::IsNullOrWhiteSpace(`$line)) { continue }
    if (`$line.TrimStart().StartsWith('#')) { continue }

    `$parts = `$line.Split('=', 2)
    if (`$parts.Count -ne 2) { continue }

    `$name = `$parts[0].Trim()
    `$value = `$parts[1]
    [System.Environment]::SetEnvironmentVariable(`$name, `$value, 'Process')
}

& '$safePythonPath' '$safeForwarderPath'
"@

    Set-Content -Path $RunnerPath -Value $content -Encoding UTF8
}

function Install-OrUpdateSysmon {
    param(
        [string]$SysmonConfigPath
    )

    Write-Stage 'Downloading Sysmon package...'
    $tempDir = Join-Path $env:TEMP ("OnyxSysmon_" + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

    $zipPath = Join-Path $tempDir 'Sysmon.zip'
    Invoke-WebRequest -Uri 'https://download.sysinternals.com/files/Sysmon.zip' -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $tempDir -Force

    $sysmonExe = Join-Path $tempDir 'Sysmon64.exe'
    if (-not (Test-Path $sysmonExe)) {
        throw 'Sysmon64.exe was not found after extraction.'
    }

    $service = Get-Service -Name 'Sysmon64' -ErrorAction SilentlyContinue
    if ($service) {
        Write-Stage 'Sysmon detected. Updating configuration...'
        & $sysmonExe -accepteula -c $SysmonConfigPath | Out-Null
    }
    else {
        Write-Stage 'Installing Sysmon service...'
        & $sysmonExe -accepteula -i $SysmonConfigPath | Out-Null
    }

    Write-Stage 'Sysmon installation/config update completed.'
}

if (-not $IngestUrl.Trim().ToLower().EndsWith('/api/telemetry/ingest')) {
    throw 'Ingest URL must end with /api/telemetry/ingest (example: https://your-server/api/telemetry/ingest)'
}

$needsAdmin = $InstallSysmon -or (-not $SkipTaskRegistration)
if ($needsAdmin -and -not (Test-IsAdministrator)) {
    throw 'Run this script in an Administrator PowerShell session when using task registration or Sysmon installation.'
}

if ([string]::IsNullOrWhiteSpace($SourceNode)) {
    $SourceNode = $env:COMPUTERNAME
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$forwarderSource = Join-Path $scriptRoot 'forwarder.py'
$requirementsSource = Join-Path $scriptRoot 'client_requirements.txt'
$sysmonConfigSource = Join-Path $scriptRoot 'sysmonconfig.xml'

if (-not (Test-Path $forwarderSource)) {
    throw "Missing forwarder source file: $forwarderSource"
}
if (-not (Test-Path $requirementsSource)) {
    throw "Missing requirements file: $requirementsSource"
}
if (-not (Test-Path $sysmonConfigSource)) {
    throw "Missing Sysmon config file: $sysmonConfigSource"
}

Write-Stage "Preparing install directory: $InstallDir"
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

$forwarderDest = Join-Path $InstallDir 'forwarder.py'
$sysmonConfigDest = Join-Path $InstallDir 'sysmonconfig.xml'
$envPath = Join-Path $InstallDir 'forwarder.env'
$ipMapPath = Join-Path $InstallDir 'ip_to_node_map.json'
$statePath = Join-Path $InstallDir 'forwarder_state.json'
$runnerPath = Join-Path $InstallDir 'run_forwarder.ps1'

Copy-Item -Path $forwarderSource -Destination $forwarderDest -Force
Copy-Item -Path $sysmonConfigSource -Destination $sysmonConfigDest -Force

if (-not (Test-Path $ipMapPath)) {
    '{}' | Set-Content -Path $ipMapPath -Encoding UTF8
}

$venvPython = Join-Path $InstallDir '.venv\\Scripts\\python.exe'
if (-not $SkipDependencyInstall) {
    $pythonPath = Resolve-PythonPath

    Write-Stage 'Creating/updating Python virtual environment...'
    & $pythonPath -m venv (Join-Path $InstallDir '.venv')

    if (-not (Test-Path $venvPython)) {
        throw "Virtual environment python not found: $venvPython"
    }

    Write-Stage 'Installing forwarder dependencies...'
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r $requirementsSource
}
elseif (-not (Test-Path $venvPython)) {
    throw 'SkipDependencyInstall was set but no virtual environment exists. Remove the switch or create .venv first.'
}

Write-Stage 'Writing forwarder environment configuration...'
Write-ForwarderEnv `
    -EnvPath $envPath `
    -EnvIngestUrl $IngestUrl `
    -EnvApiKey $ApiKey `
    -EnvTopology $Topology `
    -EnvSource $Source `
    -EnvSourceNode $SourceNode `
    -EnvTargetNode $TargetNode `
    -EnvPollSeconds $PollSeconds `
    -EnvBatchSize $BatchSize `
    -EnvProtectedPorts $ProtectedPorts `
    -StatePath $statePath `
    -IpMapPath $ipMapPath

Write-Stage 'Creating forwarder runner script...'
Create-RunnerScript -RunnerPath $runnerPath -EnvPath $envPath -PythonPath $venvPython -ForwarderPath $forwarderDest

if ($InstallSysmon) {
    Install-OrUpdateSysmon -SysmonConfigPath $sysmonConfigDest
}

if (-not $SkipTaskRegistration) {
    Write-Stage "Registering startup task: $TaskName"
    $actionArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$runnerPath`""
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $actionArgs
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null

    if ($StartTask) {
        Start-ScheduledTask -TaskName $TaskName
        Write-Stage 'Startup task started.'
    }
}

$healthUrl = $IngestUrl.Substring(0, $IngestUrl.Length - '/api/telemetry/ingest'.Length) + '/api/health'
try {
    $health = Invoke-RestMethod -Method Get -Uri $healthUrl -TimeoutSec 15
    Write-Stage "Server health check: $($health.status)"
}
catch {
    Write-Warning "Server health check failed ($healthUrl): $($_.Exception.Message)"
}

Write-Host ''
Write-Host 'Onyx laptop setup completed.'
Write-Host "InstallDir: $InstallDir"
Write-Host "Runner: $runnerPath"
if (-not $SkipTaskRegistration) {
    Write-Host "Task: $TaskName"
}
Write-Host 'Update ip_to_node_map.json if you want destination IP -> node mapping.'
Write-Host ''
