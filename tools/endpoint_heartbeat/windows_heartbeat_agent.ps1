<#
.SYNOPSIS
    Onyx Windows heartbeat-only endpoint agent.
.DESCRIPTION
    Registers a Windows laptop as a live endpoint without collecting telemetry
    or accepting containment commands. Keep this window open during a demo.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ApiUrl,

    [Parameter(Mandatory = $true)]
    [string]$ApiKey,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9_.-]+$')]
    [string]$EndpointId,

    [string]$Topology = 'enterprise_20n',
    [ValidateRange(2, 60)]
    [int]$PollSeconds = 5
)

$ErrorActionPreference = 'Continue'
$endpointUrl = "$($ApiUrl.TrimEnd('/'))/api/endpoints/heartbeat"
$ipAddress = (
    Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254*' } |
    Select-Object -First 1 -ExpandProperty IPAddress
)
$payload = @{
    endpoint_id = $EndpointId
    hostname = $env:COMPUTERNAME
    ip_address = $ipAddress
    topology = $Topology
    agent_version = 'windows-heartbeat-1.0.0'
    platform = "Windows $([Environment]::OSVersion.Version)"
    quarantined = $false
    metadata = @{
        telemetry_mode = 'heartbeat_only'
        response_capable = $false
    }
}

Write-Host "Onyx heartbeat agent running for $EndpointId. Press Ctrl+C to stop."
while ($true) {
    try {
        Invoke-RestMethod -Method Post -Uri $endpointUrl -Headers @{ Authorization = "Bearer $ApiKey" } -ContentType 'application/json' -Body ($payload | ConvertTo-Json -Compress) | Out-Null
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Connected to Onyx" -ForegroundColor Green
    }
    catch {
        Write-Warning "Heartbeat failed: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds $PollSeconds
}
