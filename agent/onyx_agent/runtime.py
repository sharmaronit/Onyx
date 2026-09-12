import json
import platform
import socket
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from . import __version__
from .http import ApiClient, ApiError
from .logging import JsonLogger
from .queue import EncryptedQueue


class AgentRunner:
    def __init__(self, config: Dict[str, Any], data_dir: Path):
        self.config, self.data_dir = config, data_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = data_dir / "collector-state.json"
        self.log = JsonLogger(data_dir / "logs" / "agent.jsonl")
        self.queue = EncryptedQueue(data_dir / "queue", config["queue_key"])
        self.client = ApiClient(config["server_url"], config["device_credential"])

    def run_once(self) -> None:
        state = self._state(); system = platform.system()
        if system == "Windows":
            from .collectors.windows import collect
            events, health, marker = collect(int(state.get("defender_record_id") or 0)); state["defender_record_id"] = marker
        elif system == "Darwin":
            from .collectors.macos import collect
            events, health, marker = collect(state.get("apple_last_timestamp")); state["apple_last_timestamp"] = marker
        else:
            events, health = [], {"collector": "unsupported"}
        self._save_state(state)
        heartbeat = {"endpoint_id": self.config["endpoint_id"], "hostname": socket.gethostname(), "ip_address": self._ip_address(), "topology": self.config.get("topology", "enterprise_20n"), "agent_version": __version__, "platform": system, "metadata": {"collector_health": health, "queue": {"pending_batches": len(self.queue.batches())}, "response_controls_enabled": False}}
        try: self.client.request("POST", "/api/endpoints/heartbeat", heartbeat)
        except ApiError as exc: self.log.write("error", "heartbeat_failed", status=exc.status, detail=str(exc)); return
        for index in range(0, len(events), 100):
            batch = {"batch_id": str(uuid.uuid4()), "topology": self.config.get("topology", "enterprise_20n"), "events": events[index:index + 100], "created_at": datetime.now(timezone.utc).isoformat()}
            removed = self.queue.put(batch)
            if removed: self.log.write("error", "queue_events_discarded", reasons=removed)
        for batch in self.queue.batches():
            try:
                self.client.request("POST", f"/api/devices/{self.config['endpoint_id']}/telemetry/batches", {k: batch[k] for k in ("batch_id", "topology", "events")})
                self.queue.acknowledge(batch["batch_id"])
            except ApiError as exc:
                self.log.write("error", "telemetry_retry_scheduled", status=exc.status, detail=str(exc)); break

    def run_forever(self) -> None:
        delay = 1
        while True:
            try: self.run_once(); delay = 300
            except Exception as exc: self.log.write("error", "agent_cycle_failed", detail=str(exc)); delay = min(300, delay * 2)
            time.sleep(delay * (0.85 + (uuid.uuid4().int % 30) / 100))

    def _state(self) -> Dict[str, Any]:
        try: return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError): return {}
    def _save_state(self, state: Dict[str, Any]) -> None: self.state_path.write_text(json.dumps(state), encoding="utf-8")
    @staticmethod
    def _ip_address() -> str | None:
        try: return socket.gethostbyname(socket.gethostname())
        except OSError: return None
