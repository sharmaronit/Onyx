import json
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List


PREDICATE = "subsystem CONTAINS[c] 'XProtect' OR subsystem CONTAINS[c] 'MRT' OR process CONTAINS[c] 'XProtect' OR process CONTAINS[c] 'MRT' OR eventMessage CONTAINS[c] 'security policy' OR eventMessage CONTAINS[c] 'authentication'"


def collect(since: str | None) -> tuple[List[Dict[str, Any]], Dict[str, Any], str]:
    """Narrow Unified Log allowlist. This is Apple security logging, not full EDR."""
    command = ["/usr/bin/log", "show", "--style", "json", "--last", "10m", "--predicate", PREDICATE]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=45, check=True)
    except FileNotFoundError:
        return [], {"apple_security_log": "unsupported"}, since or ""
    except Exception as exc:
        return [], {"apple_security_log": "error", "detail": str(exc)[:200]}, since or ""
    events, newest = [], since or ""
    for line in result.stdout.splitlines():
        try: row = json.loads(line)
        except json.JSONDecodeError: continue
        timestamp = str(row.get("timestamp") or row.get("time") or "")
        if since and timestamp and timestamp <= since: continue
        newest = max(newest, timestamp)
        raw = {"provider": "apple_security_log", "subsystem": row.get("subsystem"), "process": row.get("process"), "message": str(row.get("eventMessage") or row.get("message") or "")[:4000]}
        event_id = f"apple-{abs(hash(json.dumps(raw, sort_keys=True)))}-{timestamp}"
        events.append({"event_id": event_id, "timestamp": timestamp or datetime.now(timezone.utc).isoformat(), "event_type": "apple_security_log", "confidence": 0.8, "raw": raw})
    return events, {"apple_security_log": "ok"}, newest
