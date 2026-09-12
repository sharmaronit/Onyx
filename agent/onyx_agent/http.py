import json
import ssl
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPSHandler, ProxyHandler


class ApiError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class ApiClient:
    """Uses OS proxy settings and standard certificate verification; TLS cannot be disabled."""
    def __init__(self, base_url: str, credential: str | None = None, timeout_seconds: int = 20):
        if not base_url.startswith("https://") and not base_url.startswith("http://127.0.0.1") and not base_url.startswith("http://localhost"):
            raise ValueError("Onyx backend URL must use HTTPS")
        self.base_url = base_url.rstrip("/")
        self.credential = credential
        self.timeout_seconds = timeout_seconds
        self.opener = build_opener(ProxyHandler(), HTTPSHandler(context=ssl.create_default_context()))

    def request(self, method: str, path: str, body: Dict[str, Any] | None = None) -> Dict[str, Any]:
        headers = {"Accept": "application/json"}
        data = None
        if self.credential:
            headers["Authorization"] = f"Bearer {self.credential}"
        if body is not None:
            data = json.dumps(body, allow_nan=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8") or "{}")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise ApiError(exc.code, detail) from exc
        except URLError as exc:
            raise ApiError(0, str(exc.reason)) from exc
