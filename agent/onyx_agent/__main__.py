import argparse
import getpass
import os
import platform
import subprocess
from pathlib import Path

from .credentials import CredentialStore
from .http import ApiClient, ApiError
from .queue import new_queue_key
from .runtime import AgentRunner
from .enrollment import perform_enrollment, platform_name
from .host import run_agent_host


def data_dir() -> Path:
    return Path(r"C:\ProgramData\Onyx" if platform.system() == "Windows" else "/Library/Application Support/Onyx")


def require_administrator() -> None:
    if platform.system() == "Windows":
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            raise PermissionError("Run enrollment from PowerShell opened with Run as administrator")
    elif platform.system() == "Darwin" and os.geteuid() != 0:
        raise PermissionError("Run enrollment with sudo")


def enroll(args: argparse.Namespace) -> int:
    require_administrator()
    server_url = (args.server_url or input("HTTPS backend URL: ").strip()).rstrip("/")
    if not server_url:
        raise ValueError("Backend URL is required")
    token = getpass.getpass("One-use enrollment token: ")
    try:
        response = perform_enrollment(data_dir(), server_url, token, args.topology)
    finally:
        token = ""  # Do not keep enrollment secrets after exchange.
    if platform.system() == "Windows":
        started = subprocess.run(["sc.exe", "start", "OnyxEndpointAgent"], capture_output=True, text=True)
        if started.returncode != 0 and "already running" not in (started.stdout + started.stderr).lower():
            print("Enrollment succeeded. Start the Onyx Endpoint Agent service from Services or reboot this laptop.")
    elif platform.system() == "Darwin":
        subprocess.run(["/bin/launchctl", "bootout", "system/com.onyx.endpoint-agent"], check=False, capture_output=True)
        loaded = subprocess.run(["/bin/launchctl", "bootstrap", "system", "/Library/LaunchDaemons/com.onyx.endpoint-agent.plist"], capture_output=True, text=True)
        if loaded.returncode != 0:
            raise RuntimeError(f"Enrollment succeeded but LaunchDaemon loading failed: {loaded.stderr.strip()}")
        subprocess.run(["/bin/launchctl", "kickstart", "-k", "system/com.onyx.endpoint-agent"], check=False, capture_output=True)
    print(f"Enrolled endpoint {response['endpoint_id']} in organization {response['organization_id']}")
    return 0


def status(_: argparse.Namespace) -> int:
    config = CredentialStore(data_dir()).load()
    if not config: print("Not enrolled"); return 1
    print(f"Enrolled: {config['endpoint_id']} ({config['organization_id']})")
    return 0


def run(args: argparse.Namespace) -> int:
    config = CredentialStore(data_dir()).load()
    if args.once:
        if not config: print("Agent is not enrolled", flush=True); return 2
        AgentRunner(config, data_dir()).run_once()
    else:
        run_agent_host(data_dir())
    return 0


def rotate(args: argparse.Namespace) -> int:
    store, config = CredentialStore(data_dir()), CredentialStore(data_dir()).load()
    if not config: print("Agent is not enrolled"); return 2
    response = ApiClient(config["server_url"], config["device_credential"]).request("POST", f"/api/devices/{config['endpoint_id']}/rotate-credential", {"reason": args.reason})
    config["device_credential"] = response["device_credential"]; store.save(config)
    print("Device credential rotated")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="onyx-agent")
    sub = parser.add_subparsers(required=True)
    enroll_p = sub.add_parser("enroll"); enroll_p.add_argument("--server-url"); enroll_p.add_argument("--topology", default="enterprise_20n"); enroll_p.set_defaults(func=enroll)
    status_p = sub.add_parser("status"); status_p.set_defaults(func=status)
    run_p = sub.add_parser("run"); run_p.add_argument("--once", action="store_true"); run_p.set_defaults(func=run)
    rotate_p = sub.add_parser("rotate-credential"); rotate_p.add_argument("--reason", default="administrator_requested"); rotate_p.set_defaults(func=rotate)
    if platform.system() == "Windows":
        service_p = sub.add_parser("service")
        service_p.set_defaults(func=lambda _: __import__("onyx_agent.windows_service", fromlist=["run_service"]).run_service() or 0)
    args = parser.parse_args()
    try: return args.func(args)
    except (ApiError, OSError, ValueError) as exc: print(f"Onyx Agent error: {exc}"); return 1


if __name__ == "__main__":
    raise SystemExit(main())
