# Onyx — Live Multi-Laptop Demo Guide

> **Purpose:** Step-by-step instructions to demonstrate Onyx detecting simulated malware
> across 2–3 real laptops connected to a shared network, live in front of hackathon judges.

---

## Table of Contents

- [Prerequisites (Both Approaches)](#prerequisites-both-approaches)
- [Approach 1 — WiFi Hotspot + Live Telemetry Agents (⭐ Recommended)](#approach-1--wifi-hotspot--live-telemetry-agents--recommended)
- [Approach 2 — Sysmon + Windows Event Forwarding (Advanced)](#approach-2--sysmon--windows-event-forwarding-advanced)
- [The "Attack" — What To Run on the VM](#the-attack--what-to-run-on-the-vm)
- [Demo Script for Judges (3-Minute Talk Track)](#demo-script-for-judges-3-minute-talk-track)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites (Both Approaches)

### Hardware

| Role | Machine | Requirements |
|---|---|---|
| **Laptop A** (Server) | Your primary laptop | Runs Onyx backend + React dashboard |
| **Laptop B** (Agent) | A teammate's laptop | Windows 10/11, PowerShell 5.1+ |
| **Laptop C** (Attacker) | Your or another teammate's laptop | Windows with VirtualBox or Hyper-V, a lightweight Linux VM (Kali/Ubuntu) |

### Software Pre-Installed

- **Laptop A:** Python 3.10+, Node.js 18+, Onyx repo at `D:\Onyx`
- **Laptop B:** PowerShell 5.1+ (built into Windows)
- **Laptop C:** VirtualBox/Hyper-V with a Linux VM (Kali Linux recommended for pre-installed `nmap`, `netcat`, etc.)

### Network

- All laptops must be on the **same network**. The easiest way:
  - Turn on **Mobile Hotspot** on Laptop A (Settings → Network → Mobile Hotspot)
  - Connect Laptops B & C to that hotspot
  - Note Laptop A's IP on the hotspot interface (e.g., `192.168.137.1`)

---

## Approach 1 — WiFi Hotspot + Live Telemetry Agents (⭐ Recommended)

> **Why this approach:** Zero installation on agent laptops. Uses the existing
> `live_laptop_telemetry.ps1` script that ships with Onyx. Works in 10 minutes of setup.

### Phase 1 — Start Onyx Server on Laptop A

Open two terminal windows on Laptop A:

**Terminal 1 — Backend:**
```powershell
cd D:\Onyx
.\.venv\Scripts\Activate.ps1
cd web\backend
uvicorn server:app --host 0.0.0.0 --port 8020
```

> **Important:** Use `--host 0.0.0.0` so the backend listens on all interfaces (not just localhost).
> This makes it reachable from Laptops B and C over the hotspot.

**Terminal 2 — Frontend:**
```powershell
cd D:\Onyx\web
npm run dev -- --host 0.0.0.0
```

**Verify:** Open `http://192.168.137.1:5183` (replace with Laptop A's actual hotspot IP) in a browser.
You should see the Onyx dashboard.

### Phase 2 — Find Laptop A's Hotspot IP

```powershell
# Run on Laptop A
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like "*Wi-Fi*" -or $_.InterfaceAlias -like "*Hotspot*" } | Select-Object IPAddress, InterfaceAlias
```

Note the IP (e.g., `192.168.137.1`). This is `$SERVER_IP` in all commands below.

### Phase 3 — Run Telemetry Agent on Laptop B

Copy just one file to Laptop B: `D:\Onyx\tools\live_laptop_telemetry.ps1`

> You can use a USB drive, email, or shared folder to copy this file. It's a single self-contained script.

On **Laptop B**, open PowerShell and run:

```powershell
# Replace 192.168.137.1 with Laptop A's actual IP
.\live_laptop_telemetry.ps1 `
  -IngestUrl "http://192.168.137.1:8020/api/telemetry/ingest" `
  -Topology "enterprise_20n" `
  -Mode "enriched" `
  -TargetNode "node_05_app"
```

**What this does:**
- Scrapes all active TCP connections (`Get-NetTCPConnection`)
- Scrapes top running processes (`Get-Process`)
- In `enriched` mode, adds realistic seed attack events (credential access, lateral movement, privilege escalation)
- Sends everything to Onyx's `/api/telemetry/ingest` endpoint
- Events appear on the dashboard under **Telemetry Status**

### Phase 4 — Run Telemetry Agent on Laptop C (Host OS)

Same as Laptop B. Copy the script and run:

```powershell
.\live_laptop_telemetry.ps1 `
  -IngestUrl "http://192.168.137.1:8020/api/telemetry/ingest" `
  -Topology "enterprise_20n" `
  -Mode "pure" `
  -TargetNode "node_03_workstation"
```

> Use `"pure"` mode on Laptop C's host OS so it only sends real telemetry. The VM will
> generate the "suspicious" activity later.

### Phase 5 — Launch the "Attack" VM on Laptop C

See [The "Attack" section](#the-attack--what-to-run-on-the-vm) below for what to run inside the VM.

After the attack runs, re-run the telemetry script on Laptop C's host:

```powershell
# The new suspicious connections from the VM will now appear in Get-NetTCPConnection
.\live_laptop_telemetry.ps1 `
  -IngestUrl "http://192.168.137.1:8020/api/telemetry/ingest" `
  -Topology "enterprise_20n" `
  -Mode "enriched" `
  -TargetNode "node_09_db"
```

> Switching to `enriched` mode now injects the attack chain seed events alongside the real
> connections, simulating what a real SIEM integration would detect.

### Phase 6 — Show Results on the Dashboard

On **Laptop A's browser** (the dashboard):

1. Go to **Analysis Hub** → click **"Judge Preset"** button (auto-configures optimal settings)
2. Set **Data Source** to `hybrid` and **Telemetry Weight** to `0.6`
3. Click **"Run Simulation"**
4. Wait ~10 seconds. The simulation results appear:
   - **Success rate** (should spike due to new attack events)
   - **Top attack paths** (will now include paths through the "compromised" laptop)
   - **Patch recommendations** (Onyx will recommend patching the node the VM attacked)

**Verify telemetry was ingested:**
```powershell
# Run from any machine
Invoke-RestMethod "http://192.168.137.1:8020/api/telemetry/status?topology=enterprise_20n"
```

Expected output includes `event_count > 0`, `critical_reaches > 0`.

### Phase 7 — Run the Full Live Demo Script (Optional, Automated)

Onyx ships with an automated demo orchestrator that chains ingest → simulate → patch optimize:

```powershell
# Run on Laptop A
cd D:\Onyx\tools
.\run_live_demo.ps1 `
  -ApiBaseUrl "http://127.0.0.1:8020" `
  -Topology "enterprise_20n" `
  -Mode "enriched" `
  -Episodes 1000 `
  -TelemetryWeight 0.6
```

This prints a clean summary:
```
=========================================
Onyx Live Demo Summary
=========================================
Mode: enriched
Topology: enterprise_20n
Telemetry: events=47, blocked=3, critical=2
Simulation: success_rate=43.20%, paths=29
Top Path: mail_server
Top Patch Actions:
  - sarah_laptop | CVE-2024-10001 | impact=18.5%
  - node_05_app  | CVE-2024-10002 | impact=12.3%
=========================================
```

---

## Approach 2 — Sysmon + Windows Event Forwarding (Advanced)

> **Why this approach:** Captures kernel-level events (process creation, network connections,
> registry modifications, DLL loads) via Microsoft Sysmon. Far richer and more realistic
> telemetry than Approach 1. **Tradeoff:** More setup time required (20–30 minutes per laptop).

### Phase 1 — Start Onyx Server on Laptop A

Same as Approach 1, Phase 1. Start backend on `0.0.0.0:8020` and frontend on `0.0.0.0:5183`.

### Phase 2 — Build a Client Bundle on Laptop A

Onyx includes a one-command bundle builder that packages everything the agent laptops need:

```powershell
cd D:\Onyx\tools\sysmon

# Build a pre-filled bundle with your server's IP baked in
.\build_client_bundle.ps1 `
  -PresetIngestUrl "http://192.168.137.1:8020/api/telemetry/ingest" `
  -PresetApiKey "" `
  -PresetTopology "enterprise_20n" `
  -PresetSource "sysmon_forwarder"
```

This creates a zip file at:
```
tools/sysmon/dist/OnyxSysmonClientBundle-YYYYMMDD-HHMMSS.zip
```

### Phase 3 — Deploy Bundle to Laptops B & C

**Option A — USB Drive (Simplest):**
1. Copy the generated `.zip` to a USB drive
2. Plug into Laptop B, extract the zip
3. Right-click `RUN_SETUP_AS_ADMIN.cmd` → **Run as administrator**
4. Repeat for Laptop C

**Option B — LAN Share (No USB needed):**

On Laptop A:
```powershell
cd D:\Onyx\tools\sysmon
.\prepare_and_share_bundle_lan.ps1 -CreateSmbShare -Force
```

On Laptop B/C (Admin PowerShell):
```powershell
# Replace LAPTOP-A with Laptop A's hostname
$bundle = "\\LAPTOP-A\OnyxBundle\OnyxSysmonClientBundle-latest.zip"
.\download_and_setup_other_laptop.ps1 -BundleSource $bundle
```

**Option C — Remote Push from Laptop A (Zero-Touch):**
```powershell
cd D:\Onyx\tools\sysmon
$cred = Get-Credential  # Admin creds for target laptops

.\deploy_bundle_to_laptops.ps1 `
  -ComputerName LAPTOP-B,LAPTOP-C `
  -Credential $cred `
  -Force
```

> This remotely copies the bundle, creates a scheduled task, and starts the Sysmon forwarder —
> all without touching the target laptops.

### Phase 4 — What Gets Installed on Agent Laptops

The bundle installs and configures:

| Component | Purpose |
|---|---|
| **Sysmon** (`sysmonconfig.xml`) | Captures process creation (Event 1), network connections (Event 3), file creation (Event 11), registry modifications (Event 13) |
| **forwarder.py** | Python script that reads Windows Event Log for Sysmon events, batches them, and POSTs to Onyx's ingest API every 5 seconds |
| **Scheduled Task** | Runs forwarder automatically on boot (SYSTEM account) |
| **forwarder.env** | Pre-configured with your server IP, topology, and API key |

### Phase 5 — Verify Sysmon Is Forwarding

On Laptop B/C, check forwarder is running:
```powershell
Get-ScheduledTask -TaskName "OnyxSysmonForwarder" | Select-Object State
# Should show: Running
```

On Laptop A, check events are being received:
```powershell
Invoke-RestMethod "http://127.0.0.1:8020/api/telemetry/status?topology=enterprise_20n"
# event_count should be > 0 and increasing
```

### Phase 6 — Launch the Attack VM & Detect

Same as Approach 1. Run the attack on Laptop C's VM (see next section).

**The difference with Sysmon:** When the VM runs `nmap` or connects to other machines, Sysmon on Laptop C's host captures:
- **Event 3 (Network Connect):** VM bridged adapter connections to other IPs
- **Event 1 (Process Create):** Any suspicious processes spawned
- **Event 11 (File Create):** Dropped files from the "malware"

These are all forwarded to Onyx automatically by the forwarder service, creating a rich event stream that the hybrid simulation uses to detect the attack path.

### Phase 7 — Show Results

Same as Approach 1, Phase 6. Open the dashboard on Laptop A and run a hybrid simulation.

---

## The "Attack" — What To Run on the VM

> These are **safe, non-malicious** network scanning commands that produce the kind of telemetry
> Onyx is designed to detect. They look suspicious to monitoring tools without causing harm.

### Option A — Simple Port Scan (Recommended for Demo)

Inside the Linux VM on Laptop C:

```bash
# Scan Laptop A (the server)
nmap -sT -T4 192.168.137.1

# Scan Laptop B
nmap -sT -T4 192.168.137.X

# Rapid connection attempts (simulates brute force)
for i in $(seq 1 50); do
  nc -z -w1 192.168.137.1 22 80 443 3389 8020 5432 2>/dev/null
  echo "Attempt $i"
done
```

### Option B — Simulated Lateral Movement

```bash
# SSH brute-force attempt (will fail, but generates connection telemetry)
for i in $(seq 1 20); do
  ssh -o ConnectTimeout=1 -o StrictHostKeyChecking=no admin@192.168.137.1 2>/dev/null
  ssh -o ConnectTimeout=1 -o StrictHostKeyChecking=no admin@192.168.137.X 2>/dev/null
done

# HTTP reconnaissance
curl -s http://192.168.137.1:8020/api/status
curl -s http://192.168.137.1:8020/api/topology/enterprise_20n
curl -s http://192.168.137.1:8020/api/telemetry/status
```

### Option C — "Malware-Like" File Drop (Visual Impact)

```bash
# Create a suspicious-looking file (harmless)
echo "This is a simulated ransomware payload" > /tmp/ransomware_payload.exe
echo "Exfiltrating data..." > /tmp/exfil_log.txt

# Simulate data exfiltration attempt
curl -X POST http://192.168.137.1:8020/api/telemetry/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source": "malware_vm",
    "topology": "enterprise_20n",
    "events": [{
      "event_id": "malware-001",
      "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
      "source_node": "'"$HOSTNAME"'",
      "target_node": "customer_db",
      "event_type": "data_exfiltration",
      "cve_id": "CVE-2024-DEMO-001",
      "cvss_score": 9.5,
      "confidence": 0.92,
      "blocked": false,
      "reached_critical": true,
      "raw": {
        "payload_type": "ransomware_simulator",
        "bytes_attempted": 50000,
        "target_data": "customer_records"
      }
    }]
  }'
```

> **This is the money shot for the demo.** This directly injects a high-confidence, critical-reaching
> event into Onyx. The dashboard will immediately show a spike in risk and recommend patching
> the attack path.

---

## Demo Script for Judges (3-Minute Talk Track)

| Time | What You Do | What You Say |
|:---:|---|---|
| **0:00** | Show dashboard with green/healthy graph | *"This is Onyx monitoring our live network. 3 machines, all healthy."* |
| **0:30** | Point to telemetry panel showing events from Laptops B & C | *"Each machine runs a lightweight telemetry agent — it sends real OS-level network and process data to Onyx."* |
| **1:00** | Switch to VM on Laptop C, run the nmap scan | *"Now I'm simulating a compromised machine. This VM is running a port scan — the kind of thing real malware does for reconnaissance."* |
| **1:30** | Switch back to Laptop A dashboard, re-run telemetry ingest | *"Watch the dashboard. The telemetry pipeline picks up the new suspicious connections..."* |
| **1:45** | Click "Run Simulation" (hybrid mode) | *"Onyx now runs thousands of simulated attacks using this REAL telemetry data, blended with our AI model."* |
| **2:15** | Results appear — elevated success rate, attack paths highlighted | *"Attack success rate jumped to 43%. The AI found 29 unique attack paths through our network."* |
| **2:30** | Scroll to patch recommendations | *"And here's the actionable output: 'Patch Sarah's VPN client.' That single fix blocks 18% of all successful attacks — even though it's only a CVSS 7.1, way below the CVSS 9.8 on the database."* |
| **2:50** | Show the CVSS vs Simulation rank divergence | *"THAT is the core insight. CVSS alone would tell you to patch the database. Onyx tells you to patch the bottleneck. That's the difference between whack-a-mole and actual risk reduction."* |

---

## Troubleshooting

### "Connection refused" from Laptops B/C

- Ensure backend is started with `--host 0.0.0.0`, NOT `--host 127.0.0.1`
- Check Windows Firewall on Laptop A: allow inbound on port `8020` and `5183`
  ```powershell
  # Run on Laptop A (Admin PowerShell)
  New-NetFirewallRule -DisplayName "Onyx Backend" -Direction Inbound -Port 8020 -Protocol TCP -Action Allow
  New-NetFirewallRule -DisplayName "Onyx Frontend" -Direction Inbound -Port 5183 -Protocol TCP -Action Allow
  ```

### Hotspot IP not found

```powershell
ipconfig | Select-String -Pattern "192.168" -Context 1,0
```
Look for the adapter named "Local Area Connection* X" or "Wi-Fi Direct".

### Telemetry not appearing on dashboard

1. Check ingest worked: `Invoke-RestMethod "http://$SERVER_IP:8020/api/telemetry/status?topology=enterprise_20n"`
2. Make sure Data Source is set to `hybrid` or `telemetry` (not `simulation`)
3. Re-run the telemetry script — it's a one-shot, not a daemon

### VM can't reach the network

- VirtualBox: Set network adapter to **Bridged Adapter** (bridges to the hotspot)
- Hyper-V: Create an **External Switch** bound to the WiFi adapter
- Verify: From inside the VM, `ping 192.168.137.1` should work

### Sysmon forwarder not starting (Approach 2)

```powershell
# Check task status
Get-ScheduledTask -TaskName "OnyxSysmonForwarder" | Format-List *

# Check Sysmon is installed
sysmon -c

# Manually start forwarder for debugging
cd C:\ProgramData\Onyx\SysmonForwarder
.\.venv\Scripts\python.exe forwarder.py
```

---

## Pre-Demo Checklist

- [ ] Laptop A hotspot is ON and IP is noted
- [ ] Backend is running on `0.0.0.0:8020` (check with `curl http://localhost:8020/api/status`)
- [ ] Frontend is running on `0.0.0.0:5183`
- [ ] Firewall rules added for ports 8020 and 5183
- [ ] Laptop B connected to hotspot and telemetry script tested
- [ ] Laptop C connected to hotspot, host telemetry tested
- [ ] VM on Laptop C has bridged networking and can ping Laptop A
- [ ] Attack commands tested inside VM at least once
- [ ] Dashboard opens from Laptop B/C's browser (sanity check)
- [ ] Ran full demo flow end-to-end at least once in rehearsal
