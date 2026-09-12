#!/usr/bin/env python
import subprocess, sys, os
from pathlib import Path

os.chdir(Path(__file__).parent)

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

env = os.environ.copy()
env['PYTHONPATH'] = str(Path.cwd())

print('Starting MARL self-play...')
subprocess.run(cmd, env=env)
