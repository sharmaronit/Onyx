# Onyx Server and Client Laptop Runbook

This runbook starts Onyx on one **server laptop** and connects Windows or macOS client laptops on the same trusted LAN or hotspot.

The current web stack uses:

| Service | Address | Purpose |
| --- | --- | --- |
| FastAPI API | `http://SERVER_IP:8020` | Endpoints, telemetry, simulation, patch ranking, reports |
| React dashboard | `http://SERVER_IP:5183` | Analyst interface |
| API health check | `http://SERVER_IP:8020/api/health` | Confirms the backend is online |

Do not use the older `8020` examples found in legacy files. The active React development configuration proxies API traffic to port **8020**.

---

## 1. Choose the laptop roles

| Role | Required software | What it does |
| --- | --- | --- |
| Server laptop | Windows, Node.js 18+, Python runtime, Onyx repository | Runs the API and dashboard |
| Windows client laptop | Windows PowerShell 5.1+ | Sends heartbeats and optional Defender/telemetry evidence |
| macOS client laptop | macOS with Terminal and `curl` | Sends heartbeats |
| Optional Sysmon client | Windows local administrator rights | Sends persistent Sysmon telemetry |

All devices must join the same trusted Wi-Fi, Ethernet LAN, or hotspot. For a quick live demonstration, make the server laptop the Wi-Fi hotspot and connect the other laptops to it.

---

## 2. One-time server preparation

Open **PowerShell** on the server laptop.

```powershell
cd D:\Onyx
```

### Verify the required tools

```powershell
node --version
npm --version
.\.runtime-python310\python.exe --version
```

If PowerShell blocks scripts, allow locally created scripts for the current Windows user:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Install frontend dependencies once

```powershell
cd D:\Onyx\web
npm.cmd install
```

### Configure API keys

Client heartbeats and telemetry require `ONYX_TELEMETRY_INGEST_API_KEY`. Endpoint response actions and cost-model changes require `ONYX_RESPONSE_API_KEY`.

Create new keys for a new deployment. Keep them private and never paste them into slides, source code, or public chat.

```powershell
cd D:\Onyx

$telemetryKey = -join ((48..57) + (97..102) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
$responseKey = -join ((48..57) + (97..102) | Get-Random -Count 48 | ForEach-Object { [char]$_ })

@(
  "set ONYX_TELEMETRY_INGEST_API_KEY=$telemetryKey"
  "set ONYX_RESPONSE_API_KEY=$responseKey"
) | Set-Content -Encoding ascii .onyx-secrets.cmd
```

Load those keys into the **current PowerShell window** before starting the backend:

```powershell
Get-Content .\.onyx-secrets.cmd | ForEach-Object {
  if ($_ -match '^set\s+([^=]+)=(.+)$') {
    [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
  }
}
```

Confirm only that the variables exist. Do not print the values.

```powershell
[bool]$env:ONYX_TELEMETRY_INGEST_API_KEY
[bool]$env:ONYX_RESPONSE_API_KEY
```

Expected result: two lines showing `True`.

> `.onyx-secrets.cmd` contains secrets. Keep it local, add it to `.gitignore`, and securely share only the telemetry key with approved client laptops.

---

## 3. Find the server laptop IP address

Run this on the server laptop after all laptops join the same network:

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object {
    $_.IPAddress -notlike '127.*' -and
    $_.IPAddress -notlike '169.254.*' -and
    $_.PrefixOrigin -ne 'WellKnown'
  } |
  Select-Object IPAddress, InterfaceAlias
```

Choose the address of the active Wi-Fi, Ethernet, or hotspot interface, for example `192.168.137.1`. In this runbook, replace `SERVER_IP` with that address.

---

## 4. Start Onyx on the server laptop

Keep the PowerShell window where you loaded the API keys open.

### Terminal 1: FastAPI backend

```powershell
cd D:\Onyx\web
$env:BACKEND_PYTHON = 'D:\Onyx\.runtime-python310\python.exe'
npm.cmd run dev:backend
```

The API must report that Uvicorn is listening on `0.0.0.0:8020`.

### Terminal 2: React dashboard

Open a second PowerShell window:

```powershell
cd D:\Onyx\web
npm.cmd run dev:frontend -- --host 0.0.0.0
```

Open the dashboard locally at `http://localhost:5183`. Other laptops can open `http://SERVER_IP:5183`.

### Verify the backend

Run from the server laptop:

```powershell
Invoke-RestMethod http://127.0.0.1:8020/api/health
```

Then test from a client laptop browser or PowerShell:

```powershell
Invoke-RestMethod http://SERVER_IP:8020/api/health
```

