# Setup Other Laptop For Onyx Telemetry

Use this on a different Windows laptop to connect it to your Onyx server.

## What It Does
- Copies the forwarder and Sysmon config into a stable install folder.
- Creates a Python virtual environment.
- Downloads and installs forwarder dependencies from `client_requirements.txt`.
- Writes `forwarder.env` with your server URL, topology, and source node metadata.
- Creates `run_forwarder.ps1`.
- Registers a startup scheduled task (SYSTEM account) so forwarding continues after reboot.
- Optionally installs or updates Sysmon.

## Files
- Script: `tools/sysmon/setup_other_laptop.ps1`
- Download+install script for target laptops: `tools/sysmon/download_and_setup_other_laptop.ps1`
- Internet-mode server setup script: `tools/sysmon/setup_internet_access.ps1`
- Internet-mode target bootstrap script: `tools/sysmon/internet_other_laptop_bootstrap.ps1`
- Internet-mode stop script: `tools/sysmon/stop_internet_access.ps1`
- LAN server prep + optional SMB share script: `tools/sysmon/prepare_and_share_bundle_lan.ps1`
- Python deps: `tools/sysmon/client_requirements.txt`
- Portable bundle builder: `tools/sysmon/build_client_bundle.ps1`
- Combined server+client helper: `tools/sysmon/combined_server_client_setup.ps1`
- Multi-laptop remote deploy helper: `tools/sysmon/deploy_bundle_to_laptops.ps1`
- One-click launcher: `tools/sysmon/one_click_setup.ps1`
- Double-click runner: `tools/sysmon/RUN_SETUP_AS_ADMIN.cmd`

## Fastest Two-Laptop Flow (Recommended)

### If You See `DNS_PROBE_FINISHED_NXDOMAIN`
- `YOUR-SERVER-DOMAIN` is a placeholder, not a real host.
- For same-WiFi/LAN setup, use local IP (example: `http://172.16.13.14:8020`).
- If you want internet access, set up a real domain or install cloudflared first.

### If You See `cloudflared is not recognized`
- Use `setup_internet_access.ps1` with `-InstallCloudflaredIfMissing`.
- It installs cloudflared (or downloads a local fallback binary), starts tunnels, and prints ready commands.

## Internet Access One-Command Setup (Laptop A)

Run on Laptop A:

```powershell
cd D:\dehradun\tools\sysmon
.\setup_internet_access.ps1 -InstallCloudflaredIfMissing -Force
```

What it does:
- Starts backend on localhost.
- Opens public tunnel URL for API via cloudflared.
- Builds prefilled client bundle using that public ingest URL.
- Hosts bundle and setup scripts on a second public tunnel URL.
- Prints commands for target laptops.

After it finishes, run the printed commands on each target laptop (Admin PowerShell).

Stop internet-mode processes later:

```powershell
cd D:\dehradun\tools\sysmon
.\stop_internet_access.ps1
```

### LAN One-Command Prep On Laptop A

```powershell
cd D:\dehradun\tools\sysmon
.\prepare_and_share_bundle_lan.ps1 -CreateSmbShare -Force
```

This script:
- Starts backend on `0.0.0.0:8020`.
- Builds a prefilled bundle with local LAN URL.
- Optionally shares latest bundle at `\\<LaptopAName>\OnyxBundle\OnyxSysmonClientBundle-latest.zip`.
- Copies target setup script to `\\<LaptopAName>\OnyxBundle\download_and_setup_other_laptop.ps1`.

### Laptop A (Server Laptop)

Run this once to create a prefilled bundle and (optionally) start backend:

```powershell
cd D:\dehradun\tools\sysmon
.\combined_server_client_setup.ps1 `
  -Role server `
  -PublicServerBaseUrl "https://YOUR-SERVER-DOMAIN" `
  -ApiKey "YOUR_INGEST_API_KEY" `
  -Topology "enterprise_20n" `
  -Source "sysmon_forwarder" `
  -TargetNode "node_05_app" `
  -StartBackend `
  -Force
```

What this does on Laptop A:
- Exports `ONYX_TELEMETRY_INGEST_API_KEY` in current shell.
- Starts backend on `0.0.0.0:8020` when `-StartBackend` is passed.
- Builds a prefilled zip bundle in `tools/sysmon/dist`.

### Laptop B/C/D... (Each Target Laptop)

1) Copy the generated zip from Laptop A.
2) Extract the zip.
3) Right-click `RUN_SETUP_AS_ADMIN.cmd` and choose **Run as administrator**.

Alternative command-only flow (Admin PowerShell in extracted folder):

```powershell
cd .\OnyxSysmonClient
.\combined_server_client_setup.ps1 -Role client
```

