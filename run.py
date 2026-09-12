"""
run.py — Onyx top-level orchestrator.

Runs the complete pipeline in the correct order:
  1. Verify setup (imports, GPU, data files)
  2. Generate episode dataset (if not cached)
  3. Train GNN world model
  4. Train Red (attacker) agent
  5. Train Blue (defender) agent
  6. MARL self-play training
  7. Run patch optimizer
  8. Generate report

Usage:
    # Full pipeline
    python run.py --all

    # Individual stages
    python run.py --stage setup
    python run.py --stage data
    python run.py --stage gnn
    python run.py --stage red
    python run.py --stage blue
    python run.py --stage marl
    python run.py --stage patch
    python run.py --stage report

    # Start the demo
    python run.py --demo
"""

from __future__ import annotations
import argparse
import subprocess
import sys
import os
from pathlib import Path


def check(msg: str):
    print(f"  [OK] {msg}")


def warn(msg: str):
    print(f"  [WARN] {msg}")


def fail(msg: str):
    print(f"  [FAIL] {msg}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Stage: Setup
# ---------------------------------------------------------------------------

def stage_setup():
    print("\n[Stage 0] Verifying setup...\n")

    # Python version
    import sys
    if sys.version_info < (3, 9):
        fail(f"Python 3.9+ required. Got {sys.version}")
    check(f"Python {sys.version.split()[0]}")

    # PyTorch + CUDA
    try:
        import torch
        check(f"PyTorch {torch.__version__}")
        if torch.cuda.is_available():
            check(f"CUDA available: {torch.cuda.get_device_name(0)}")
        else:
            warn("CUDA not available — training will be slow on CPU")
    except ImportError:
        fail("PyTorch not installed. Run: pip install -r requirements.txt")

    # PyG
    try:
        import torch_geometric
        check(f"PyTorch Geometric {torch_geometric.__version__}")
    except ImportError:
        warn("torch-geometric not installed. GNN training will fail.")

    # SB3 + sb3-contrib
    try:
        import stable_baselines3
        check(f"Stable-Baselines3 {stable_baselines3.__version__}")
    except ImportError:
        fail("stable-baselines3 not installed.")

    try:
        import sb3_contrib
        check("sb3-contrib (MaskablePPO) available")
    except ImportError:
        fail("sb3-contrib not installed.")

    # Data files
    required_data = [
        "data/topologies/enterprise_20n.json",
        "data/topologies/small_office_10n.json",
        "data/topologies/cloud_hybrid_30n.json",
        "data/cve/cve_dataset.json",
        "configs/config.yaml",
    ]
    for path in required_data:
        if Path(path).exists():
            check(f"Data file: {path}")
        else:
            fail(f"Missing: {path}")

    # Load and validate topology
    from src.graph.topology_loader import load_topology
    from src.graph.cve_tagger import load_cve_database, tag_graph

    graph = load_topology("data/topologies/enterprise_20n.json")
    cve_db = load_cve_database("data/cve/cve_dataset.json")
    tag_graph(graph, cve_db)

    tagged_nodes = sum(1 for n in graph.nodes if n.num_vulns > 0)
    check(f"Enterprise topology: {graph.num_nodes} nodes, {tagged_nodes} with CVEs")

    print("\n[DONE] Setup verified.\n")


# ---------------------------------------------------------------------------
# Stage: Generate data
# ---------------------------------------------------------------------------

def stage_data():
    print("\n[Stage 1] Generating episode dataset...\n")
    from src.simulator.episode_generator import generate_dataset

    stats = generate_dataset(
        topologies_dir="data/topologies",
        cve_path="data/cve/cve_dataset.json",
        output_path="data/episodes/transitions.h5",
        episodes_per_topology=5000,
        max_steps=50,
        seed=42,
        verbose=True,
    )
    print(f"\n[DONE] Dataset generated: {stats['total_transitions']:,} transitions\n")


# ---------------------------------------------------------------------------
# Stage: Train GNN
# ---------------------------------------------------------------------------

def stage_gnn():
    print("\n[Stage 2] Training GNN World Model...\n")
    cmd = [
        sys.executable, "-m", "src.training.train_gnn",
        "--topologies_dir", "data/topologies",
        "--cve_path", "data/cve/cve_dataset.json",
        "--hdf5_cache", "data/episodes/transitions.h5",
        "--output", "checkpoints/gnn_world_model.pt",
        "--log_dir", "logs/gnn",
        "--arch", "sage",
        "--epochs", "50",
        "--episodes", "50000",
    ]
    subprocess.run(cmd, check=True)
    print("\n[DONE] GNN world model trained.\n")


# ---------------------------------------------------------------------------
# Stage: Train Red agent
# ---------------------------------------------------------------------------

def stage_red():
    print("\n[Stage 3] Training Red (attacker) agent...\n")
    cmd = [
        sys.executable, "-m", "src.training.train_red",
        "--topology", "data/topologies/enterprise_20n.json",
        "--cve_path", "data/cve/cve_dataset.json",
        "--output", "checkpoints/red_agent.zip",
        "--log_dir", "logs/red",
        "--timesteps", "1000000",
    ]
    env = os.environ.copy()
    env['PYTHONPATH'] = str(Path(__file__).parent)
    subprocess.run(cmd, check=True, env=env, cwd=Path(__file__).parent)
    print("\n[DONE] Red agent trained.\n")


# ---------------------------------------------------------------------------
# Stage: Train Blue agent
# ---------------------------------------------------------------------------

def stage_blue():
    print("\n[Stage 4] Training Blue (defender) agent...\n")
    cmd = [
        sys.executable, "-m", "src.training.train_blue",
        "--topology", "data/topologies/enterprise_20n.json",
        "--cve_path", "data/cve/cve_dataset.json",
        "--output", "checkpoints/blue_agent.zip",
        "--log_dir", "logs/blue",
        "--timesteps", "1000000",
    ]
    env = os.environ.copy()
    env['PYTHONPATH'] = str(Path(__file__).parent)
    subprocess.run(cmd, check=True, env=env, cwd=Path(__file__).parent)
    print("\n[DONE] Blue agent trained.\n")


# ---------------------------------------------------------------------------
# Stage: MARL self-play
# ---------------------------------------------------------------------------

def stage_marl():
    print("\n[Stage 5] MARL alternating self-play...\n")
    cmd = [
        sys.executable, "-m", "src.training.train_marl",
        "--topology",    "data/topologies/enterprise_20n.json",
        "--cve_path",    "data/cve/cve_dataset.json",
        "--red_start",   "checkpoints/red_agent.zip",
        "--blue_start",  "checkpoints/blue_agent.zip",
        "--output_dir",  "checkpoints/marl",
        "--n_rounds",    "5",
        "--steps_per_round", "200000",
    ]
    env = os.environ.copy()
    env['PYTHONPATH'] = str(Path(__file__).parent)
    subprocess.run(cmd, check=True, env=env, cwd=Path(__file__).parent)
    print("\n[DONE] MARL training complete.\n")


# ---------------------------------------------------------------------------
# Stage: Patch optimizer
# ---------------------------------------------------------------------------

def stage_patch():
    print("\n[Stage 6] Running patch optimizer...\n")
    if not Path("checkpoints/red_agent.zip").exists():
        fail("Red agent not found. Run Stage 3 first.")

    from src.analysis.patch_optimizer import compute_patch_impact, save_results
    results = compute_patch_impact(
        topology_path="data/topologies/enterprise_20n.json",
        cve_path="data/cve/cve_dataset.json",
        agent_path="checkpoints/red_agent.zip",
        n_baseline=500,
        n_eval_per_patch=100,
        verbose=True,
    )
    save_results(results, "reports/patch_analysis.json")
    print("\n[DONE] Patch analysis complete.\n")


# ---------------------------------------------------------------------------
# Stage: Report
# ---------------------------------------------------------------------------

def stage_report():
    print("\n[Stage 7] Generating report...\n")
    if not Path("reports/patch_analysis.json").exists():
        fail("Patch analysis not found. Run Stage 6 first.")

    import json
    with open("reports/patch_analysis.json") as f:
        results = json.load(f)

    from src.analysis.report_generator import generate_report
    generate_report(
        patch_results=results,
        topology_name="enterprise_20n",
        n_episodes=10000,
        output_html="reports/morning_report.html",
        output_pdf="reports/morning_report.pdf",
    )
    print("\n[DONE] Report generated.\n")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def start_demo():
    print("\n[Demo] Starting Streamlit app...\n")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "demo/app.py"], check=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

STAGES = {
    "setup":  stage_setup,
    "data":   stage_data,
    "gnn":    stage_gnn,
    "red":    stage_red,
    "blue":   stage_blue,
    "marl":   stage_marl,
    "patch":  stage_patch,
    "report": stage_report,
}

if __name__ == "__main__":
    # Change to project root
    os.chdir(Path(__file__).parent)
    sys.path.insert(0, str(Path(__file__).parent))

    parser = argparse.ArgumentParser(description="Onyx pipeline")
    parser.add_argument("--stage", choices=list(STAGES.keys()) + ["all"])
    parser.add_argument("--all",   action="store_true")
    parser.add_argument("--demo",  action="store_true")
    args = parser.parse_args()

    if args.demo:
        start_demo()
    elif args.all:
        for name, fn in STAGES.items():
            fn()
    elif args.stage:
        STAGES[args.stage]()
    else:
        parser.print_help()
