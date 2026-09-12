import platform
import uuid
from pathlib import Path
from typing import Any, Dict

from .credentials import CredentialStore
from .http import ApiClient
from .queue import new_queue_key


def platform_name() -> str:
    return "macOS" if platform.system() == "Darwin" else platform.system()


def perform_enrollment(data_dir: Path, server_url: str, token: str, topology: str = "enterprise_20n") -> Dict[str, Any]:
    server_url = server_url.strip().rstrip("/")
    if not server_url:
        raise ValueError("Backend URL is required")
    if not token:
        raise ValueError("Enrollment token is required")
    endpoint_id = str(uuid.uuid4())
    response = ApiClient(server_url).request(
        "POST",
        "/api/device-enrollment/exchange",
        {"enrollment_token": token, "endpoint_id": endpoint_id, "platform": platform_name()},
    )
    config = {
        "server_url": server_url,
        "endpoint_id": endpoint_id,
        "organization_id": response["organization_id"],
        "device_credential": response["device_credential"],
        "queue_key": new_queue_key(),
        "topology": topology,
    }
    CredentialStore(data_dir).save(config)
    return {key: config[key] for key in ("server_url", "endpoint_id", "organization_id", "topology")}