Both checks should return a healthy response.

### Allow LAN access through Windows Firewall

Run these commands once in **Administrator PowerShell** on the server laptop. Restrict `RemoteAddress` to the trusted LAN range when possible.

```powershell
New-NetFirewallRule -DisplayName 'Onyx API 8020' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8020 -Profile Private
New-NetFirewallRule -DisplayName 'Onyx Dashboard 5183' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5183 -Profile Private
```

Do not expose these development ports directly to the public internet.

---

## 5. Fastest client connection: Windows heartbeat agent

Use this path when you need connected laptops to appear in the Reality-mode topology. It sends a heartbeat and observed network connections. It does not install software and does not execute endpoint response commands.

Copy this file from the server to each Windows client laptop:

```text
D:\Onyx\tools\endpoint_heartbeat\windows_heartbeat_agent.ps1
```

On each Windows client laptop, open PowerShell in the folder containing the file and run the following. Use a **unique** endpoint ID for every laptop.

```powershell
.\windows_heartbeat_agent.ps1 `
  -ApiUrl 'http://SERVER_IP:8020' `
  -ApiKey 'TELEMETRY_INGEST_API_KEY' `
  -EndpointId 'laptop-b' `
  -Topology 'enterprise_20n' `
  -PollSeconds 5
```

Keep this window open during the demonstration. Stop the agent with `Ctrl+C`.

Verify the client registered from the server laptop:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8020/api/endpoints?topology=enterprise_20n&mode=reality'
```

Open **Topology** in the dashboard and select **Reality** mode. The endpoint should appear as active within roughly 30 seconds.

---

## 6. Windows client with Defender detections

Use the live endpoint agent when you want heartbeats plus Microsoft Defender detection forwarding.

Copy this file to the Windows client:

```text
D:\Onyx\tools\endpoint_heartbeat\windows_live_endpoint_agent.ps1
```

Start it with a unique endpoint ID:

```powershell
.\windows_live_endpoint_agent.ps1 `
  -ApiUrl 'http://SERVER_IP:8020' `
  -ApiKey 'TELEMETRY_INGEST_API_KEY' `
  -EndpointId 'laptop-b' `
  -Topology 'enterprise_20n' `
  -PollSeconds 5
```

For a safe rehearsal event only, use the built-in simulated-detection switch. It does **not** create malware or a test file.

```powershell
.\windows_live_endpoint_agent.ps1 `
  -ApiUrl 'http://SERVER_IP:8020' `
  -ApiKey 'TELEMETRY_INGEST_API_KEY' `
  -EndpointId 'laptop-b' `
  -EmitSimulatedDetection
```

The telemetry event appears in the Reality-mode telemetry and incident views.

---

## 7. Windows client with live telemetry collection

Use `live_laptop_telemetry.ps1` to submit a bounded sample of established TCP connections and high-CPU processes. `pure` sends observed data only. `enriched` adds clearly synthetic rehearsal events, so reserve it for demos.

Copy this file to the client laptop:

```text
D:\Onyx\tools\live_laptop_telemetry.ps1
```

### Real observed telemetry

```powershell
.\live_laptop_telemetry.ps1 `
  -IngestUrl 'http://SERVER_IP:8020/api/telemetry/ingest' `
  -ApiKey 'TELEMETRY_INGEST_API_KEY' `
  -Topology 'enterprise_20n' `
  -Mode pure `
  -TargetNode 'node_05_app'
```

### Safe enriched demo telemetry

```powershell
.\live_laptop_telemetry.ps1 `
  -IngestUrl 'http://SERVER_IP:8020/api/telemetry/ingest' `
  -ApiKey 'TELEMETRY_INGEST_API_KEY' `
  -Topology 'enterprise_20n' `
  -Mode enriched `
  -TargetNode 'node_05_app'
```

Verify ingestion on the server:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8020/api/telemetry/status?topology=enterprise_20n'
```

---

## 8. macOS client heartbeat agent

Copy `tools/endpoint_heartbeat/macos_heartbeat_agent.sh` to the Mac. In Terminal:

```bash
chmod +x macos_heartbeat_agent.sh
export ONYX_API_URL='http://SERVER_IP:8020'
export ONYX_INGEST_API_KEY='TELEMETRY_INGEST_API_KEY'
export ONYX_ENDPOINT_ID='macbook-demo'
export ONYX_TOPOLOGY='enterprise_20n'
./macos_heartbeat_agent.sh
```

Keep the terminal open. Stop it with `Ctrl+C`.

---

## 9. Direct-connect bundles for a demo

