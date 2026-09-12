# 🚀 Onyx — How to Start the Project

> **Platform:** Windows (PowerShell)
> **Python:** 3.9+ (3.11 recommended)
> **GPU:** Optional (CUDA) — CPU fallback supported

---

## 📋 Prerequisites

| Requirement | Why |
|---|---|
| **Python 3.9+** | Core runtime for training, simulation, and backends |
| **pip** | Dependency installation |
| **Node.js 18+** & **npm** | Only needed if running the React web frontend |
| **PowerShell** | Primary launch scripts are `.ps1` files |
| **Git** | Version control (optional, already cloned) |

### One-time setup: execution policy

If PowerShell blocks `.ps1` scripts, run this once:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 🔧 Environment Setup (First Time Only)

### 1. Create & activate the virtual environment

```powershell
cd D:\Onyx
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install Python dependencies

```powershell
pip install -r requirements.txt
```

> **Note:** `start.ps1` will auto-create the `.venv` and activate it if missing, so you can skip this step if you use the PowerShell launcher.

### 3. Verify the installation

```powershell
python test_imports.py
```

Expected output:
```
✓ AttackerEnv imported successfully
✓ DefenderEnv imported successfully
✓ OnyxMARLEnv imported successfully
```

---

## ⚡ Quick Start — Three Ways to Run

### Option A: PowerShell Launcher (`start.ps1`) — Recommended

The all-in-one script that handles venv, GPU detection, and mode selection.

```powershell
cd D:\Onyx
```

| Command | What it does | Time |
|---|---|---|
| `.\start.ps1 demo` | Launches **Streamlit dashboard only** (assumes trained models exist) | < 1 min |
| `.\start.ps1 train` | Runs all **8 training stages**, then launches demo | ~12–14 hrs |
| `.\start.ps1 full` | Same as `train` + auto-starts Streamlit after completion | ~12–14 hrs + demo |

After launch, open **http://localhost:8511** in your browser.

---

### Option B: Python CLI (`run.py`)

For granular control over individual pipeline stages.

```powershell
cd D:\Onyx
.\.venv\Scripts\Activate.ps1
```

| Command | Stage |
|---|---|
| `python run.py --stage setup` | Verify environment, imports, GPU, data files |
| `python run.py --stage data` | Generate 102K+ transition episodes to `data/episodes/transitions.h5` |
| `python run.py --stage gnn` | Train GNN world model → `checkpoints/gnn_world_model.pt` |
| `python run.py --stage red` | Train Red (attacker) agent (1M steps) → `checkpoints/red_agent.zip` |
| `python run.py --stage blue` | Train Blue (defender) agent (1M steps) → `checkpoints/blue_agent.zip` |
| `python run.py --stage marl` | MARL self-play (5 rounds × 200K steps) → `checkpoints/marl/` |
| `python run.py --stage patch` | Run patch impact optimizer → `reports/patch_analysis.json` |
| `python run.py --stage report` | Generate morning report → `reports/morning_report.html` |
| `python run.py --all` | Run **all stages** in order |
| `python run.py --demo` | Start Streamlit dashboard |

> **Tip:** Stages are designed to be run sequentially. Each stage depends on the outputs of previous stages.

---

### Option C: React Web Frontend (`web/`)

A full React + Vite frontend connected to a FastAPI backend.

```powershell
cd D:\Onyx\web
```

#### 1. Install backend deps (once)

```powershell
pip install -r backend/requirements.txt
```

> This pulls in `fastapi` and `uvicorn` on top of the base `requirements.txt`.

#### 2. Install frontend deps (once)

```powershell
npm install
```

#### 3. Start the full dev stack

```powershell
npm run dev
```

This starts **both**:
- **FastAPI backend** at `http://127.0.0.1:8020`
- **Vite frontend** at `http://localhost:5183`

The Vite dev server proxies all `/api` requests to the backend automatically.

#### Individual components

| Command | What it starts |
|---|---|
| `npm run dev` | Backend + Frontend together |
| `npm run dev:frontend` | Vite dev server only (port 5183) |
| `npm run dev:backend` | FastAPI backend only (port 8020) |
| `npm run smoke:backend` | Quick backend health check |
| `npm run build` | Production build → `web/dist/` |

#### Custom Python interpreter

If Python is not on your PATH:

