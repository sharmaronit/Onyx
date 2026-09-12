#!/usr/bin/env python
"""Test runner for MARL training."""
import subprocess
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent
logfile = project_root / "logs_marl_training.log"

# Remove old log
if logfile.exists():
    logfile.unlink()
    print(f"Cleared old log: {logfile}")

print("Starting MARL training launcher...")
with open(logfile, "w") as f:
    proc = subprocess.Popen(
        [sys.executable, str(project_root / "launch_marl.py")],
        stdout=f,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(project_root),
    )

print(f"Process PID: {proc.pid}")
print(f"Logging to: {logfile}")

# Wait for initialization
print("Waiting 8 seconds for initialization...")
time.sleep(8)

# Check if log has content
if logfile.exists():
    with open(logfile) as f:
        content = f.read()
    lines = content.splitlines()
    print(f"\n=== First 50 lines of log ===")
    for i, line in enumerate(lines[:50], 1):
        print(f"{i:3d}: {line}")
    print(f"\n(Total lines so far: {len(lines)})")
else:
    print(f"Log file not found at {logfile}")

print("\nDone.")
