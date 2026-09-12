#!/usr/bin/env python
"""Test launcher for MARL training."""
import subprocess
import sys
import os
from pathlib import Path
import time

os.chdir(Path(__file__).parent)

# Write status
with open('logs_marl_training.log', 'w') as f:
    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting MARL launcher test\n")
    f.write(f"Python: {sys.executable}\n")
    f.write(f"CWD: {os.getcwd()}\n")
    f.write(f"Python Version: {sys.version}\n")
    f.flush()

    cmd = [
        sys.executable, '-m', 'src.training.train_marl',
        '--topology', 'data/topologies/enterprise_20n.json',
        '--cve_path', 'data/cve/cve_dataset.json',
        '--red_start', 'checkpoints/red_agent.zip',
        '--blue_start', 'checkpoints/blue_agent.zip',
        '--output_dir', 'checkpoints/marl',
        '--n_rounds', '5',
        '--steps_per_round', '200000',
    ]

    f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Command: {' '.join(cmd)}\n\n")
    f.flush()

    env = os.environ.copy()
    env['PYTHONPATH'] = str(Path.cwd())

    try:
        result = subprocess.run(cmd, env=env, capture_output=False, timeout=120)
        f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Process exited with code {result.returncode}\n")
    except subprocess.TimeoutExpired:
        f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Process timeout after 120 seconds\n")
    except Exception as e:
        f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error: {e}\n")

print("Test launcher completed. Check logs_marl_training.log")
