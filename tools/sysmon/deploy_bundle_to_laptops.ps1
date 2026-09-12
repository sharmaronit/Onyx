[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string[]]$ComputerName,

    [string]$BundlePath = '',

    [string]$RemoteDeployDir = 'C:\ProgramData\Onyx\RemoteDeploy',
    [string]$TaskNamePrefix = 'OnyxRemoteClientSetup',

    [pscredential]$Credential,

    [switch]$CopyOnly,
    [switch]$SkipCleanupTask,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

function Write-Stage {
    param([string]$Message)
    Write-Host "[Onyx Remote Deploy] $Message"
}

function Resolve-BundlePath {
    param([string]$InputBundlePath)

    if (-not [string]::IsNullOrWhiteSpace($InputBundlePath)) {
        if (-not (Test-Path $InputBundlePath)) {
            throw "Bundle not found: $InputBundlePath"
        }
        return (Resolve-Path $InputBundlePath).Path
    }

    $latest = Get-ChildItem -Path (Join-Path $PSScriptRoot 'dist\OnyxSysmonClientBundle-*.zip') |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $latest) {
        throw 'No bundle found in tools/sysmon/dist. Run combined_server_client_setup.ps1 -Role server first.'
    }

    return $latest.FullName
}

function New-RemoteBootstrapScript {
    param(
        [string]$DeployDir,
        [string]$OutputPath
    )

    $scriptText = @"
`$ErrorActionPreference = 'Stop'
`$deployDir = '$DeployDir'
`$zipPath = Join-Path `$deployDir 'bundle.zip'
`$extractDir = Join-Path `$deployDir 'bundle'
`$clientDir = Join-Path `$extractDir 'OnyxSysmonClient'
`$logPath = Join-Path `$deployDir 'remote_setup.log'

if (-not (Test-Path `$zipPath)) {
    throw "Bundle file not found: `$zipPath"
}

if (Test-Path `$extractDir) {
    Remove-Item -Path `$extractDir -Recurse -Force
}

Expand-Archive -Path `$zipPath -DestinationPath `$extractDir -Force

if (-not (Test-Path `$clientDir)) {
    throw "Extracted client folder missing: `$clientDir"
}

Set-Location `$clientDir
& .\combined_server_client_setup.ps1 -Role client *>> `$logPath
if (`$LASTEXITCODE -ne 0) {
    exit `$LASTEXITCODE
}
"@

    Set-Content -Path $OutputPath -Value $scriptText -Encoding UTF8
}

function Invoke-Schtasks {
    param(
        [string[]]$Arguments,
        [pscredential]$Cred
    )

    $argsAll = @($Arguments)
    if ($Cred) {
        $password = $Cred.GetNetworkCredential().Password
        $argsAll += @('/U', $Cred.UserName, '/P', $password)
    }

    $output = & schtasks.exe @argsAll 2>&1
    $exitCode = $LASTEXITCODE

    return [pscustomobject]@{
        ExitCode = $exitCode
        Output = ($output -join [Environment]::NewLine)
    }
}

$bundleResolved = Resolve-BundlePath -InputBundlePath $BundlePath
Write-Stage "Using bundle: $bundleResolved"

$results = [System.Collections.Generic.List[object]]::new()

foreach ($computer in $ComputerName) {
    if ([string]::IsNullOrWhiteSpace($computer)) {
        continue
    }

    $node = $computer.Trim()
    $remoteShareRoot = "\\$node\C$"
    $remoteDeployPath = $RemoteDeployDir.TrimEnd('\\')
    $remoteZipPath = Join-Path $remoteDeployPath 'bundle.zip'
    $remoteBootstrapPath = Join-Path $remoteDeployPath 'run_remote_setup.ps1'
    $remoteLogPath = Join-Path $remoteDeployPath 'remote_setup.log'

    $taskSafeNode = ($node -replace '[^A-Za-z0-9_-]', '_')
    $taskName = "$TaskNamePrefix-$taskSafeNode"

    Write-Stage "[$node] Starting deployment..."

    $driveName = "DNR" + (Get-Random -Minimum 1000 -Maximum 9999)
    $driveCreated = $false

    try {
        if ($Credential) {
            New-PSDrive -Name $driveName -PSProvider FileSystem -Root $remoteShareRoot -Credential $Credential -ErrorAction Stop | Out-Null
            $driveCreated = $true
            $remoteUncDeploy = "$driveName`:\" + $remoteDeployPath.Substring(3)
        }
        else {
            $remoteUncDeploy = "\\$node\C$\" + $remoteDeployPath.Substring(3)
        }

        if ($Force -and (Test-Path $remoteUncDeploy)) {
            Remove-Item -Path $remoteUncDeploy -Recurse -Force -ErrorAction SilentlyContinue
        }

        New-Item -Path $remoteUncDeploy -ItemType Directory -Force | Out-Null
        Copy-Item -Path $bundleResolved -Destination (Join-Path $remoteUncDeploy 'bundle.zip') -Force

        $tempBootstrap = Join-Path $env:TEMP ("onyx_remote_bootstrap_" + [Guid]::NewGuid().ToString('N') + '.ps1')
        New-RemoteBootstrapScript -DeployDir $remoteDeployPath -OutputPath $tempBootstrap
        Copy-Item -Path $tempBootstrap -Destination (Join-Path $remoteUncDeploy 'run_remote_setup.ps1') -Force
        Remove-Item -Path $tempBootstrap -Force -ErrorAction SilentlyContinue

        if (-not $CopyOnly) {
            $startTime = (Get-Date).AddMinutes(1).ToString('HH:mm')
            $taskCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$remoteBootstrapPath`""

            $create = Invoke-Schtasks -Arguments @(
                '/Create',
                '/S', $node,
                '/TN', $taskName,
                '/SC', 'ONCE',
                '/ST', $startTime,
                '/RU', 'SYSTEM',
                '/RL', 'HIGHEST',
                '/TR', $taskCommand,
                '/F'
            ) -Cred $Credential

            if ($create.ExitCode -ne 0) {
                throw "schtasks /Create failed: $($create.Output)"
            }

            $run = Invoke-Schtasks -Arguments @(
                '/Run',
                '/S', $node,
                '/TN', $taskName
            ) -Cred $Credential

            if ($run.ExitCode -ne 0) {
                throw "schtasks /Run failed: $($run.Output)"
            }

            if (-not $SkipCleanupTask) {
                $delete = Invoke-Schtasks -Arguments @(
                    '/Delete',
                    '/S', $node,
                    '/TN', $taskName,
                    '/F'
                ) -Cred $Credential

                if ($delete.ExitCode -ne 0) {
                    Write-Warning "[$node] Could not delete temporary task $taskName. You can delete it manually."
                }
            }
        }

        $results.Add([pscustomobject]@{
            computer = $node
            status = 'ok'
            copied_bundle = $true
            triggered_remote_setup = (-not $CopyOnly)
            remote_deploy_dir = $remoteDeployPath
            remote_log_path = $remoteLogPath
            notes = if ($CopyOnly) { 'Copied only. No remote execution requested.' } else { 'Task triggered. Check remote_setup.log on target laptop.' }
        }) | Out-Null

        Write-Stage "[$node] Completed."
    }
    catch {
        $results.Add([pscustomobject]@{
            computer = $node
            status = 'failed'
            copied_bundle = $false
            triggered_remote_setup = $false
            remote_deploy_dir = $remoteDeployPath
            remote_log_path = $remoteLogPath
            notes = $_.Exception.Message
        }) | Out-Null

        Write-Warning "[$node] Deployment failed: $($_.Exception.Message)"
    }
    finally {
        if ($driveCreated) {
            Remove-PSDrive -Name $driveName -ErrorAction SilentlyContinue
        }
    }
}

Write-Host ''
Write-Host 'Deployment summary:'
$results | Format-Table -AutoSize
Write-Host ''

$okCount = ($results | Where-Object { $_.status -eq 'ok' } | Measure-Object).Count
$failCount = ($results | Where-Object { $_.status -eq 'failed' } | Measure-Object).Count
Write-Host "Successful: $okCount"
Write-Host "Failed    : $failCount"

if ($failCount -gt 0) {
    exit 1
}
