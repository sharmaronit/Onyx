[CmdletBinding()]
param(
    [string]$ApiKey = '',

    [ValidateSet('enterprise_20n', 'small_office_10n', 'cloud_hybrid_30n')]
    [string]$Topology = 'enterprise_20n',

    [string]$Source = 'sysmon_forwarder',
    [string]$TargetNode = 'node_05_app',

    [string]$BackendPython = '',
    [string]$BackendWorkingDir = '',
    [int]$BackendPort = 8020,

    [int]$BundlePort = 8081,
    [string]$PublishDir = '',

    [switch]$UsePublicDns,
    [string[]]$DnsServers = @('1.1.1.1', '8.8.8.8'),

    [switch]$InstallCloudflaredIfMissing,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

function Write-Stage {
    param([string]$Message)
    Write-Host "[Onyx Internet Setup] $Message"
}

function New-ApiKeyValue {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return [Convert]::ToBase64String($bytes)
}

function Resolve-PythonExecutable {
    param([string]$Preferred)

    if (-not [string]::IsNullOrWhiteSpace($Preferred)) {
        if (-not (Test-Path $Preferred)) {
            throw "BackendPython not found: $Preferred"
        }
        return $Preferred
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return $pythonCmd.Source
    }

    throw 'Python executable not found. Pass -BackendPython or install Python.'
}

function Resolve-CloudflaredExecutable {
    param([switch]$AllowInstall)

    function Find-CloudflaredCandidate {
        $cloudflaredCmd = Get-Command cloudflared -ErrorAction SilentlyContinue
        if ($cloudflaredCmd) {
            return $cloudflaredCmd.Source
        }

        $paths = @(
            'C:\Program Files\cloudflared\cloudflared.exe',
            (Join-Path $scriptRoot 'bin\cloudflared.exe')
        )

        foreach ($path in $paths) {
            if (-not [string]::IsNullOrWhiteSpace($path) -and (Test-Path $path)) {
                return $path
            }
        }

        $wingetPackages = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
        if (Test-Path $wingetPackages) {
            $pkgDir = Get-ChildItem -Path $wingetPackages -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -like 'Cloudflare.cloudflared*' } |
                Select-Object -First 1

            if ($pkgDir) {
                $pkgExe = Get-ChildItem -Path $pkgDir.FullName -Recurse -Filter 'cloudflared*.exe' -ErrorAction SilentlyContinue |
                    Select-Object -First 1
                if ($pkgExe) {
                    return $pkgExe.FullName
                }
            }
        }

        return ''
    }

    $candidate = Find-CloudflaredCandidate
    if (-not [string]::IsNullOrWhiteSpace($candidate)) {
        return $candidate
    }

    if (-not $AllowInstall) {
        throw 'cloudflared is not installed. Re-run with -InstallCloudflaredIfMissing or install with winget.'
    }

    $wingetCmd = Get-Command winget -ErrorAction SilentlyContinue
    if ($wingetCmd) {
        Write-Stage 'Installing cloudflared with winget...'
        & winget install -e --id Cloudflare.cloudflared --accept-source-agreements --accept-package-agreements | Out-Null

        $candidate = Find-CloudflaredCandidate
        if (-not [string]::IsNullOrWhiteSpace($candidate)) {
            return $candidate
        }
    }

    $binDir = Join-Path $scriptRoot 'bin'
    New-Item -Path $binDir -ItemType Directory -Force | Out-Null
    $manualPath = Join-Path $binDir 'cloudflared.exe'

    Write-Stage "Downloading cloudflared directly: $manualPath"
    Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile $manualPath -UseBasicParsing

    if (Test-Path $manualPath) {
        return $manualPath
    }

    throw 'cloudflared installation failed: executable could not be resolved.'
}

function Stop-PortListeners {
    param([int]$Port)

    $ownerIds = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique

    foreach ($ownerId in $ownerIds) {
        Stop-Process -Id $ownerId -Force -ErrorAction SilentlyContinue
    }
}

function Start-LoggedProcess {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$WorkingDirectory,
        [string]$StdOutPath,
        [string]$StdErrPath
    )

    if (Test-Path $StdOutPath) { Remove-Item -Path $StdOutPath -Force -ErrorAction SilentlyContinue }
    if (Test-Path $StdErrPath) { Remove-Item -Path $StdErrPath -Force -ErrorAction SilentlyContinue }

    return Start-Process -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $StdOutPath `
        -RedirectStandardError $StdErrPath `
        -PassThru -WindowStyle Hidden
}

function Wait-HttpReachable {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 40
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        }
        catch {
            # Keep waiting until timeout.
        }
        Start-Sleep -Milliseconds 500
    }

    throw "Timed out waiting for HTTP endpoint: $Url"
}

