# Slide 1 — Title Page

## SMART INDIA HACKATHON 2026

### Onyx
### Automated AI Threat Simulation and Proactive Cyber Defense

**Problem Statement ID:** SIH26145  
**Theme:** Cybersecurity & Defense  
**Category:** Software  
**Team:** ALGORYTHMS

**Tagline:** A digital twin that lets security teams test attack paths before attackers do.

---

# Slide 2 — Idea Title

## Onyx: From Alert Floods to a Defensible Patch Decision

**The problem**

Security teams receive isolated CVEs, alerts, and asset data. They still need to answer the harder question: *Which weakness creates the most dangerous route to a critical asset in our network?*

**The Onyx approach**

- Build a security-focused digital twin from network topology, endpoint evidence, vulnerabilities, and critical assets.
- Run attacker-versus-defender simulations inside that model, never on the production network.
- Trace successful routes, identify the bottleneck weakness, and rank the remediation action by expected risk reduction and effort.

**Why it is different**

- It evaluates a vulnerability in network context rather than treating its CVSS score as the final decision.
- It connects predictive simulation with an operational dashboard, endpoint telemetry, patch ROI, and response workflows.
- It gives analysts a clear recommendation with evidence they can review before taking action.

---

# Slide 3 — Technical Approach

## Digital Twin, World Model, and Defense Loop

**1. Observe the network**

- Windows endpoint agents send heartbeat and telemetry evidence to the FastAPI backend.
- The backend stores assets, vulnerabilities, incidents, and observed relationships in the network representation.

**2. Learn and simulate**

- A GraphSAGE-based world model predicts how compromise state can change after an attacker action. A GAT alternative is also available.
- The simulation environment supports Red Agent and Blue Agent behavior through multi-agent reinforcement learning.
- Attack-path analysis evaluates whether simulated routes can reach important assets.

**3. Prioritize and respond**

- Cost-aware ranking compares remediation effort with risk reduction.
- The analyst dashboard provides topology, exposure, telemetry, simulation, and patch-priority views.
- Authorized response commands support endpoint actions such as isolate or release, with command acknowledgement recorded by the backend.

**Implemented stack**

Python, PyTorch, PyTorch Geometric, Stable-Baselines3, Gymnasium, PettingZoo, NetworkX, FastAPI, React, TanStack Router, and Windows PowerShell automation.

---

# Slide 4 — Feasibility and Viability

## Prototype Status and Deployment Path

**What works today**

- React and FastAPI product interface with Demo and Reality modes.
- Live endpoint heartbeat, telemetry ingestion, incident handling, notifications, topology views, and endpoint-command acknowledgement APIs.
- Network simulation, attack-path regression tests, patch optimization, cost-model persistence, and report-generation endpoints.
- A PowerShell startup workflow for fast demonstration and complete model-training runs.

**Practical feasibility**

- The system can begin with a controlled network snapshot and read-only vulnerability data.
- Teams can validate each recommendation in the dashboard before using any endpoint response command.
- CPU mode supports demonstration. GPU acceleration shortens model-training time.

**Scale-up requirements**

- Validate data quality and topology completeness before relying on risk rankings.
- Add enterprise identity, role-based access control, secrets management, and audit retention for production deployment.
- Measure recommendation quality against analyst-reviewed incidents and penetration-test findings.

---

# Slide 5 — Impact and Benefits

## Value for Security Teams

**For analysts**

- One prioritized patch queue replaces scattered CVE lists and disconnected alerts.
- Each recommendation links remediation effort to the attack paths it disrupts.
- Interactive topology and exposure views make the reasoning visible instead of presenting a black-box score.

**For security leadership**

- Cost-aware patch ROI helps justify remediation work with measurable security context.
- Continuous simulation complements periodic penetration testing with repeatable scenario analysis.
- Reports, notifications, and historical records support operational review.

**For organizations with limited security capacity**

- A small team can focus first on the weaknesses most likely to enable lateral movement toward critical assets.
- The digital twin allows safe experimentation with defensive choices before changes reach the live environment.

---

# Slide 6 — Research and References

## Research Basis

**World models and latent simulation**

1. Ha, D. and Schmidhuber, J. (2018). *World Models*. Introduces a learned compressed environment for training and planning.  
   https://arxiv.org/abs/1803.10122

2. Hafner, D. et al. (2018). *Learning Latent Dynamics for Planning from Pixels (PlaNet)*. Presents latent dynamics for model-based planning.  
   https://arxiv.org/abs/1811.04551

3. Hafner, D. et al. (2019). *Dream to Control: Learning Behaviors by Latent Imagination (Dreamer)*. Uses imagined trajectories in a learned latent world model.  
   https://arxiv.org/abs/1912.01603

4. Hafner, D. et al. (2023). *Mastering Diverse Domains through World Models (DreamerV3)*. Demonstrates robust world-model learning across diverse tasks.  
   https://arxiv.org/abs/2301.04104

**Cybersecurity and implementation references**

- MITRE ATT&CK knowledge base for attacker tactics and techniques: https://attack.mitre.org/
- National Vulnerability Database for CVE and CVSS data: https://nvd.nist.gov/
- Onyx prototype: GraphSAGE/GAT world-model modules, attack simulation environment, FastAPI backend, React dashboard, and endpoint telemetry components.
