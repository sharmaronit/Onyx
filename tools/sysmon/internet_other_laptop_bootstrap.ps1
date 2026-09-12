[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$PublishBaseUrl,

    [string]$WorkDir = "$env:ProgramData\Onyx\InternetBootstrap",

    [string]$IngestUrl = '',
    [string]$ApiKey = '',

    [ValidateSet('enterprise_20n', 'small_office_10n', 'cloud_hybrid_30n')]
    [string]$Topology = '',

    [string]$Source = '',
    [string]$SourceNode = '',
    [string]$TargetNode = ''
)

$ErrorActionPreference = 'Stop'

function Write-Stage {
    param([string]$Message)
    Write-Host "[Onyx Internet Client] $Message"
}

function Test-IsAdministrator {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdministrator)) {
    Write-Host 'Requesting administrator privileges...'

    $args = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"{0}"' -f $MyInvocation.MyCommand.Path))
    $args += @('-PublishBaseUrl', ('"{0}"' -f $PublishBaseUrl))

    if (-not [string]::IsNullOrWhiteSpace($WorkDir)) {
        $args += @('-WorkDir', ('"{0}"' -f $WorkDir))
    }
    if (-not [string]::IsNullOrWhiteSpace($IngestUrl)) {
        $args += @('-IngestUrl', ('"{0}"' -f $IngestUrl))
    }
    if (-not [string]::IsNullOrWhiteSpace($ApiKey)) {
        $args += @('-ApiKey', ('"{0}"' -f $ApiKey))
    }
    if (-not [string]::IsNullOrWhiteSpace($Topology)) {
        $args += @('-Topology', ('"{0}"' -f $Topology))
    }
    if (-not [string]::IsNullOrWhiteSpace($Source)) {
        $args += @('-Source', ('"{0}"' -f $Source))
    }
    if (-not [string]::IsNullOrWhiteSpace($SourceNode)) {
        $args += @('-SourceNode', ('"{0}"' -f $SourceNode))
    }
    if (-not [string]::IsNullOrWhiteSpace($TargetNode)) {
        $args += @('-TargetNode', ('"{0}"' -f $TargetNode))
    }

    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $args | Out-Null
    exit 0
}

$base = $PublishBaseUrl.Trim().TrimEnd('/')
if (-not ($base.StartsWith('http://') -or $base.StartsWith('https://'))) {
    throw 'PublishBaseUrl must start with http:// or https://'
}

New-Item -Path $WorkDir -ItemType Directory -Force | Out-Null
$downloadScriptPath = Join-Path $WorkDir 'download_and_setup_other_laptop.ps1'
$downloadScriptUrl = "$base/download_and_setup_other_laptop.ps1"
$bundleUrl = "$base/OnyxSysmonClientBundle-latest.zip"

Write-Stage "Downloading helper script from: $downloadScriptUrl"
Invoke-WebRequest -Uri $downloadScriptUrl -OutFile $downloadScriptPath -UseBasicParsing

$runArgs = @{
    BundleSource = $bundleUrl
}

if (-not [string]::IsNullOrWhiteSpace($IngestUrl)) {
    $runArgs.IngestUrl = $IngestUrl
}
if (-not [string]::IsNullOrWhiteSpace($ApiKey)) {
    $runArgs.ApiKey = $ApiKey
}
if (-not [string]::IsNullOrWhiteSpace($Topology)) {
    $runArgs.Topology = $Topology
}
if (-not [string]::IsNullOrWhiteSpace($Source)) {
    $runArgs.Source = $Source
}
if (-not [string]::IsNullOrWhiteSpace($SourceNode)) {
    $runArgs.SourceNode = $SourceNode
}
if (-not [string]::IsNullOrWhiteSpace($TargetNode)) {
    $runArgs.TargetNode = $TargetNode
}

Write-Stage 'Running downloaded setup helper...'
& $downloadScriptPath @runArgs

Write-Host ''
Write-Host 'Onyx internet bootstrap completed on this laptop.'
Write-Host "PublishBaseUrl: $base"
Write-Host "Downloaded helper: $downloadScriptPath"
Write-Host ''
