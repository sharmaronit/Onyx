#!/usr/bin/env python
import subprocess, sys, os
from pathlib import Path

os.chdir(Path(__file__).parent)

cmd = [
    sys.executable, '-u', 'src/training/train_blue.py',
    '--topology', 'data/topologies/enterprise_20n.json',
    '--cve_path', 'data/cve/cve_dataset.json',
    '--output', 'checkpoints/blue_agent.zip',
    '--log_dir', 'logs/blue',
    '--timesteps', '1000000',
]

env = os.environ.copy()
env['PYTHONPATH'] = str(Path.cwd())

print('Starting Blue Agent training...')
subprocess.run(cmd, env=env)
