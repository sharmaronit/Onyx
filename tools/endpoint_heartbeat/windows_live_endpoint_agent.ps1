<#
.SYNOPSIS
  Consent-based Onyx live endpoint agent for a Windows laptop.
.DESCRIPTION
  Sends a heartbeat and Microsoft Defender detections to Onyx. Use
  -EmitSimulatedDetection only for a harmless, clearly labelled rehearsal event.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ApiUrl,
    [Parameter(Mandatory = $true)][string]$ApiKey,
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9_.-]+$')][string]$EndpointId,
    [string]$Topology = 'enterprise_20n',
    [ValidateRange(2, 60)][int]$PollSeconds = 5,
    [switch]$EmitSimulatedDetection,
    [string]$BookmarkPath = "$env:ProgramData\Onyx\defender-bookmark.json"
)

$ErrorActionPreference = 'Continue'
$baseUrl = $ApiUrl.TrimEnd('/')
$headers = @{ Authorization = "Bearer $ApiKey" }
$directory = Split-Path -Parent $BookmarkPath
New-Item -ItemType Directory -Force -Path $directory | Out-Null

function Send-OnyxJson([string]$Path, [object]$Payload) {
    Invoke-RestMethod -Method Post -Uri "$baseUrl$Path" -Headers $headers -ContentType 'application/json' -Body ($Payload | ConvertTo-Json -Depth 8 -Compress) | Out-Null
}

function Send-Heartbeat {
    $ip = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254*' } | Select-Object -First 1 -ExpandProperty IPAddress
    $observed = @(Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue | Select-Object -First 20 | ForEach-Object { @{ target = "$($_.RemoteAddress):$($_.RemotePort)"; type = 'observed_connection'; confidence = 0.8 } })
    Send-OnyxJson '/api/endpoints/heartbeat' @{
        endpoint_id=$EndpointId; hostname=$env:COMPUTERNAME; ip_address=$ip; topology=$Topology
        agent_version='windows-live-endpoint-1.0.0'; platform="Windows $([Environment]::OSVersion.Version)"; quarantined=$false
        metadata=@{ telemetry_mode='defender_polling'; response_capable=$false; observed_connections=$observed }
    }
}

function Send-Detection([string]$EventId, [string]$ThreatName, [string]$Path, [bool]$Simulated) {
    $raw = @{ threat_name=$ThreatName; path=$Path; defender_detection=(-not $Simulated); simulated_detection=$Simulated; provenance=if ($Simulated) {'safe_local_simulator'} else {'microsoft_defender'} }
    Send-OnyxJson '/api/telemetry/ingest' @{ source=$raw.provenance; topology=$Topology; events=@(@{
        event_id=$EventId; timestamp=(Get-Date).ToUniversalTime().ToString('o'); source_node=$EndpointId; target_node='onyx_control_server'
        event_type='malware_detected'; confidence=if ($Simulated) {1.0} else {0.95}; blocked=$false; reached_critical=$false; raw=$raw
    }) }
}

if ($EmitSimulatedDetection) {
    Send-Heartbeat
    Send-Detection "safe-sim-$([guid]::NewGuid().ToString('N'))" 'Onyx Safe Demo Detection' 'No file created; operator-triggered rehearsal' $true
    Write-Host 'Safe simulated detection sent. No malware or test file was created.' -ForegroundColor Yellow
    exit 0
}

$lastRecordId = 0
if (Test-Path $BookmarkPath) { try { $lastRecordId = [int]((Get-Content $BookmarkPath -Raw | ConvertFrom-Json).record_id) } catch {} }
Write-Host "Onyx live endpoint agent running as $EndpointId. Press Ctrl+C to stop."
while ($true) {
    try {
        Send-Heartbeat
        $events = Get-WinEvent -FilterHashtable @{ LogName='Microsoft-Windows-Windows Defender/Operational'; Id=1116 } -MaxEvents 20 -ErrorAction SilentlyContinue | Where-Object { $_.RecordId -gt $lastRecordId } | Sort-Object RecordId
        foreach ($event in $events) {
            Send-Detection "defender-$($event.RecordId)" 'Microsoft Defender detection' $event.Message $false
            $lastRecordId = $event.RecordId
            @{ record_id=$lastRecordId } | ConvertTo-Json | Set-Content -Encoding UTF8 $BookmarkPath
        }
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Connected to Onyx" -ForegroundColor Green
    } catch { Write-Warning "Endpoint report failed: $($_.Exception.Message)" }
    Start-Sleep -Seconds $PollSeconds
}
