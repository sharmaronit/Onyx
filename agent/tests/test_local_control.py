import threading
from pathlib import Path

from agent.onyx_agent.ipc import AgentControlServer
from agent.onyx_agent.status import update_status


def test_local_status_and_diagnostics_never_expose_credentials(tmp_path: Path) -> None:
    update_status(tmp_path, enrolled=True, endpoint_id="endpoint-1", device_credential="must-not-leak", last_error=None)
    server = AgentControlServer(tmp_path, threading.Event())
    status = server._handle({"command": "status"})
    diagnostics = server._handle({"command": "diagnostics"})
    assert status["status"]["endpoint_id"] == "endpoint-1"
    assert "device_credential" not in status["status"]
    assert "device_credential" not in diagnostics["diagnostics"]


def test_retry_signals_agent_host(tmp_path: Path) -> None:
    retry = threading.Event()
    reply = AgentControlServer(tmp_path, retry)._handle({"command": "retry"})
    assert reply == {"ok": True}
    assert retry.is_set()
