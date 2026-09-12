"""Windows Service host. Imported only on Windows builds with pywin32 installed."""
import threading

import win32event
import win32service
import win32serviceutil
import servicemanager

from .host import run_agent_host
from .__main__ import data_dir


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
        self.worker = threading.Thread(target=run_agent_host, args=(data_dir(), self.worker_stop), daemon=True)
        self.worker.start()
        win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
        self.worker.join(timeout=10)


def run_service() -> None:
    """Enter the Windows Service Control Manager dispatcher."""
    servicemanager.Initialize("OnyxEndpointAgent", None)
    servicemanager.PrepareToHostSingle(OnyxEndpointAgentService)
    servicemanager.StartServiceCtrlDispatcher()
