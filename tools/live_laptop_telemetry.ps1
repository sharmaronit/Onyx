param(
    [string]$IngestUrl = 'http://127.0.0.1:8020/api/telemetry/ingest',
    [string]$ApiKey = '',
    [string]$Topology = 'enterprise_20n',
    [ValidateSet('pure', 'enriched')]
    [string]$Mode = 'pure',
    [string]$Source = '',
    [string]$TargetNode = 'node_05_app',
    [int]$MaxConnections = 20,
    [int]$MaxProcesses = 20
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($Source)) {
    $Source = if ($Mode -eq 'enriched') { 'laptop_rich_telemetry' } else { 'laptop_live_telemetry' }
}

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = [string]$env:ONYX_TELEMETRY_INGEST_API_KEY
}

function New-LiveTelemetryEvent {
    param(
        [string]$EventId,
        [string]$EventType,
        [hashtable]$Raw,
        [double]$CvssScore,
        [double]$Confidence,
        [string]$Target,
        [bool]$Blocked = $false,
        [bool]$ReachedCritical = $false,
        [string]$CveId = '',
        [string]$Timestamp = ''
    )

    if ([string]::IsNullOrWhiteSpace($Timestamp)) {
        $Timestamp = (Get-Date).ToUniversalTime().ToString('o')
    }

    if ([string]::IsNullOrWhiteSpace($CveId)) {
        $CveId = "CVE-LIVE-$($EventType.ToUpper())"
    }

    [pscustomobject]@{
        event_id = $EventId
        timestamp = $Timestamp
        source_node = $env:COMPUTERNAME
        target_node = $Target
        event_type = $EventType
        cve_id = $CveId
        cvss_score = $CvssScore
        confidence = $Confidence
        blocked = $Blocked
        reached_critical = $ReachedCritical
        raw = $Raw
    }
}

function Add-EnrichedSeedEvents {
    param(
        [System.Collections.Generic.List[object]]$Events,
        [datetime]$BaseTime,
        [string]$HostNode
    )

    $seedRows = @(
        @{ id = 'session-1'; offset = 0; src = $HostNode; dst = 'node_03_workstation'; etype = 'credential_access'; cve = 'CVE-2024-10001'; cvss = 7.1; conf = 0.83; blocked = $false; critical = $false; stage = 'initial' },
        @{ id = 'session-1'; offset = 2; src = 'node_03_workstation'; dst = 'node_05_app'; etype = 'lateral_movement'; cve = 'CVE-2024-10002'; cvss = 8.2; conf = 0.84; blocked = $false; critical = $false; stage = 'pivot' },
        @{ id = 'session-1'; offset = 4; src = 'node_05_app'; dst = 'node_09_db'; etype = 'privilege_escalation'; cve = 'CVE-2024-10003'; cvss = 9.1; conf = 0.87; blocked = $false; critical = $true; stage = 'critical' },

        @{ id = 'session-2'; offset = 1; src = $HostNode; dst = 'node_04_mail_server'; etype = 'phishing_execution'; cve = 'CVE-2023-40011'; cvss = 6.4; conf = 0.74; blocked = $false; critical = $false; stage = 'entry' },
        @{ id = 'session-2'; offset = 3; src = 'node_04_mail_server'; dst = 'node_05_app'; etype = 'lateral_movement'; cve = 'CVE-2023-40012'; cvss = 7.3; conf = 0.76; blocked = $true; critical = $false; stage = 'blocked' },

        @{ id = 'session-3'; offset = 2; src = $HostNode; dst = 'node_06_vpn_gateway'; etype = 'vpn_abuse'; cve = 'CVE-2022-81001'; cvss = 7.8; conf = 0.79; blocked = $false; critical = $false; stage = 'entry' },
        @{ id = 'session-3'; offset = 5; src = 'node_06_vpn_gateway'; dst = 'node_07_internal_fw'; etype = 'firewall_bypass'; cve = 'CVE-2022-81002'; cvss = 8.0; conf = 0.81; blocked = $false; critical = $false; stage = 'pivot' },
        @{ id = 'session-3'; offset = 8; src = 'node_07_internal_fw'; dst = 'node_09_db'; etype = 'db_access'; cve = 'CVE-2022-81003'; cvss = 9.0; conf = 0.85; blocked = $false; critical = $true; stage = 'critical' },

        @{ id = 'session-4'; offset = 1; src = $HostNode; dst = 'node_08_file_server'; etype = 'file_drop'; cve = 'CVE-2021-70010'; cvss = 5.8; conf = 0.68; blocked = $false; critical = $false; stage = 'entry' },
        @{ id = 'session-4'; offset = 4; src = 'node_08_file_server'; dst = 'node_10_backup'; etype = 'backup_tamper'; cve = 'CVE-2021-70011'; cvss = 6.6; conf = 0.72; blocked = $true; critical = $false; stage = 'blocked' }
    )

    foreach ($row in $seedRows) {
        $eventParams = @{
            EventId = $row.id
            EventType = $row.etype
            CvssScore = $row.cvss
            Confidence = $row.conf
            Target = $row.dst
            Blocked = $row.blocked
            ReachedCritical = $row.critical
            CveId = $row.cve
            Timestamp = $BaseTime.AddSeconds($row.offset).ToString('o')
            Raw = @{ stage = $row.stage; source_node = $row.src; target_node = $row.dst }
        }

        $Events.Add((New-LiveTelemetryEvent @eventParams))
    }
}

