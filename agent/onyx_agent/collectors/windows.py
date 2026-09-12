import json
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List


def collect(last_record_id: int) -> tuple[List[Dict[str, Any]], Dict[str, Any], int]:
    """Read Defender Operational 1116/1117 only; no Defender settings are changed."""
    command = "Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Windows Defender/Operational'; Id=1116,1117} | Select-Object RecordId,Id,TimeCreated,Message | ConvertTo-Json -Compress"
    try:
        result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command], capture_output=True, text=True, timeout=30, check=True)
        rows = json.loads(result.stdout or "[]")
        if isinstance(rows, dict): rows = [rows]
    except FileNotFoundError:
        return [], {"windows_defender": "unsupported"}, last_record_id
    except Exception as exc:
        return [], {"windows_defender": "error", "detail": str(exc)[:200]}, last_record_id
    events, newest = [], last_record_id
    for row in rows:
        record_id = int(row.get("RecordId") or 0)
        if record_id <= last_record_id: continue
        newest = max(newest, record_id)
        event_id = int(row.get("Id") or 0)
        events.append({"event_id": f"defender-{record_id}", "timestamp": str(row.get("TimeCreated") or datetime.now(timezone.utc).isoformat()), "event_type": "malware_detected" if event_id == 1116 else "malware_action", "confidence": 1.0, "blocked": event_id == 1117, "raw": {"provider": "Microsoft Defender Operational", "windows_event_id": event_id, "record_id": record_id, "message": str(row.get("Message") or "")[:4000]}})
    return events, {"windows_defender": "ok"}, newest