function Wait-TryCloudflareUrl {
    param(
        [string]$StdOutPath,
        [string]$StdErrPath,
        [int]$TimeoutSeconds = 120
    )

    function Find-UrlFromText {
        param([string]$Text)

        if ([string]::IsNullOrWhiteSpace($Text)) {
            return ''
        }

        $patterns = @(
                'https://[a-z0-9-]+\.trycloudflare\.com',
                'https://[^\s"''<>]+\.trycloudflare\.com'
        )

        foreach ($pattern in $patterns) {
            $matches = [regex]::Matches($Text, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
            foreach ($match in $matches) {
                $url = $match.Value.TrimEnd('/')

                try {
                    $host = ([Uri]$url).Host.ToLowerInvariant()
                    if ($host -ne 'api.trycloudflare.com') {
                        return $url
                    }
                }
                catch {
                    # Keep scanning remaining matches.
                }
            }
        }

        return ''
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while ((Get-Date) -lt $deadline) {
        $combined = ''
        if (Test-Path $StdOutPath) {
            $combined += (Get-Content -Path $StdOutPath -Raw -ErrorAction SilentlyContinue)
        }
        if (Test-Path $StdErrPath) {
            $combined += "`n"
            $combined += (Get-Content -Path $StdErrPath -Raw -ErrorAction SilentlyContinue)
        }

        $found = Find-UrlFromText -Text $combined
        if (-not [string]::IsNullOrWhiteSpace($found)) {
            return $found
        }

        Start-Sleep -Milliseconds 500
    }

    # One final fallback scan in case file access was intermittent while process was writing.
    $fallbackText = ''
    if (Test-Path $StdOutPath) {
        $fallbackText += (Get-Content -Path $StdOutPath -Tail 300 -ErrorAction SilentlyContinue | Out-String)
    }
    if (Test-Path $StdErrPath) {
        $fallbackText += (Get-Content -Path $StdErrPath -Tail 300 -ErrorAction SilentlyContinue | Out-String)
    }

    $fallbackFound = Find-UrlFromText -Text $fallbackText
    if (-not [string]::IsNullOrWhiteSpace($fallbackFound)) {
        return $fallbackFound
    }

    throw "Timed out waiting for trycloudflare URL in logs: $StdOutPath and $StdErrPath"
}

function Set-PublicDnsOnActiveInterfaces {
    param([string[]]$Servers)

    $activeAliases = Get-NetIPConfiguration -ErrorAction SilentlyContinue |
        Where-Object { $_.IPv4DefaultGateway -ne $null } |
        Select-Object -ExpandProperty InterfaceAlias -Unique

    if (-not $activeAliases) {
        throw 'No active network interfaces with IPv4 default gateway were found.'
    }

    foreach ($alias in $activeAliases) {
        Write-Stage "Setting DNS for interface '$alias' -> $($Servers -join ', ')"
        Set-DnsClientServerAddress -InterfaceAlias $alias -ServerAddresses $Servers -ErrorAction Stop
    }

    & ipconfig /flushdns | Out-Null
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptRoot)

if ([string]::IsNullOrWhiteSpace($BackendWorkingDir)) {
    $BackendWorkingDir = Join-Path $repoRoot 'web'
}
if ([string]::IsNullOrWhiteSpace($PublishDir)) {
    $PublishDir = Join-Path $scriptRoot 'internet_publish'
}

$buildBundleScript = Join-Path $scriptRoot 'build_client_bundle.ps1'
$downloadSetupScript = Join-Path $scriptRoot 'download_and_setup_other_laptop.ps1'
$internetBootstrapScript = Join-Path $scriptRoot 'internet_other_laptop_bootstrap.ps1'

foreach ($required in @($buildBundleScript, $downloadSetupScript, $internetBootstrapScript)) {
    if (-not (Test-Path $required)) {
        throw "Required file not found: $required"
    }
}

$pythonExe = Resolve-PythonExecutable -Preferred $BackendPython
$cloudflaredExe = Resolve-CloudflaredExecutable -AllowInstall:$InstallCloudflaredIfMissing

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = New-ApiKeyValue
}
$env:ONYX_TELEMETRY_INGEST_API_KEY = $ApiKey

New-Item -Path $PublishDir -ItemType Directory -Force | Out-Null
$logDir = Join-Path $PublishDir 'logs'
New-Item -Path $logDir -ItemType Directory -Force | Out-Null
$runId = [Guid]::NewGuid().ToString('N')

$existingStatePath = Join-Path $PublishDir 'internet_access_state.json'
if (Test-Path $existingStatePath) {
    try {
        $existingState = Get-Content -Path $existingStatePath -Raw | ConvertFrom-Json
        $existingProcIds = @(
            [int]$existingState.backend_pid,
            [int]$existingState.backend_tunnel_pid,
            [int]$existingState.bundle_server_pid,
            [int]$existingState.bundle_tunnel_pid
        ) | Where-Object { $_ -gt 0 } | Select-Object -Unique

        foreach ($existingProcId in $existingProcIds) {
            Stop-Process -Id $existingProcId -Force -ErrorAction SilentlyContinue
        }
    }
    catch {
        Write-Warning "Could not parse/stop previous internet access state from $existingStatePath"
    }
}

Write-Stage "Using python: $pythonExe"
Write-Stage "Using cloudflared: $cloudflaredExe"

if ($UsePublicDns) {
    Write-Stage 'Applying public DNS servers for tunnel reliability...'
    Set-PublicDnsOnActiveInterfaces -Servers $DnsServers
}

Write-Stage "Restarting backend on 127.0.0.1:$BackendPort"
Stop-PortListeners -Port $BackendPort
$backendStdOut = Join-Path $logDir ("backend.$runId.out.log")
$backendStdErr = Join-Path $logDir ("backend.$runId.err.log")
$backendProc = Start-LoggedProcess `
    -FilePath $pythonExe `
    -ArgumentList @('-m', 'uvicorn', 'backend.server:app', '--host', '127.0.0.1', '--port', "$BackendPort") `
    -WorkingDirectory $BackendWorkingDir `
    -StdOutPath $backendStdOut `
    -StdErrPath $backendStdErr
Wait-HttpReachable -Url "http://127.0.0.1:$BackendPort/docs"

Write-Stage 'Starting tunnel for backend API...'
$backendTunnelOut = Join-Path $logDir ("backend_tunnel.$runId.out.log")
$backendTunnelErr = Join-Path $logDir ("backend_tunnel.$runId.err.log")
$backendTunnelProc = Start-LoggedProcess `
    -FilePath $cloudflaredExe `
    -ArgumentList @('tunnel', '--url', "http://127.0.0.1:$BackendPort", '--no-autoupdate') `
    -WorkingDirectory $PublishDir `
    -StdOutPath $backendTunnelOut `
    -StdErrPath $backendTunnelErr
try {
    $backendPublicUrl = Wait-TryCloudflareUrl -StdOutPath $backendTunnelOut -StdErrPath $backendTunnelErr
}
catch {
    $backendErrText = ''
    if (Test-Path $backendTunnelErr) {
        $backendErrText = Get-Content -Path $backendTunnelErr -Raw -ErrorAction SilentlyContinue
    }

    if ($backendErrText -match 'lookup\s+api\.trycloudflare\.com') {
        throw 'cloudflared failed DNS lookup for api.trycloudflare.com. Re-run with -UsePublicDns (Administrator) or manually set DNS to 1.1.1.1 and 8.8.8.8.'
    }

    throw
}

$ingestUrl = "$backendPublicUrl/api/telemetry/ingest"

Write-Stage 'Building prefilled client bundle for internet ingest URL...'
$bundleArgs = @{
    PresetIngestUrl = $ingestUrl
    PresetApiKey = $ApiKey
    PresetTopology = $Topology
    PresetSource = $Source
    PresetTargetNode = $TargetNode
}
if ($Force) {
    $bundleArgs.Force = $true
}
& $buildBundleScript @bundleArgs

$latestBundle = Get-ChildItem -Path (Join-Path $scriptRoot 'dist\OnyxSysmonClientBundle-*.zip') |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $latestBundle) {
    throw 'Bundle build failed: no bundle zip found in dist.'
}

