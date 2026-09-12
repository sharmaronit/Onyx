"""Windows Service host. Imported only on Windows builds with pywin32 installed."""
import threading

import win32event
import win32service
import win32serviceutil

from .credentials import CredentialStore
from .runtime import AgentRunner
from .__main__ import data_dir


class OnyxEndpointAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = "OnyxEndpointAgent"
    _svc_display_name_ = "Onyx Endpoint Agent"
    _svc_description_ = "Collects configured Onyx endpoint security telemetry over HTTPS."

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.worker = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        config = CredentialStore(data_dir()).load()
        if not config:
            return
        runner = AgentRunner(config, data_dir())
        self.worker = threading.Thread(target=runner.run_forever, daemon=True)
        self.worker.start()
        win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)


def run_service() -> None:
    win32serviceutil.HandleCommandLine(OnyxEndpointAgentService)
