param(
    [string]$ApiBaseUrl = 'http://127.0.0.1:8020',
    [string]$Topology = 'enterprise_20n',
    [ValidateSet('pure', 'enriched')]
    [string]$Mode = 'enriched',
    [int]$Episodes = 1000,
    [double]$TelemetryWeight = 0.6,
    [int]$NBaseline = 200,
    [int]$NEvalPerPatch = 50,
    [int]$TopPatchCount = 3
)

$ErrorActionPreference = 'Stop'

function Convert-ToJsonObjectFromText {
    param([string]$Text)

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $null
    }

    try {
        return ($Text | ConvertFrom-Json -ErrorAction Stop)
    } catch {
    }

    $lines = $Text -split "`r?`n" | Where-Object { $_.Trim().Length -gt 0 }
    for ($i = $lines.Count - 1; $i -ge 0; $i--) {
        $candidate = ($lines[$i..($lines.Count - 1)] -join "`n").Trim()
        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }
        try {
            return ($candidate | ConvertFrom-Json -ErrorAction Stop)
        } catch {
        }
    }

    return $null
}

function Get-PatchImpact {
    param($Row)

    if ($null -ne $Row.simulation_impact) {
        return [double]$Row.simulation_impact
    }
    if ($null -ne $Row.impact) {
        return [double]$Row.impact
    }
    return 0.0
}

$apiRoot = $ApiBaseUrl.TrimEnd('/')
$ingestScript = Join-Path $PSScriptRoot 'live_laptop_telemetry.ps1'
if (-not (Test-Path $ingestScript)) {
    throw "Required script not found: $ingestScript"
}

$ingestResultRaw = & $ingestScript -IngestUrl "$apiRoot/api/telemetry/ingest" -Topology $Topology -Mode $Mode
$ingestText = ($ingestResultRaw | Out-String).Trim()
$ingestResult = Convert-ToJsonObjectFromText -Text $ingestText
if (-not $ingestResult) {
    throw "Unable to parse live telemetry ingest output as JSON."
}

$simulateBody = @{
    topology = $Topology
    n_episodes = $Episodes
    data_source = 'telemetry'
    telemetry_weight = $TelemetryWeight
} | ConvertTo-Json

$simulateResult = Invoke-RestMethod -Method Post -Uri "$apiRoot/api/simulate" -ContentType 'application/json' -Body $simulateBody

$patchBody = @{
    topology = $Topology
    n_baseline = $NBaseline
    n_eval_per_patch = $NEvalPerPatch
    data_source = 'telemetry'
    telemetry_weight = $TelemetryWeight
} | ConvertTo-Json

$patchResult = Invoke-RestMethod -Method Post -Uri "$apiRoot/api/patch-optimize" -ContentType 'application/json' -Body $patchBody
$statusResult = Invoke-RestMethod -Method Get -Uri "$apiRoot/api/telemetry/status?topology=$([System.Uri]::EscapeDataString($Topology))"

$topPath = 'n/a'
if ($simulateResult.top_paths -and $simulateResult.top_paths.Count -gt 0) {
    $topPath = [string]$simulateResult.top_paths[0].path
}

$patchRows = @($patchResult.results)
$topPatches = @($patchRows | Sort-Object -Property @{ Expression = { Get-PatchImpact $_ } } -Descending | Select-Object -First $TopPatchCount)
$successRate = if ($null -ne $simulateResult.success_rate) { [double]$simulateResult.success_rate } else { 0.0 }
$pathCount = @($simulateResult.top_paths).Count
$patchCount = @($patchRows).Count

$topPatchObjects = @(
    foreach ($row in $topPatches) {
        $nodeId = if ($null -ne $row.node_id -and "$($row.node_id)".Trim().Length -gt 0) {
            [string]$row.node_id
        } elseif ($null -ne $row.patch_id -and "$($row.patch_id)".Trim().Length -gt 0) {
            [string]$row.patch_id
        } else {
            'n/a'
        }

        $cveId = if ($null -ne $row.cve_id -and "$($row.cve_id)".Trim().Length -gt 0) {
            [string]$row.cve_id
        } else {
            'n/a'
        }

        [ordered]@{
            node_id = $nodeId
            cve_id = $cveId
            impact = [math]::Round((Get-PatchImpact $row) * 100.0, 2)
        }
    }
)

$summary = [ordered]@{
    timestamp_utc = (Get-Date).ToUniversalTime().ToString('o')
    api_base_url = $apiRoot
    topology = $Topology
    mode = $Mode
    ingest = [ordered]@{
        source = $ingestResult.source
        ingested = $ingestResult.ingested
        event_count = $statusResult.event_count
        blocked_events = $statusResult.blocked_events
        critical_reaches = $statusResult.critical_reaches
        updated_at = $statusResult.updated_at
    }
    simulation = [ordered]@{
        episodes = $Episodes
        success_rate = [math]::Round($successRate, 4)
        path_count = $pathCount
        top_path = $topPath
    }
    patch_optimization = [ordered]@{
        n_baseline = $NBaseline
        n_eval_per_patch = $NEvalPerPatch
        recommendation_count = $patchCount
    }
    top_patches = $topPatchObjects
}

Write-Host ''
Write-Host '========================================='
Write-Host 'Onyx Live Demo Summary'
Write-Host '========================================='
Write-Host "Mode: $Mode"
Write-Host "Topology: $Topology"
Write-Host "Telemetry: events=$($statusResult.event_count), blocked=$($statusResult.blocked_events), critical=$($statusResult.critical_reaches)"
Write-Host "Simulation: success_rate=$([math]::Round($successRate * 100.0, 2))%, paths=$pathCount"
Write-Host "Top Path: $topPath"
Write-Host "Patch Recommendations: $patchCount"

if ($topPatchObjects.Count -gt 0) {
    Write-Host 'Top Patch Actions:'
    foreach ($item in $topPatchObjects) {
        Write-Host "  - $($item.node_id) | $($item.cve_id) | impact=$($item.impact)%"
    }
}

Write-Host '========================================='
Write-Host ''

$summary | ConvertTo-Json -Depth 8
