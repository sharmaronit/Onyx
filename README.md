# Onyx

### Evidence-led security operations for employee devices and network exposure

Onyx is a cybersecurity research platform and prototype console that helps security and IT teams understand which devices, vulnerabilities, and network relationships deserve attention first. It combines endpoint telemetry, a network knowledge graph, vulnerability context, safe offline attack simulation, and remediation prioritization in one workflow.

> **Prototype status:** Onyx is suitable for lab evaluation, demonstrations, and supervised design-partner pilots. It is not currently a replacement for antivirus, MDM, EDR, penetration testing, or a 24/7 SOC. Simulation output is modelled evidence, not a probability of a real breach.

## The problem

Small and midsize organizations often have endpoint alerts, scanner exports, and incomplete asset inventories, but limited time to decide what to fix first. CVSS severity alone does not explain how a finding relates to an organization's own devices and connections.

Onyx helps answer:

> **Which verified action should our administrator take next, and what evidence supports it?**

```text
Enroll or import evidence → map assets and relationships → review findings
→ prioritize remediation → assign ownership → refresh evidence → verify completion
```

## Capabilities

- Endpoint heartbeats and observed network relationships
- Microsoft Defender and Sysmon event ingestion through consent-based collectors
- Source-attributed vulnerability finding ingestion
- Network topology and attack-path visualization
- Offline, world-model-only attack simulation with reproducible seeds
- Red/Blue reinforcement-learning research environments
- Patch prioritization and effort-aware ranking
- Provenance, freshness, confidence, replay, and evidence-bundle fields
- FastAPI backend with SQLite persistence
- React, TanStack Start, Vite, TypeScript, and Tailwind console
- Streamlit research/demo application

The maintained console is in `web/`. `web_backup/` and `Security Sentinel/` are historical or alternate frontend copies.

## Boundaries

Simulation runs against a frozen graph and does not send packets or endpoint commands. It cannot discover a true zero-day merely by simulating one, and a simulated attack win rate does not equal a customer's breach likelihood.

Reality-mode findings require evidence from enrolled endpoints, observed relationships, and imported vulnerability data. A prioritization estimate is an estimate. Keep existing endpoint protection and device-management platforms in place while evaluating Onyx.

Endpoint response tooling is experimental. Use it only on infrastructure you own or are explicitly authorized to administer, and test disruptive controls in a lab before production use.

## Architecture

```text
Endpoint / scanner / SIEM evidence
                 │
                 ▼
        Telemetry normalization
                 │
                 ▼
       Network knowledge graph
          ┌──────┴──────┐
          ▼             ▼
   Reality evidence   Offline simulator
          │             │
          └──────┬──────┘
                 ▼
     Exposure and remediation ranking
                 │
                 ▼
   Assigned actions, reports, verification
```

The research path adds a Graph Neural Network world model and reinforcement-learning agents. Customer workflows should remain useful when those models are unavailable and label rule-based, estimated, simulated, and telemetry-backed results separately.

## Repository layout

| Path | Purpose |
| --- | --- |
| `src/graph/` | Topology, CVE tagging, graph conversion |
| `src/simulator/` | Rule-based transitions and episode generation |
| `src/models/` | GNN world-model and policy code |
| `src/envs/` | Attacker, defender, and MARL environments |
| `src/analysis/` | Path analysis, patch ranking, cost model, reports |
| `src/integrations/` | Telemetry clients, mapping, and storage |
| `web/` | React/TanStack console and FastAPI backend |
| `demo/` | Streamlit research/demo application |
| `data/topologies/` | Small sanitized example topologies |
| `data/cve/` | Example vulnerability fixtures; validate production identifiers |
| `configs/` | Simulation, graph, telemetry, and cost configuration |
| `tests/` | Focused regression and API tests |
| `tools/` | Endpoint collectors, evidence tooling, and lab utilities |
| `docs/` | Telemetry, credibility, and runbook documentation |

Generated reports, model checkpoints, logs, databases, virtual environments, dependency folders, archives, and secrets are excluded by `.gitignore`.

## Quick start

Requirements: Windows PowerShell, Python 3.10+, Node.js, and npm.

### Web console and backend

```powershell
cd D:\Onyx
npm --prefix web install
npm --prefix web run dev
```

The launcher starts the frontend and FastAPI backend. The console is normally at `http://localhost:3000`; the backend listens on port `8020`.

If the project virtual environment is unavailable, select a working interpreter:

```powershell
$env:BACKEND_PYTHON = "C:\Path\to\python.exe"
npm --prefix web run dev
```

### Python demo

```powershell
cd D:\Onyx
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\start.ps1 demo
```

Read `START_GUIDE.md` and `LIVE_DEMO_GUIDE.md` before using demo scripts.

### Research training

The full pipeline can take many hours and requires compatible ML dependencies and model storage:

```powershell
.\start.ps1 train
```

Do not run training as part of a customer deployment. Trained artifacts are not included in this repository.

## Verification

```powershell
python -B -m unittest tests.test_attack_path_regression -v
python -B -m unittest tests.test_endpoint_response_api -v
npm --prefix web run lint
npm --prefix web run build
```

Known issues and validation limits are documented in [ONYX_BUSINESS_AND_TECHNICAL_REVIEW.md](ONYX_BUSINESS_AND_TECHNICAL_REVIEW.md). Passing a route test does not establish tenant isolation, endpoint containment, model validity, or production readiness.

## Safe pilot direction

The most credible first paid offer is a supervised, read-only remediation assessment for one organization using an existing scanner export and a small approved device cohort. Deliver a source-backed action list, named owners, effort assumptions, a review session, and a later verification report.

Before distributing an endpoint agent or exposing the API to the internet, implement authenticated administrator access, tenant/data isolation, per-device identity, signed and verified installers, command retries and recovery, backup/retention, and controlled containment tests.

## Security and privacy

- Use only owned or explicitly authorized infrastructure.
- Never commit `.onyx-secrets.cmd`, API keys, tokens, private telemetry, databases, or generated bundles.
- Keep customer deployments isolated until tenant boundaries are implemented and tested.
- Collect only the endpoint and security metadata required for the agreed workflow.
- Define retention, access, and deletion rules with every customer.
- Do not use experimental response controls on production devices without a rollback plan.

## Documents

- [Business and technical review](ONYX_BUSINESS_AND_TECHNICAL_REVIEW.md)
- [Real-data integration TODO](docs/REAL_DATA_INTEGRATION_TODO.md)
- [Simulation credibility plan](docs/SIMULATION_CREDIBILITY_PLAN.md)
- [Telemetry schema](docs/TELEMETRY_SCHEMA.md)
- [Live demo guide](LIVE_DEMO_GUIDE.md)
- [Server/client runbook](SERVER_AND_CLIENT_LAPTOP_RUNBOOK.md)

## License

No license file is currently provided. Treat this repository as all-rights-reserved until the project owner adds an explicit license.