What this does on each target laptop:
- Installs/updates Python dependencies.
- Writes `forwarder.env` from prefilled `installer_defaults.json`.
- Registers startup task so forwarding auto-starts after reboot.

## Roll Out To Many Laptops From Laptop A (SMB + Remote Task)

Run from Laptop A after creating the bundle:

```powershell
cd D:\dehradun\tools\sysmon
.\deploy_bundle_to_laptops.ps1 `
  -ComputerName LAPTOP-B,LAPTOP-C,LAPTOP-D `
  -Force
```

If remote admin credentials are required:

```powershell
cd D:\dehradun\tools\sysmon
$cred = Get-Credential
.\deploy_bundle_to_laptops.ps1 `
  -ComputerName LAPTOP-B,LAPTOP-C,LAPTOP-D `
  -Credential $cred `
  -Force
```

What it does:
- Copies latest bundle zip to `C:\ProgramData\Onyx\RemoteDeploy` on each target laptop.
- Pushes a temporary bootstrap script.
- Triggers remote install via a temporary scheduled task (SYSTEM, highest privileges).
- Reports success/failure per laptop.

Troubleshooting prerequisites:
- Admin share access (`\\TARGET\C$`) must be reachable.
- Remote Task Scheduler RPC must be allowed by firewall.
- Credentials must have local admin rights on target laptops.

## Run Directly On Each Target Laptop (Download + Install)

Use this if you want to run one script manually on each laptop.

```powershell
# Run in Administrator PowerShell on target laptop
powershell -NoProfile -ExecutionPolicy Bypass -File .\download_and_setup_other_laptop.ps1 `
  -BundleSource "\\LAPTOP-A\Shared\OnyxSysmonClientBundle-YYYYMMDD-HHMMSS.zip"
```

You can also use an HTTPS URL for `-BundleSource`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\download_and_setup_other_laptop.ps1 `
  -BundleSource "https://YOUR-DOMAIN/downloads/OnyxSysmonClientBundle-latest.zip"
```

Optional overrides (if you want to force values on target):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\download_and_setup_other_laptop.ps1 `
  -BundleSource "https://YOUR-DOMAIN/downloads/OnyxSysmonClientBundle-latest.zip" `
  -IngestUrl "https://YOUR-DOMAIN/api/telemetry/ingest" `
  -ApiKey "YOUR_INGEST_API_KEY" `
  -Topology "enterprise_20n" `
  -SourceNode $env:COMPUTERNAME
```

## Create Portable Zip (From Server Laptop)

```powershell
cd D:\dehradun\tools\sysmon
.\build_client_bundle.ps1
```

### Create Pre-Filled Bundle (No Parameter Typing On Target Laptop)

```powershell
cd D:\dehradun\tools\sysmon
.\build_client_bundle.ps1 `
  -PresetIngestUrl "https://YOUR-SERVER-DOMAIN/api/telemetry/ingest" `
  -PresetApiKey "YOUR_INGEST_API_KEY" `
  -PresetTopology "enterprise_20n" `
  -PresetSource "sysmon_forwarder"
```

Generated zip:
- `tools/sysmon/dist/OnyxSysmonClientBundle-YYYYMMDD-HHMMSS.zip`

Copy this zip to any target laptop, extract it, and run `RUN_SETUP_AS_ADMIN.cmd`.

## One-Click Target Laptop Setup (No Parameters)
- Extract bundle
- Open `installer_defaults.json` and verify values if needed
- Right-click `RUN_SETUP_AS_ADMIN.cmd` and choose **Run as administrator**
- Wait for completion message

## Run (Administrator PowerShell)

```powershell
cd D:\dehradun\tools\sysmon
.\setup_other_laptop.ps1 `
  -IngestUrl "https://YOUR-SERVER-DOMAIN/api/telemetry/ingest" `
  -ApiKey "YOUR_INGEST_API_KEY" `
  -Topology "enterprise_20n" `
  -Source "sysmon_forwarder" `
  -SourceNode $env:COMPUTERNAME `
  -TargetNode "node_05_app" `
  -InstallPythonIfMissing `
  -InstallSysmon `
  -StartTask
```

## Notes
- If you do not want a startup task, add `-SkipTaskRegistration`.
- If Python/venv already exists and you only want to update config, use `-SkipDependencyInstall`.
- To map destination IPs to topology nodes, edit:
  - `%ProgramData%\\Onyx\\SysmonForwarder\\ip_to_node_map.json`

## Quick Check
- On server laptop:
  - `GET /api/telemetry/status?topology=enterprise_20n`
- In Onyx Analysis page:
  - use `Telemetry Status` and run `Data Source = Telemetry`.