$publishedBundle = Join-Path $PublishDir 'OnyxSysmonClientBundle-latest.zip'
Copy-Item -Path $latestBundle.FullName -Destination $publishedBundle -Force
Copy-Item -Path $downloadSetupScript -Destination (Join-Path $PublishDir 'download_and_setup_other_laptop.ps1') -Force
Copy-Item -Path $internetBootstrapScript -Destination (Join-Path $PublishDir 'internet_other_laptop_bootstrap.ps1') -Force

Write-Stage "Starting temporary file server on 127.0.0.1:$BundlePort"
Stop-PortListeners -Port $BundlePort
$bundleServerOut = Join-Path $logDir ("bundle_server.$runId.out.log")
$bundleServerErr = Join-Path $logDir ("bundle_server.$runId.err.log")
$bundleServerProc = Start-LoggedProcess `
    -FilePath $pythonExe `
    -ArgumentList @('-m', 'http.server', "$BundlePort", '--bind', '127.0.0.1', '--directory', $PublishDir) `
    -WorkingDirectory $PublishDir `
    -StdOutPath $bundleServerOut `
    -StdErrPath $bundleServerErr
Wait-HttpReachable -Url "http://127.0.0.1:$BundlePort/"

Write-Stage 'Starting tunnel for bundle download host...'
$bundleTunnelOut = Join-Path $logDir ("bundle_tunnel.$runId.out.log")
$bundleTunnelErr = Join-Path $logDir ("bundle_tunnel.$runId.err.log")
$bundleTunnelProc = Start-LoggedProcess `
    -FilePath $cloudflaredExe `
    -ArgumentList @('tunnel', '--url', "http://127.0.0.1:$BundlePort", '--no-autoupdate') `
    -WorkingDirectory $PublishDir `
    -StdOutPath $bundleTunnelOut `
    -StdErrPath $bundleTunnelErr
