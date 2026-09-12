"""Build double-click endpoint heartbeat bundles for a local Onyx demo."""

from __future__ import annotations

import argparse
import re
import shutil
import zipfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
OUTPUT_ROOT = SCRIPT_DIR / "dist"


def read_ingest_key() -> str:
    secrets_path = PROJECT_ROOT / ".onyx-secrets.cmd"
    content = secrets_path.read_text(encoding="ascii")
    match = re.search(r"^set ONYX_TELEMETRY_INGEST_API_KEY=(.+)$", content, re.MULTILINE)
    if not match:
        raise RuntimeError(f"Telemetry key was not found in {secrets_path}")
    return match.group(1).strip()


def add_zip_file(archive: zipfile.ZipFile, source: Path, archive_name: str, executable: bool) -> None:
    info = zipfile.ZipInfo.from_file(source, archive_name)
    info.create_system = 3
    info.external_attr = ((0o100755 if executable else 0o100644) << 16)
    with source.open("rb") as handle:
        archive.writestr(info, handle.read())


def build_windows(server_url: str, ingest_key: str, endpoint_id: str) -> Path:
    bundle_dir = OUTPUT_ROOT / "Onyx-Windows-Connect"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SCRIPT_DIR / "windows_heartbeat_agent.ps1", bundle_dir)
    launcher = bundle_dir / "Connect-Windows-Laptop.cmd"
    launcher.write_text(
        "@echo off\r\n"
        "title Onyx Windows Laptop Connection\r\n"
        "echo Connecting this laptop to Onyx...\r\n"
        f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows_heartbeat_agent.ps1" -ApiUrl "{server_url}" -ApiKey "{ingest_key}" -EndpointId "{endpoint_id}"\r\n'
        "echo.\r\n"
        "echo The Onyx connection stopped.\r\n"
        "pause\r\n",
        encoding="ascii",
        newline="",
    )
    zip_path = OUTPUT_ROOT / "Onyx-Windows-Connect.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        add_zip_file(archive, launcher, launcher.name, False)
        add_zip_file(
            archive,
            bundle_dir / "windows_heartbeat_agent.ps1",
            "windows_heartbeat_agent.ps1",
            False,
        )
    return zip_path


def build_server(ingest_key: str, endpoint_id: str) -> Path:
    bundle_dir = OUTPUT_ROOT / "Onyx-Server-Laptop-Connect"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SCRIPT_DIR / "windows_heartbeat_agent.ps1", bundle_dir)
    launcher = bundle_dir / "Connect-Server-Laptop.cmd"
    launcher.write_text(
        "@echo off\r\n"
        "title Onyx Server Laptop Connection\r\n"
        "echo Registering this server laptop with Onyx...\r\n"
        f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows_heartbeat_agent.ps1" -ApiUrl "http://127.0.0.1:8020" -ApiKey "{ingest_key}" -EndpointId "{endpoint_id}"\r\n'
        "echo.\r\n"
        "echo The Onyx server-laptop connection stopped.\r\n"
        "pause\r\n",
        encoding="ascii",
        newline="",
    )
    zip_path = OUTPUT_ROOT / "Onyx-Server-Laptop-Connect.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        add_zip_file(archive, launcher, launcher.name, False)
        add_zip_file(
            archive,
            bundle_dir / "windows_heartbeat_agent.ps1",
            "windows_heartbeat_agent.ps1",
            False,
        )
    return zip_path


def build_judges_virus_demo(server_url: str, ingest_key: str) -> Path:
    bundle_dir = OUTPUT_ROOT / "Onyx-Judges-Virus-Demo"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    agent = bundle_dir / "windows_live_endpoint_agent.ps1"
    shutil.copy2(SCRIPT_DIR / "windows_live_endpoint_agent.ps1", agent)
    launcher = bundle_dir / "Run-Virus-Laptop-Demo.cmd"
    launcher.write_text(
        "@echo off\r\n"
        "title Onyx Safe Virus-Laptop Demonstration\r\n"
        "color 0E\r\n"
        "echo ========================================================\r\n"
        "echo  ONYX SAFE SIMULATED ENDPOINT DETECTION\r\n"
        "echo  No malware or test file will be created.\r\n"
        "echo ========================================================\r\n"
        "echo.\r\n"
        "echo Registering virus-laptop and sending one rehearsal event...\r\n"
        f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows_live_endpoint_agent.ps1" -ApiUrl "{server_url}" -ApiKey "{ingest_key}" -EndpointId "virus-laptop" -Topology "enterprise_20n" -EmitSimulatedDetection\r\n'
        "if errorlevel 1 (\r\n"
        "  color 0C\r\n"
        "  echo DEMO FAILED. Check the server connection and API key.\r\n"
        ") else (\r\n"
        "  color 0A\r\n"
        "  echo.\r\n"
        "  echo SUCCESS: virus-laptop is now visible as an affected endpoint.\r\n"
        "  echo Refresh the Onyx Reality dashboard once.\r\n"
        ")\r\n"
        "echo.\r\n"
        "pause\r\n",
        encoding="ascii",
        newline="",
    )
    zip_path = OUTPUT_ROOT / "Onyx-Judges-Virus-Demo.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        add_zip_file(archive, launcher, launcher.name, False)
        add_zip_file(archive, agent, agent.name, False)
    return zip_path


def build_macos(server_url: str, ingest_key: str, endpoint_id: str) -> Path:
    bundle_dir = OUTPUT_ROOT / "Onyx-Mac-Connect-8020"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    agent = bundle_dir / "macos_heartbeat_agent.sh"
    shutil.copy2(SCRIPT_DIR / "macos_heartbeat_agent.sh", agent)
    launcher = bundle_dir / "Connect-Mac-8020.command"
    launcher.write_text(
        "#!/bin/zsh\n"
        'SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
        f"export ONYX_API_URL='{server_url}'\n"
        f"export ONYX_INGEST_API_KEY='{ingest_key}'\n"
        f"export ONYX_ENDPOINT_ID='{endpoint_id}'\n"
        'exec /bin/zsh "$SCRIPT_DIR/macos_heartbeat_agent.sh"\n',
        encoding="utf-8",
        newline="\n",
    )
    zip_path = OUTPUT_ROOT / "Onyx-Mac-Connect-8020.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        add_zip_file(archive, launcher, launcher.name, True)
        add_zip_file(archive, agent, agent.name, True)
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-url", default="http://192.168.1.12:8020")
    parser.add_argument("--windows-name", default="windows-laptop-demo")
    parser.add_argument("--mac-name", default="macbook-demo")
    parser.add_argument("--server-name", default="onyx-server-laptop")
    args = parser.parse_args()

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    ingest_key = read_ingest_key()
    windows_zip = build_windows(args.server_url.rstrip("/"), ingest_key, args.windows_name)
    mac_zip = build_macos(args.server_url.rstrip("/"), ingest_key, args.mac_name)
    server_zip = build_server(ingest_key, args.server_name)
    judges_zip = build_judges_virus_demo(args.server_url.rstrip("/"), ingest_key)
    print(f"Created {windows_zip}")
    print(f"Created {mac_zip}")
    print(f"Created {server_zip}")
    print(f"Created {judges_zip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
