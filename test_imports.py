#!/usr/bin/env python
"""Simple import test for MARL."""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("Testing imports...")
try:
    from src.envs.attacker_env import AttackerEnv
    print("✓ AttackerEnv imported successfully")
except Exception as e:
    print(f"✗ Failed to import AttackerEnv: {e}")

try:
    from src.envs.defender_env import DefenderEnv
    print("✓ DefenderEnv imported successfully")
except Exception as e:
    print(f"✗ Failed to import DefenderEnv: {e}")

try:
    from src.envs.marl_env import OnyxMARLEnv
    print("✓ OnyxMARLEnv imported successfully")
except Exception as e:
    print(f"✗ Failed to import OnyxMARLEnv: {e}")

print("All imports tested.")