$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$events = New-Object 'System.Collections.Generic.List[object]'
$hostNode = if ([string]::IsNullOrWhiteSpace($env:COMPUTERNAME)) { 'unknown_laptop' } else { $env:COMPUTERNAME }

if ($Mode -eq 'enriched') {
    Add-EnrichedSeedEvents -Events $events -BaseTime (Get-Date).ToUniversalTime() -HostNode $hostNode
}

$targetRotation = @('node_05_app', 'node_08_file_server', 'node_10_backup', 'node_07_internal_fw', 'node_09_db')

$connections = Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue | Select-Object -First $MaxConnections
$connIndex = 0
foreach ($connection in $connections) {
    $connIndex++
    $target = if ($Mode -eq 'enriched') { $targetRotation[$connIndex % $targetRotation.Count] } else { $TargetNode }
    $critical = ($Mode -eq 'enriched' -and $target -eq 'node_09_db' -and ($connIndex % 3 -eq 0))

    $eventParams = @{
        EventId = "live-net-$stamp-$connIndex"
        EventType = 'network_connect_live'
        CvssScore = 6.8
        Confidence = 0.72
        Target = $target
        Blocked = $false
        ReachedCritical = $critical
        Raw = @{
            local_ip = $connection.LocalAddress
            local_port = $connection.LocalPort
            remote_ip = $connection.RemoteAddress
            remote_port = $connection.RemotePort
            state = [string]$connection.State
        }
    }

    $events.Add((New-LiveTelemetryEvent @eventParams))
}

$processes = Get-Process | Sort-Object -Property CPU -Descending | Select-Object -First $MaxProcesses
$procIndex = 0
foreach ($process in $processes) {
    $procIndex++
    $target = if ($Mode -eq 'enriched') { $targetRotation[$procIndex % $targetRotation.Count] } else { $TargetNode }
    $blocked = ($Mode -eq 'enriched' -and ($process.ProcessName -match 'defender|msmpeng|security|av|sentinel'))

    $eventParams = @{
        EventId = "live-proc-$stamp-$procIndex"
        EventType = 'process_creation_live'
        CvssScore = 5.9
        Confidence = 0.67
        Target = $target
        Blocked = $blocked
        ReachedCritical = $false
        Raw = @{
            process_name = $process.ProcessName
            pid = $process.Id
            cpu = $process.CPU
            working_set_mb = [math]::Round($process.WorkingSet64 / 1MB, 2)
        }
    }

    $events.Add((New-LiveTelemetryEvent @eventParams))
}

if ($events.Count -eq 0) {
    throw 'No live laptop telemetry events could be collected.'
}

$payload = @{
    source = $Source
    topology = $Topology
    events = $events.ToArray()
} | ConvertTo-Json -Depth 8

$requestArgs = @{
    Method = 'Post'
    Uri = $IngestUrl
    ContentType = 'application/json'
    Body = $payload
}

if (-not [string]::IsNullOrWhiteSpace($ApiKey)) {
    $requestArgs.Headers = @{ 'X-API-Key' = $ApiKey }
}

$response = Invoke-RestMethod @requestArgs

$ingestUri = [System.Uri]$IngestUrl
$statusUri = '{0}://{1}/api/telemetry/status?topology={2}' -f $ingestUri.Scheme, $ingestUri.Authority, [System.Uri]::EscapeDataString($Topology)
$status = Invoke-RestMethod -Method Get -Uri $statusUri

[pscustomobject]@{
    mode = $Mode
    source = $Source
    ingested = $response.ingested
    event_count = $status.event_count
    blocked_events = $status.blocked_events
    critical_reaches = $status.critical_reaches
    updated_at = $status.updated_at
} | ConvertTo-Json -Depth 6
