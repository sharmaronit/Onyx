"""Simple local store for ingested telemetry events."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


RELATIVE_STORE_PATH = Path("data") / "telemetry" / "ingested_events.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def telemetry_store_path(project_root: Path) -> Path:
    return project_root / RELATIVE_STORE_PATH


def read_ingested_events(project_root: Path) -> Dict[str, Any]:
    path = telemetry_store_path(project_root)
    if not path.exists():
        return {"updated_at": None, "events": []}

    with open(path, "r", encoding="utf-8-sig") as f:
        payload = json.load(f)

    if isinstance(payload, list):
        return {"updated_at": None, "events": payload}

    return {
        "updated_at": payload.get("updated_at"),
        "events": payload.get("events", []),
        "source": payload.get("source"),
        "topology": payload.get("topology"),
    }


def write_ingested_events(
    project_root: Path,
    events: List[Dict[str, Any]],
    source: str,
    topology: str,
) -> Dict[str, Any]:
    path = telemetry_store_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "updated_at": _utc_now_iso(),
        "source": source,
        "topology": topology,
        "events": events,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload
