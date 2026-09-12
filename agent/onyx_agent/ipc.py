"""Local JSON control channel. Device credentials never leave this process."""
import json
import os
import platform
import socket
import threading
from pathlib import Path
from typing import Any, Callable, Dict

from .enrollment import perform_enrollment
from .status import read_status, update_status


PIPE_NAME = r"\\.\pipe\onyx-agent-v1"
SOCKET_PATH = "/var/run/onyx-agent-v1.sock"
MAX_REQUEST_BYTES = 64 * 1024
SAFE_STATUS_KEYS = {
    "service_state", "enrolled", "endpoint_id", "organization_id", "server_url",
    "agent_version", "platform", "last_attempt_at", "last_connected_at", "last_error",
    "collector_health", "pending_batches", "updated_at", "next_action",
}


def _safe_status(data_dir: Path) -> Dict[str, Any]:
    status = read_status(data_dir)
    return {key: status.get(key) for key in SAFE_STATUS_KEYS if key in status}


class AgentControlServer:
    def __init__(self, data_dir: Path, retry_event: threading.Event):
        self.data_dir = data_dir
        self.retry_event = retry_event
        self.stop_event = threading.Event()
        self.listener: Any = None

    def serve(self) -> None:
        if platform.system() == "Windows":
            self._serve_windows()
        else:
            self._serve_unix()

    def stop(self) -> None:
        self.stop_event.set()
        try:
            if self.listener:
                self.listener.close()
        except OSError:
            pass

    def _handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        command = request.get("command")
        if command == "status":
            return {"ok": True, "status": _safe_status(self.data_dir)}
        if command == "retry":
            self.retry_event.set()
            update_status(self.data_dir, next_action="connection_retry_requested")
            return {"ok": True}
        if command == "diagnostics":
            return {"ok": True, "diagnostics": _safe_status(self.data_dir)}
        if command == "enroll":
            if read_status(self.data_dir).get("enrolled"):
                return {"ok": False, "error": "This laptop is already enrolled"}
            result = perform_enrollment(
                self.data_dir,
                str(request.get("server_url") or ""),
                str(request.get("token") or ""),
                str(request.get("topology") or "enterprise_20n"),
            )
            update_status(self.data_dir, service_state="running", enrolled=True, **result)
            self.retry_event.set()
            return {"ok": True, "device": result}
        return {"ok": False, "error": "Unsupported local command"}

    def _process_bytes(self, raw: bytes) -> bytes:
        if len(raw) > MAX_REQUEST_BYTES:
            return b'{"ok":false,"error":"Request is too large"}\n'
        try:
            request = json.loads(raw.decode("utf-8"))
            if not isinstance(request, dict):
                raise ValueError("Expected a JSON object")
            response = self._handle(request)
        except Exception as exc:
            response = {"ok": False, "error": str(exc)[:500]}
        return (json.dumps(response, allow_nan=False) + "\n").encode("utf-8")

    def _serve_unix(self) -> None:
        path = Path(SOCKET_PATH)
        path.unlink(missing_ok=True)
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.listener = listener
        listener.bind(SOCKET_PATH)
        os.chmod(SOCKET_PATH, 0o666)
        listener.listen(8)
        listener.settimeout(1)
        while not self.stop_event.is_set():
            try:
                connection, _ = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with connection:
                raw = self._read_socket(connection)
                connection.sendall(self._process_bytes(raw))
        path.unlink(missing_ok=True)

    @staticmethod
    def _read_socket(connection: socket.socket) -> bytes:
        chunks, size = [], 0
        while size <= MAX_REQUEST_BYTES:
            chunk = connection.recv(min(4096, MAX_REQUEST_BYTES + 1 - size))
            if not chunk:
                break
            chunks.append(chunk); size += len(chunk)
            if b"\n" in chunk:
                break
        return b"".join(chunks).split(b"\n", 1)[0]

    def _serve_windows(self) -> None:
        import pywintypes
        import win32file
        import win32pipe
        import win32security

        descriptor = win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
            "D:(A;;GA;;;SY)(A;;GA;;;BA)(A;;GRGW;;;AU)",
            win32security.SDDL_REVISION_1,
        )
        attributes = pywintypes.SECURITY_ATTRIBUTES()
        attributes.SECURITY_DESCRIPTOR = descriptor
        while not self.stop_event.is_set():
            pipe = win32pipe.CreateNamedPipe(
                PIPE_NAME,
                win32pipe.PIPE_ACCESS_DUPLEX,
                win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_READMODE_BYTE | win32pipe.PIPE_WAIT,
                8,
                MAX_REQUEST_BYTES,
                MAX_REQUEST_BYTES,
                1000,
                attributes,
            )
            try:
                win32pipe.ConnectNamedPipe(pipe, None)
                _, raw = win32file.ReadFile(pipe, MAX_REQUEST_BYTES + 1)
                win32file.WriteFile(pipe, self._process_bytes(bytes(raw).split(b"\n", 1)[0]))
                win32file.FlushFileBuffers(pipe)
            except pywintypes.error:
                if not self.stop_event.is_set():
                    continue
            finally:
                try:
                    win32pipe.DisconnectNamedPipe(pipe)
                except pywintypes.error:
                    pass
                win32file.CloseHandle(pipe)
