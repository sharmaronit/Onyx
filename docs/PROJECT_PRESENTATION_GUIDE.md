# Onyx Project Presentation Guide

## 1. What This Project Is
Onyx is an AI-driven cyber defense simulation platform.

It models an organization's infrastructure as a graph, simulates attacker behavior, trains attacker and defender agents with reinforcement learning, and recommends the most effective vulnerability patches based on measured simulated impact, not just CVSS severity.

In one line:
Onyx helps security teams answer: Which single fix reduces my real attack risk the most in my exact network?

---

## 2. The Problem Onyx Solves
Traditional vulnerability management often prioritizes by CVSS score alone.

That misses network context:
- How vulnerabilities chain across topology
- Which assets are reachable from compromise paths
- Which patch gives the largest risk reduction in this specific environment

Onyx addresses this by combining:
- Network graph modeling
- World-model learning (GNN)
- Red/Blue reinforcement learning
- Patch impact simulation and ranking

---

## 3. Core Idea and Workflow
### Step A: Build a graph of the network
Input topology JSON files define nodes (servers, workstations, routers, firewalls, database/cloud assets) and edges (ssh/http/sql/rdp/ftp/vpn links).

### Step B: Attach vulnerabilities
A CVE dataset is matched by software/version and attached to graph nodes.

### Step C: Simulate attacks
A rule-based simulator generates attack episodes where compromise probability is tied to node vulnerability severity.

### Step D: Train a world model
A Graph Neural Network (GraphSAGE primary; GAT/GCN alternatives) learns transition dynamics: given state + attacked node, predict next compromised nodes.

### Step E: Train RL agents
- Red agent (attacker): learns efficient paths to critical assets.
- Blue agent (defender): learns patch/isolation decisions to reduce compromise.
- MARL self-play alternates Red and Blue training rounds to model adversarial adaptation.

### Step F: Optimize patch decisions
For each CVE patch candidate, Onyx re-evaluates attack success and computes risk reduction impact.

### Step G: Produce actionable outputs
- Attack path analytics
- Patch ranking by simulation impact
- Cost-aware ranking (risk reduction per estimated effort)
- Explainability cards
- Morning report (HTML/PDF)

---

## 4. System Architecture (High Level)
### Graph and simulation layer
- Topology loader builds in-memory graph
- CVE tagger attaches vulnerability metadata
- Rule-based simulator executes stochastic attack steps
- TransitionModel abstraction supports rule-based or GNN transition backend

### ML layer
- GNN world model trained on generated transitions
- RL agents trained with MaskablePPO (action masking prevents invalid actions)
- Alternating MARL rounds produce Red/Blue arms-race metrics

### Analytics layer
- Attack path frequency analysis
- Patch impact computation
- Cost model ROI ranking
- Explainability narrative generation
- Report generation for executive communication

### Product/UI layer
- Streamlit demo app for fast research showcase
- React + Vite frontend for command center UX
- FastAPI backend exposing simulation, optimization, telemetry, report, and persistence endpoints
- SQLite for user preferences, history, model versions, request logs, and training jobs

---

