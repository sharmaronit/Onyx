# Real Data Runbook (Authorized Sources Only)

## Pilot Source Selection
- Selected pilot source: scanner_export
- Supported pilot topology: enterprise_20n
- Rationale: fastest normalization path with CVE-rich data.

## Legal Boundary
- Use only systems you own or have explicit written authorization to test.
- Do not scan or probe public infrastructure without permission.
- Mark all non-telemetry outputs as estimated or hybrid in demos.

## Telemetry Ingestion API

## Onboard Another Laptop (Windows)
- Use `tools/sysmon/combined_server_client_setup.ps1` for end-to-end server+bundle automation.
- For same-LAN setup without domain, use `tools/sysmon/prepare_and_share_bundle_lan.ps1`.
- For internet-access setup without a custom domain, use `tools/sysmon/setup_internet_access.ps1`.
- Use `tools/sysmon/setup_other_laptop.ps1` to install dependencies, configure forwarder env, and register startup forwarding.
- Use `tools/sysmon/download_and_setup_other_laptop.ps1` to download/copy bundle and install in one step on target laptops.
- Use `tools/sysmon/internet_other_laptop_bootstrap.ps1` on target laptops when bundle is hosted on internet tunnel URL.
- Build a portable zip for distribution using `tools/sysmon/build_client_bundle.ps1`.
- For multi-laptop rollout from one command, use `tools/sysmon/deploy_bundle_to_laptops.ps1`.
- For the easiest target-laptop flow, run `RUN_SETUP_AS_ADMIN.cmd` from the extracted bundle.
- Quick reference: `tools/sysmon/SETUP_OTHER_LAPTOP.md`
- Run in Administrator PowerShell on the target laptop.

### 1) Load sample telemetry data
POST /api/telemetry/load-sample?topology=enterprise_20n

### 2) Ingest custom telemetry events
POST /api/telemetry/ingest
Content-Type: application/json

{
  "source": "scanner_export",
  "topology": "enterprise_20n",
  "events": [
    {
      "event_id": "evt-2001",
      "timestamp": "2026-04-05T02:11:00Z",
      "source_node": "node_03_workstation",
      "target_node": "node_05_app",
      "event_type": "lateral_movement",
      "cve_id": "CVE-2024-12345",
      "cvss_score": 8.2,
      "confidence": 0.84,
      "blocked": false,
      "reached_critical": false
    }
  ]
}

### 3) Check telemetry status
GET /api/telemetry/status?topology=enterprise_20n

### 4) Run telemetry-backed analysis
POST /api/simulate
{
  "topology": "enterprise_20n",
  "n_episodes": 700,
  "data_source": "telemetry",
  "telemetry_weight": 0.6
}

### 5) Run telemetry-backed patch optimization
POST /api/patch-optimize
{
  "topology": "enterprise_20n",
  "n_baseline": 300,
  "n_eval_per_patch": 80,
  "data_source": "telemetry",
  "telemetry_weight": 0.6
}

## Expected Provenance Labels
- data_source: telemetry
- confidence: measured
- data_source_note: telemetry_local_ingest (for local ingest mode)
