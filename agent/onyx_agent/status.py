import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


_lock = threading.Lock()


def update_status(data_dir: Path, **changes: Any) -> Dict[str, Any]:
    """Atomically update the sanitized status snapshot used by local IPC."""
    path = data_dir / "status.json"
    data_dir.mkdir(parents=True, exist_ok=True)
    with _lock:
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            current = {}
        current.update(changes)
        current["updated_at"] = datetime.now(timezone.utc).isoformat()
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(current, allow_nan=False), encoding="utf-8")
        os.replace(temporary, path)
        return current


def read_status(data_dir: Path) -> Dict[str, Any]:
    try:
        return json.loads((data_dir / "status.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"service_state": "starting", "enrolled": False}