try {
    $bundlePublicUrl = Wait-TryCloudflareUrl -StdOutPath $bundleTunnelOut -StdErrPath $bundleTunnelErr
}
catch {
    $bundleErrText = ''
    if (Test-Path $bundleTunnelErr) {
        $bundleErrText = Get-Content -Path $bundleTunnelErr -Raw -ErrorAction SilentlyContinue
    }

    if ($bundleErrText -match 'lookup\s+api\.trycloudflare\.com') {
        throw 'cloudflared failed DNS lookup for api.trycloudflare.com. Re-run with -UsePublicDns (Administrator) or manually set DNS to 1.1.1.1 and 8.8.8.8.'
    }

    throw
}

$statePath = Join-Path $PublishDir 'internet_access_state.json'
$state = [ordered]@{
    created_at = (Get-Date).ToString('o')
    backend_public_url = $backendPublicUrl
    bundle_public_url = $bundlePublicUrl
    ingest_url = $ingestUrl
    api_key = $ApiKey
    backend_pid = $backendProc.Id
    backend_tunnel_pid = $backendTunnelProc.Id
    bundle_server_pid = $bundleServerProc.Id
    bundle_tunnel_pid = $bundleTunnelProc.Id
    bundle_file = $publishedBundle
    logs = [ordered]@{
        backend_out = $backendStdOut
        backend_err = $backendStdErr
        backend_tunnel_out = $backendTunnelOut
        backend_tunnel_err = $backendTunnelErr
        bundle_server_out = $bundleServerOut
        bundle_server_err = $bundleServerErr
        bundle_tunnel_out = $bundleTunnelOut
        bundle_tunnel_err = $bundleTunnelErr
    }
}
$state | ConvertTo-Json -Depth 6 | Set-Content -Path $statePath -Encoding UTF8

$targetLaptopCommand1 = "iwr -UseBasicParsing '$bundlePublicUrl/internet_other_laptop_bootstrap.ps1' -OutFile `$env:TEMP\internet_other_laptop_bootstrap.ps1"
$targetLaptopCommand2 = "powershell -NoProfile -ExecutionPolicy Bypass -File `$env:TEMP\internet_other_laptop_bootstrap.ps1 -PublishBaseUrl '$bundlePublicUrl'"

$quickStartPath = Join-Path $PublishDir 'INTERNET_QUICKSTART.txt'
$quickStart = @"
Onyx Internet Access Ready

Backend URL (public): $backendPublicUrl
Backend docs: $backendPublicUrl/docs
Ingest URL: $ingestUrl
API Key: $ApiKey
Bundle host URL: $bundlePublicUrl

Run on each target laptop (Administrator PowerShell):
$targetLaptopCommand1
$targetLaptopCommand2

To stop these internet access processes later, run stop_internet_access.ps1.
"@
Set-Content -Path $quickStartPath -Value $quickStart -Encoding UTF8

$backendHost = ([Uri]$backendPublicUrl).Host
$bundleHost = ([Uri]$bundlePublicUrl).Host

try {
    Resolve-DnsName -Name $backendHost -ErrorAction Stop | Out-Null
}
catch {
    Write-Warning "Local DNS could not resolve $backendHost. If browser/tests fail, set DNS to 1.1.1.1 or 8.8.8.8 and flush DNS cache."
}

try {
    Resolve-DnsName -Name $bundleHost -ErrorAction Stop | Out-Null
}
catch {
    Write-Warning "Local DNS could not resolve $bundleHost. If target laptops fail download, set DNS to 1.1.1.1 or 8.8.8.8 there too."
}

Write-Host ''
Write-Host '========================================='
Write-Host 'Onyx Internet Access Ready'
Write-Host '========================================='
Write-Host "Backend URL   : $backendPublicUrl"
Write-Host "Backend Docs  : $backendPublicUrl/docs"
Write-Host "Ingest URL    : $ingestUrl"
Write-Host "API Key       : $ApiKey"
Write-Host "Bundle Host   : $bundlePublicUrl"
Write-Host ''
Write-Host 'Run on each target laptop (Admin PowerShell):'
Write-Host $targetLaptopCommand1
Write-Host $targetLaptopCommand2
Write-Host ''
Write-Host "State file    : $statePath"
Write-Host "Quickstart    : $quickStartPath"
Write-Host '========================================='
Write-Host ''