## 5. Data Inputs and Artifacts
### Inputs
- Topologies: data/topologies/*.json
- CVE dataset: data/cve/cve_dataset.json
- Config: configs/config.yaml
- Optional telemetry events: data/telemetry/ingested_events.json

### Key generated artifacts
- Episode transitions: data/episodes/transitions.h5
- GNN model: checkpoints/gnn_world_model.pt
- Red agent: checkpoints/red_agent.zip
- Blue agent: checkpoints/blue_agent.zip
- MARL rounds/finals: checkpoints/marl/*
- Patch analysis: reports/patch_analysis.json
- Morning report: reports/morning_report.html and reports/morning_report.pdf

---

## 6. Training and Execution Pipeline
The orchestrator runs an 8-stage flow:
1. Setup verification (deps, GPU, data integrity)
2. Dataset generation from simulator episodes
3. GNN world-model training
4. Red agent training
5. Blue agent training
6. MARL self-play (multi-round alternating training)
7. Patch optimization
8. Report generation

Typical full-cycle runtime target in docs: about 12-14 hours.

Quick usage modes via PowerShell launcher:
- demo: start Streamlit using existing checkpoints
- train: run full pipeline
- full: run training and then launch demo

---

## 7. Reinforcement Learning Design
### Red agent environment
- Action: choose node to attack
- Reward: positive for compromise, high bonus for critical asset, penalties for invalid actions and time
- Uses action masks so only reachable/valid targets are selected

### Blue agent environment
- Action: patch node or isolate node
- Reward: penalize attacker progress, bonus for defending critical assets until episode end

### MARL setup
- Alternating optimization:
  - Train Red against frozen Blue context
  - Train Blue against frozen Red context
- Produces round-by-round Red vs Blue win-rate curves

---

## 8. Analytics and Decision Intelligence
### Attack path analysis
Computes:
- Edge traversal frequencies
- Node compromise frequencies
- Top recurring full attack paths
- Overall simulated success rate

### Patch optimizer (flagship value)
For each vulnerability candidate:
- Remove the CVE from a copy of the graph
- Re-run attack evaluations
- Measure baseline vs patched success rate
- Rank by simulation impact

This directly exposes divergence between:
- CVSS rank (global severity)
- Simulation rank (network-context risk impact)

### Cost-aware ranking
Adds estimated engineering effort (by node type, severity, criticality) and computes ROI-style scores:
- risk reduction percentage points per effort hour

### Explainability cards
Generates plain-language decision cards with:
- Why a patch is ranked high
- Trade-offs
- Before/after risk preview

---

## 9. Web Platform and APIs
### Frontend (React)
Main pages:
- Dashboard
- Analysis Hub
- Training
- Reports

Analysis Hub supports:
- Topology/scenario selection
- Simulation, hybrid, or telemetry data source mode
- Telemetry weight blending in hybrid mode
- Running simulation and patch optimization
- Viewing replay and MARL outputs

### Backend (FastAPI)
Broad capability groups:
- Health/status and topology info
- Simulation/scenario execution
- Patch optimization and cost ranking
- Explainability and reports
- Telemetry ingest/status/sample loading
- User preferences and scenario history
- Cost model versioning/activation
- Training job queue/status/cancel
- Request logs and metrics

### Persistence
SQLite schema includes:
- user_preferences
- scenario_history
- analysis_results
- cost_models
- request_logs
- training_jobs

---

## 10. Telemetry and Real-Data Strategy
The project includes a phased simulation to telemetry integration path:
- simulation mode
- telemetry mode
- hybrid mode (weighted blend)

Important transparency metadata is exposed in responses:
- data_source
- requested_data_source
- data_source_note
- data_freshness_at
- confidence markers (estimated, hybrid, measured)

This supports credible demo storytelling and judge-facing provenance clarity.

---

## 11. Main Strengths (Presentation Talking Points)
1. Network-context-aware patch prioritization, not CVSS-only sorting.
2. Full-stack pipeline from raw topology to executive report.
3. Combines graph ML + RL + adversarial self-play in one workflow.
4. Actionable output format (top fix with measurable impact).
5. Productized delivery via Streamlit demo and React/FastAPI app.
6. Real-data integration path already scaffolded with telemetry ingestion and fallback logic.

---

## 12. Current Limitations and Risks
1. Real-world telemetry validation phase is still in progress (per integration TODO).
2. Many metrics remain simulation-derived in default mode.
3. Training is compute-intensive and long-running.
4. Patch optimization cost can increase with topology and CVE count.
5. Some web features are still evolving placeholders (for example, training visualization depth and PDF/export UX flow).

---

## 13. Recommended Presentation Flow (7-10 Minutes)
### Slide 1: Problem
- Vulnerability overload + CVSS-only prioritization gap

### Slide 2: Solution
- Onyx as AI cyber war-game and patch intelligence engine

### Slide 3: Architecture
- Graph model -> simulator -> GNN -> RL agents -> patch optimizer -> reporting

### Slide 4: Method
- How attack episodes are generated and how models are trained

### Slide 5: Key output
- CVSS rank vs simulation rank divergence and top patch impact

### Slide 6: Product demo
- Dashboard -> Analysis Hub run -> patch ranking -> report preview

### Slide 7: Real-data roadmap
- simulation/hybrid/telemetry modes and provenance transparency

### Slide 8: Business value
- Faster remediation decisions, better risk reduction per engineering effort

---

## 14. Short Demo Script (Narration)
We load a topology and CVE data, then run attack simulation across many episodes.
The Red agent identifies realistic compromise paths, while Blue strategies model defense actions.
Next, the optimizer tests each patch candidate and quantifies how much each one reduces attack success.
Instead of saying patch highest CVSS first, Onyx shows which fix actually blocks the most attacks in this network.
Finally, we generate an executive report with ranked actions, impact estimates, and transparent data-source confidence.

---

## 15. One-Minute Executive Summary
Onyx is an AI-powered cyber risk prioritization platform.
It models enterprise infrastructure as a graph, simulates adversarial behavior, trains attacker and defender RL agents, and recommends the highest-impact patch actions by measured scenario reduction.
Its core innovation is replacing generic severity-only patch ordering with network-context, simulation-backed decision intelligence, delivered through an interactive web product and executive-ready reporting.
