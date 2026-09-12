import base64
import ctypes
import json
import platform
import subprocess
from ctypes import wintypes
from pathlib import Path
from typing import Any, Dict, Optional


SERVICE_NAME = "com.onyx.endpoint-agent"


class CredentialStore:
    """Stores the complete device binding in the OS credential facility, never in installer arguments."""
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def save(self, value: Dict[str, Any]) -> None:
        raw = json.dumps(value, allow_nan=False).encode("utf-8")
        if platform.system() == "Darwin":
            subprocess.run(["/usr/bin/security", "add-generic-password", "-U", "-s", SERVICE_NAME, "-a", "root", "-w", "-"], input=raw, check=True)
            return
        if platform.system() == "Windows":
            self._write_windows(self._protect_windows(raw)); return
        raise RuntimeError("Onyx Agent supports Windows and macOS only")

    def load(self) -> Optional[Dict[str, Any]]:
        try:
            if platform.system() == "Darwin":
                result = subprocess.run(["/usr/bin/security", "find-generic-password", "-s", SERVICE_NAME, "-a", "root", "-w"], capture_output=True, check=True)
                return json.loads(result.stdout.decode("utf-8"))
            if platform.system() == "Windows":
                return json.loads(self._unprotect_windows(self._read_windows()).decode("utf-8"))
        except (FileNotFoundError, subprocess.CalledProcessError, OSError, ValueError):
            return None
        return None

    def delete(self) -> None:
        if platform.system() == "Darwin":
            subprocess.run(["/usr/bin/security", "delete-generic-password", "-s", SERVICE_NAME, "-a", "root"], check=False, capture_output=True)
        elif platform.system() == "Windows":
            self._credential_file().unlink(missing_ok=True)

    def _credential_file(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "device.dpapi"

    def _write_windows(self, protected: bytes) -> None:
        path = self._credential_file(); path.write_bytes(base64.b64encode(protected))
        # The service runs as LocalSystem; make inherited ACLs unavailable to ordinary users.
        subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r", "SYSTEM:F", "Administrators:F"], check=True, capture_output=True)

    def _read_windows(self) -> bytes:
        return base64.b64decode(self._credential_file().read_bytes())

    @staticmethod
    def _protect_windows(raw: bytes) -> bytes:
        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]
        buffer = ctypes.create_string_buffer(raw)
        source = DATA_BLOB(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
        target = DATA_BLOB()
        if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(source), None, None, None, None, 4, ctypes.byref(target)):
            raise ctypes.WinError()
        try: return ctypes.string_at(target.pbData, target.cbData)
        finally: ctypes.windll.kernel32.LocalFree(target.pbData)

    @staticmethod
    def _unprotect_windows(raw: bytes) -> bytes:
        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]
        buffer = ctypes.create_string_buffer(raw)
        source, target = DATA_BLOB(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), DATA_BLOB()
        if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(target)):
            raise ctypes.WinError()
        try: return ctypes.string_at(target.pbData, target.cbData)
        finally: ctypes.windll.kernel32.LocalFree(target.pbData)
