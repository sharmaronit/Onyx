#!/bin/bash
set -euo pipefail
ARCH="${1:?pass x64 or arm64}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
case "$ARCH" in x64) RUNNER_ARCH="x86_64";; arm64) RUNNER_ARCH="arm64";; *) echo "Unknown macOS architecture: $ARCH" >&2; exit 2;; esac
mkdir -p "$ROOT/dist"
python3 -m pip install -r "$ROOT/requirements.txt"
cd "$ROOT"
python3 -m PyInstaller --clean --noconfirm --onefile --name "OnyxAgent-$ARCH" onyx_agent_entry.py
test "$(uname -m)" = "$RUNNER_ARCH" || { echo "Build this binary on a $RUNNER_ARCH Mac runner." >&2; exit 2; }
set +e
SMOKE_OUTPUT="$("$ROOT/dist/OnyxAgent-$ARCH" status 2>&1)"
SMOKE_STATUS=$?
set -e
[[ "$SMOKE_STATUS" = "1" && "$SMOKE_OUTPUT" == *"Not enrolled"* ]] || { echo "Packaged agent command-line smoke test failed: $SMOKE_OUTPUT" >&2; exit 3; }
