"""Windows Service host. Imported only on Windows builds with pywin32 installed."""
from __future__ import annotations

import json
import threading
import traceback
from datetime import datetime, timezone

import win32event
import win32service
import win32serviceutil
import servicemanager

from .host import run_agent_host
from .__main__ import data_dir
from .status import update_status


def _record_startup_error(error: BaseException) -> None:
    """Leave an actionable diagnostic when a background collector cannot start."""
    message = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    try:
        logs = data_dir() / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        with (logs / "service-startup.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "time": datetime.now(timezone.utc).isoformat(),
                "level": "error",
                "component": "windows_service",
                "error": message,
            }) + "\n")
        update_status(data_dir(), service_state="error", last_error=str(error))
    except Exception:
        # A broken data directory must never bring down the service dispatcher.
        pass
    try:
        servicemanager.LogErrorMsg(f"Onyx Endpoint Agent startup error:\n{message}")
    except Exception:
        pass


class OnyxEndpointAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = "OnyxEndpointAgent"
    _svc_display_name_ = "Onyx Endpoint Agent"
    _svc_description_ = "Collects configured Onyx endpoint security telemetry over HTTPS."

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.worker = None
        self.worker_stop = threading.Event()

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.worker_stop.set()
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        def run_worker() -> None:
            try:
                run_agent_host(data_dir(), self.worker_stop)
            except BaseException as error:
                _record_startup_error(error)

        try:
            servicemanager.LogInfoMsg("Onyx Endpoint Agent service started")
            self.worker = threading.Thread(target=run_worker, name="onyx-agent-host", daemon=True)
        except BaseException as error:
            _record_startup_error(error)
            raise
        self.worker.start()
        win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
        self.worker.join(timeout=10)


def run_service() -> None:
    """Enter the Windows Service Control Manager dispatcher."""
    servicemanager.Initialize("OnyxEndpointAgent", None)
    servicemanager.PrepareToHostSingle(OnyxEndpointAgentService)
    servicemanager.StartServiceCtrlDispatcher()