The project can generate Windows and macOS heartbeat bundles prefilled with the current server IP and telemetry key.

On the server laptop, after creating `.onyx-secrets.cmd`, connect to the Wi-Fi/hotspot and run:

```powershell
cd D:\Onyx
.\tools\endpoint_heartbeat\rebuild_direct_connect_bundles.ps1
```

The output appears here:

```text
D:\Onyx\tools\endpoint_heartbeat\dist\
```

Transfer the appropriate ZIP file privately, extract it, and run its launcher.

> The generated Windows bundle uses one preset endpoint ID. For more than one Windows client, use the manual command in section 5 or edit the launcher so each laptop has a unique endpoint ID. Do not distribute a bundle outside the trusted demo network because it contains the telemetry key.

---

## 10. Persistent Sysmon forwarding (advanced)

Use the Sysmon path only when you need continuous Windows event forwarding after reboot. It needs Administrator rights on each client and is more suitable for a prepared lab than a quick presentation.

### Build a LAN client bundle on the server laptop

```powershell
cd D:\Onyx\tools\sysmon
.\build_client_bundle.ps1 `
  -PresetIngestUrl 'http://SERVER_IP:8020/api/telemetry/ingest' `
  -PresetApiKey 'TELEMETRY_INGEST_API_KEY' `
  -PresetTopology 'enterprise_20n' `
  -PresetSource 'sysmon_forwarder'
```

Transfer the created ZIP from `tools\sysmon\dist` to each Windows client.

### Install on each client laptop

1. Extract the ZIP.
2. Open `installer_defaults.json` and confirm the server address and topology.
3. Right-click `RUN_SETUP_AS_ADMIN.cmd` and choose **Run as administrator**.
4. Wait for the installation to finish. The installer creates a scheduled task for the forwarder.

Check telemetry on the server:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8020/api/telemetry/status?topology=enterprise_20n'
```

For configuration details, see `tools\sysmon\SETUP_OTHER_LAPTOP.md`.

---

## 11. How to run a complete multi-laptop demonstration

1. Connect all laptops to the same trusted network.
2. On the server laptop, load API keys and start the backend on port `8020`.
3. Start the React dashboard on port `5183`.
4. Confirm `http://SERVER_IP:8020/api/health` from a client laptop.
5. Start the heartbeat or live-endpoint agent on every client with a unique endpoint ID.
6. Open the dashboard on the server laptop at `http://localhost:5183` and switch to **Reality** mode.
7. Show newly connected endpoints in **Topology** and telemetry evidence in **Telemetry**.
8. Use the simulation page to run the offline world-model scenario. Real endpoint telemetry remains evidence and does not become simulated attacker input.
9. Review the ranked actions in **Patches**. Enter the response API key only when saving the cost model or sending an authorized response action.

---

## 12. Troubleshooting

### Client cannot reach the API

On the client:

```powershell
Test-NetConnection SERVER_IP -Port 8020
```

- Confirm the server backend is running with host `0.0.0.0`.
- Confirm the server laptop and client are on the same network.
- Confirm the Windows Firewall rule for port `8020` is enabled.
- Confirm you used the LAN IP, not `127.0.0.1` or `localhost`.

### Dashboard is not reachable from another laptop

- Start Vite with `--host 0.0.0.0` as shown in section 4.
- Confirm TCP port `5183` is allowed through the Private firewall profile.
- The dashboard proxy only works when the API is running locally on the server laptop at port `8020`.

### API returns `401 Unauthorized`

- The telemetry key is missing, incorrect, or was not loaded before the backend started.
- Restart the backend after loading `ONYX_TELEMETRY_INGEST_API_KEY`.
- Make sure the client sends the key in the command shown in this guide.

### Client appears offline

- Keep the agent terminal window open.
- The API marks an endpoint offline when no heartbeat arrives for about 30 seconds.
- Use a unique `EndpointId` for every client.

### Port already in use

Find the process on the server laptop:

```powershell
Get-NetTCPConnection -LocalPort 8020 -State Listen | Select-Object OwningProcess
Get-NetTCPConnection -LocalPort 5183 -State Listen | Select-Object OwningProcess
```

Stop only the identified Onyx process, then restart the relevant terminal command.

---

## 13. Stop the system safely

- Press `Ctrl+C` in the backend terminal.
- Press `Ctrl+C` in the frontend terminal.
- Press `Ctrl+C` in each client agent terminal.
- For Sysmon forwarding, remove or disable the scheduled task only if you no longer want telemetry forwarding.
- Rotate the telemetry and response keys after a public demo or whenever a client bundle may have been copied outside the team.