```powershell
$env:BACKEND_PYTHON = "path/to/python.exe"
npm run dev
```

---

## 📊 What You See After Startup

### Streamlit Dashboard (port 8511)

| Tab | Description |
|---|---|
| **Interactive Network Graph** | 20-node enterprise topology visualization (pyvis) |
| **CVSS vs Onyx Ranking** | Side-by-side comparison of standard CVE scores vs AI-recommended patches |
| **MARL Arms Race** | Red vs Blue agent learning curves across 5 training rounds |
| **Morning Report** | Top 5 patch recommendations with full rationale |

### React Web App (port 5183)

| Page | Description |
|---|---|
| **Network Map** | Live topology + CVE tables |
| **Attack Analysis** | Real simulation runs with patch optimizer |
| **Red vs Blue** | MARL results with chart cards |
| **Report** | Morning report preview |

---

## 🔄 The 8-Stage Pipeline (In Detail)

```
Stage 0: Setup      → Verify Python, PyTorch, CUDA, data files, topology loading
Stage 1: Data       → Generate 50K episodes × 3 topologies → transitions.h5
Stage 2: GNN        → Train GraphSAGE world model (50 epochs, target AUC > 0.87)
Stage 3: Red Agent  → Train MaskablePPO attacker (1M timesteps)
Stage 4: Blue Agent → Train MaskablePPO defender (1M timesteps)
Stage 5: MARL       → Alternating self-play (5 rounds × 200K steps each)
Stage 6: Patch      → Evaluate every patchable CVE (500 baseline + 100 per patch)
Stage 7: Report     → Render HTML/PDF morning security report
```

### Stage dependency chain

```
setup → data → gnn → red → blue → marl → patch → report
```

> All stages must be run in order. The output of each feeds into the next.

---

## 📁 Key File Locations

| Item | Path |
|---|---|
| PowerShell launcher | `start.ps1` |
| Python pipeline CLI | `run.py` |
| Master config | `configs/config.yaml` |
| Python requirements | `requirements.txt` |
| Streamlit demo app | `demo/app.py` |
| React frontend | `web/` |
| Web backend server | `web/backend/server.py` |
| Network topologies | `data/topologies/*.json` |
| CVE database | `data/cve/cve_dataset.json` |
| Trained models | `checkpoints/` |
| MARL checkpoints | `checkpoints/marl/` |
| Generated reports | `reports/` |
| Training logs | `logs/` |
| Tests | `tests/` |

---

## 🛠 Utility Scripts

| Script | Purpose |
|---|---|
| `test_imports.py` | Verify core module imports (AttackerEnv, DefenderEnv, MARLEnv) |
| `test_marl_launch.py` | Test MARL training launch configuration |
| `launch_blue.py` | Standalone Blue agent training launcher |
| `launch_marl.py` | Standalone MARL self-play launcher |
| `monitor_blue.py` | Live TensorBoard progress monitor for Blue agent training |

---

## 🐛 Troubleshooting

### PowerShell execution policy error
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Virtual environment not found
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### GPU not detected
- The system falls back to CPU automatically.
- Demo mode works fine on CPU; training will be significantly slower.
- Verify with: `python -c "import torch; print(torch.cuda.is_available())"`

### Streamlit port 8511 already in use
```powershell
# Kill existing process
Get-Process streamlit | Stop-Process -Force

# Or use a different port
streamlit run demo/app.py --server.port 8502
```

### Web backend port 8020 already in use
```powershell
# Find and kill the process
Get-NetTCPConnection -LocalPort 8020 -State Listen |
  Select-Object -ExpandProperty OwningProcess |
  ForEach-Object { Stop-Process -Id $_ -Force }
```

### Training crashes mid-way
Check the last successful stage in logs, then re-run from that stage:
```powershell
python run.py --stage <next-stage-name>
```

### Import errors
Make sure you're in the project root and PYTHONPATH is set:
```powershell
$env:PYTHONPATH = "D:\Onyx"
python run.py --stage setup
```

---

## 🏁 TL;DR — Fastest Path to a Working Demo

```powershell
cd D:\Onyx
.\start.ps1 demo
```

Open **http://localhost:8511** — done. ✅

> Pre-trained checkpoints already exist in `checkpoints/`, so the demo works immediately without any training.
