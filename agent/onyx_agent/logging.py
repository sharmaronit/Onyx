import json
from datetime import datetime, timezone
from pathlib import Path


class JsonLogger:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, level: str, event: str, **detail: object) -> None:
        row = {"timestamp": datetime.now(timezone.utc).isoformat(), "level": level, "event": event, **detail}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
