import platform
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .credentials import CredentialStore
from .ipc import AgentControlServer
from .runtime import AgentRunner
from .status import update_status


def run_agent_host(data_dir: Path, stop_event: threading.Event | None = None) -> None:
    stop_event = stop_event or threading.Event()
    retry_event = threading.Event()
    ipc = AgentControlServer(data_dir, retry_event)
    ipc_thread = threading.Thread(target=ipc.serve, name="onyx-local-control", daemon=True)
    ipc_thread.start()
    update_status(data_dir, service_state="running", agent_version=__version__, platform=platform.system())
    next_cycle = 0.0
    reported_binding = None
    try:
        while not stop_event.is_set():
            config = CredentialStore(data_dir).load()
            if not config:
                if reported_binding is not False:
                    update_status(data_dir, enrolled=False, service_state="waiting_for_enrollment")
                    reported_binding = False
                retry_event.wait(1); retry_event.clear()
                continue
            binding = (config["endpoint_id"], config["organization_id"], config["server_url"])
            if reported_binding != binding:
                update_status(
                    data_dir,
                    enrolled=True,
                    endpoint_id=config["endpoint_id"],
                    organization_id=config["organization_id"],
                    server_url=config["server_url"],
                )
                reported_binding = binding
            now = time.monotonic()
            if retry_event.is_set() or now >= next_cycle:
                retry_event.clear()
                try:
                    AgentRunner(config, data_dir).run_once()
                    next_cycle = time.monotonic() + 300
                except Exception as exc:
                    update_status(data_dir, last_error=str(exc)[:500], last_attempt_at=datetime.now(timezone.utc).isoformat())
                    next_cycle = time.monotonic() + 30
            stop_event.wait(min(1, max(0.1, next_cycle - time.monotonic())))
    finally:
        update_status(data_dir, service_state="stopped")
        ipc.stop()
