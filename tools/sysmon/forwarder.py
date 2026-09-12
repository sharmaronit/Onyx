#!/usr/bin/env python3
"""Onyx Sysmon telemetry forwarder.

Reads Sysmon events from Windows Event Log and forwards normalized batches to
Onyx telemetry ingest endpoint.

Environment variables:
- ONYX_INGEST_URL: Required. Example: https://your-server/api/telemetry/ingest
- ONYX_INGEST_API_KEY: Optional bearer token value.
- ONYX_TOPOLOGY: Optional, default enterprise_20n
- ONYX_SOURCE: Optional, default sysmon_forwarder
- ONYX_SOURCE_NODE: Optional, default COMPUTERNAME
- ONYX_TARGET_NODE: Optional, default node_05_app
- ONYX_POLL_SECONDS: Optional, default 5
- ONYX_BATCH_SIZE: Optional, default 25
- ONYX_STATE_PATH: Optional, default tools/sysmon/forwarder_state.json
- ONYX_IP_NODE_MAP_PATH: Optional JSON file: {"10.0.0.5": "node_05_app"}
"""

from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests


AGENT_VERSION = "2.0.0"
EVENT_IDS = (1, 3, 11, 13)
DEFENDER_EVENT_IDS = (1116, 1117)
EVENT_TYPE_MAP = {
    1: "process_creation",
    3: "network_connect",
    11: "file_create",
    13: "registry_set",
}
@dataclass
class ForwarderConfig:
    ingest_url: str
    ingest_api_key: str
    topology: str
    source: str
    source_node: str
    default_target_node: str
    poll_seconds: int
    batch_size: int
    state_path: Path
    ip_node_map: Dict[str, str]
    protected_ports: List[int]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, fallback: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return fallback
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return fallback


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def build_config() -> ForwarderConfig:
    ingest_url = os.getenv("ONYX_INGEST_URL", "").strip()
    if not ingest_url:
        raise ValueError("ONYX_INGEST_URL is required")

    state_path = Path(os.getenv("ONYX_STATE_PATH", str(Path(__file__).with_name("forwarder_state.json"))))

    ip_map_path_raw = os.getenv("ONYX_IP_NODE_MAP_PATH", "").strip()
    ip_map = {}
    if ip_map_path_raw:
        ip_map = load_json(Path(ip_map_path_raw), {})

    return ForwarderConfig(
        ingest_url=ingest_url,
        ingest_api_key=os.getenv("ONYX_INGEST_API_KEY", "").strip(),
        topology=os.getenv("ONYX_TOPOLOGY", "enterprise_20n").strip(),
        source=os.getenv("ONYX_SOURCE", "sysmon_forwarder").strip(),
        source_node=os.getenv("ONYX_SOURCE_NODE", os.getenv("COMPUTERNAME", "unknown_vm")).strip(),
        default_target_node=os.getenv("ONYX_TARGET_NODE", "node_05_app").strip(),
        poll_seconds=max(1, int(os.getenv("ONYX_POLL_SECONDS", "5"))),
        batch_size=max(1, int(os.getenv("ONYX_BATCH_SIZE", "25"))),
        state_path=state_path,
        ip_node_map=ip_map,
        protected_ports=[
            int(port)
            for port in os.getenv(
                "ONYX_PROTECTED_PORTS", "22,80,443,445,3389,5432"
            ).split(",")
            if port.strip().isdigit() and 1 <= int(port) <= 65535
        ],
    )


def load_state(path: Path) -> Dict[str, Any]:
    state = load_json(
        path,
        {"last_record_id": 0, "last_defender_record_id": 0, "quarantined": False},
    )
    if "last_record_id" not in state:
        state["last_record_id"] = 0
    if "last_defender_record_id" not in state:
        state["last_defender_record_id"] = 0
    if "quarantined" not in state:
        state["quarantined"] = False
    return state


def to_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def get_sysmon_events() -> List[Dict[str, Any]]:
    ids_str = ",".join(str(v) for v in EVENT_IDS)
    ps_script = rf"""
$events = Get-WinEvent -LogName 'Microsoft-Windows-Sysmon/Operational' -FilterHashtable @{{ Id=@({ids_str}) }} -MaxEvents 200 |
    Sort-Object RecordId

$rows = @()
foreach ($evt in $events) {{
    $xml = [xml]$evt.ToXml()
    $data = @{{}}
    foreach ($entry in $xml.Event.EventData.Data) {{
        $name = $entry.Name
        if ([string]::IsNullOrWhiteSpace($name)) {{ $name = 'Value' }}
        $data[$name] = $entry.'#text'
    }}

    $rows += [pscustomobject]@{{
        RecordId = [int64]$evt.RecordId
        Id = [int]$evt.Id
        TimeCreated = $evt.TimeCreated.ToUniversalTime().ToString('o')
        Data = $data
    }}
}}

$rows | ConvertTo-Json -Depth 6
"""

    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "Failed to query Sysmon events")

    raw = completed.stdout.strip()
    if not raw:
        return []

    parsed = json.loads(raw)
    return to_list(parsed)


def get_defender_events() -> List[Dict[str, Any]]:
    ids_str = ",".join(str(value) for value in DEFENDER_EVENT_IDS)
    ps_script = rf"""
$events = Get-WinEvent -LogName 'Microsoft-Windows-Windows Defender/Operational' -FilterHashtable @{{ Id=@({ids_str}) }} -MaxEvents 100 |
    Sort-Object RecordId
$rows = @()
foreach ($evt in $events) {{
    $xml = [xml]$evt.ToXml()
    $data = @{{}}
    foreach ($entry in $xml.Event.EventData.Data) {{
        $name = $entry.Name
        if ([string]::IsNullOrWhiteSpace($name)) {{ $name = 'Value' }}
        $data[$name] = $entry.'#text'
    }}
    $rows += [pscustomobject]@{{
        RecordId = [int64]$evt.RecordId
        Id = [int]$evt.Id
        TimeCreated = $evt.TimeCreated.ToUniversalTime().ToString('o')
        Data = $data
        Message = $evt.Message
    }}
}}
$rows | ConvertTo-Json -Depth 6
"""
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip()
        if "No events were found" in message:
            return []
        raise RuntimeError(message or "Failed to query Microsoft Defender events")
    raw = completed.stdout.strip()
    return to_list(json.loads(raw)) if raw else []


def map_defender_event(cfg: ForwarderConfig, event: Dict[str, Any]) -> Dict[str, Any]:
    event_id = int(event.get("Id", 0))
    record_id = int(event.get("RecordId", 0))
    data = event.get("Data") or {}
    return {
        "event_id": f"defender-{record_id}-{event_id}",
        "timestamp": event.get("TimeCreated") or utc_now_iso(),
        "source_node": cfg.source_node,
        "target_node": cfg.source_node,
        "event_type": "malware_detected" if event_id == 1116 else "malware_remediated",
        "confidence": 1.0,
        "blocked": event_id == 1117,
        "reached_critical": False,
        "raw": {
            "provider": "Microsoft-Windows-Windows Defender",
            "windows_event_id": event_id,
            "record_id": record_id,
            "threat_name": data.get("Threat Name") or data.get("ThreatName"),
            "severity": data.get("Severity Name") or data.get("SeverityName"),
            "path": data.get("Path"),
            "action": data.get("Action Name") or data.get("ActionName"),
            "event_data": data,
            "message": event.get("Message"),
        },
    }


def map_event_to_onyx(cfg: ForwarderConfig, event: Dict[str, Any]) -> Dict[str, Any]:
    event_id = int(event.get("Id", 0))
    record_id = int(event.get("RecordId", 0))
    data = event.get("Data") or {}

    target_node = cfg.default_target_node
    if event_id == 3:
        dst_ip = str(data.get("DestinationIp") or "").strip()
        if dst_ip and dst_ip in cfg.ip_node_map:
            target_node = cfg.ip_node_map[dst_ip]

    timestamp = event.get("TimeCreated") or utc_now_iso()

    return {
        "event_id": f"sysmon-{record_id}-{event_id}",
        "timestamp": timestamp,
        "source_node": cfg.source_node,
        "target_node": target_node,
        "event_type": EVENT_TYPE_MAP.get(event_id, "sysmon_event"),
        "confidence": 1.0,
        "blocked": False,
        "reached_critical": False,
        "raw": {
            "event_id": event_id,
            "record_id": record_id,
            "event_data": data,
        },
    }


def post_events(cfg: ForwarderConfig, events: List[Dict[str, Any]]) -> requests.Response:
    payload = {
        "source": cfg.source,
        "topology": cfg.topology,
        "events": events,
    }
    headers = {"Content-Type": "application/json"}
    if cfg.ingest_api_key:
        headers["Authorization"] = f"Bearer {cfg.ingest_api_key}"

    return requests.post(cfg.ingest_url, json=payload, headers=headers, timeout=20)


def api_root(cfg: ForwarderConfig) -> str:
    suffix = "/telemetry/ingest"
    url = cfg.ingest_url.rstrip("/")
    if not url.endswith(suffix):
        raise ValueError("ONYX_INGEST_URL must end with /api/telemetry/ingest")
    return url[: -len(suffix)]


def agent_headers(cfg: ForwarderConfig) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if cfg.ingest_api_key:
        headers["Authorization"] = f"Bearer {cfg.ingest_api_key}"
    return headers


def local_ip_address() -> str:
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return ""


def post_heartbeat(
    cfg: ForwarderConfig,
    quarantined: bool,
    last_error: str = "",
) -> requests.Response:
    payload = {
        "endpoint_id": cfg.source_node,
        "hostname": os.getenv("COMPUTERNAME", socket.gethostname()),
        "ip_address": local_ip_address(),
        "topology": cfg.topology,
        "agent_version": AGENT_VERSION,
        "platform": platform.platform(),
        "quarantined": quarantined,
        "last_error": last_error or None,
        "metadata": {"protected_ports": cfg.protected_ports},
    }
    return requests.post(
        f"{api_root(cfg)}/endpoints/heartbeat",
        json=payload,
        headers=agent_headers(cfg),
        timeout=20,
    )


def get_pending_commands(cfg: ForwarderConfig) -> List[Dict[str, Any]]:
    response = requests.get(
        f"{api_root(cfg)}/endpoints/{cfg.source_node}/commands/pending",
        headers=agent_headers(cfg),
        timeout=20,
    )
    response.raise_for_status()
    return response.json().get("commands", [])


def apply_response_command(
    cfg: ForwarderConfig,
    command: Dict[str, Any],
) -> tuple[bool, Dict[str, Any], str]:
    action = command.get("action")
    requested_ports = command.get("parameters", {}).get("protected_ports") or cfg.protected_ports
    ports = sorted({int(port) for port in requested_ports if 1 <= int(port) <= 65535})
    group = "Onyx Endpoint Quarantine"

    if action == "quarantine":
        if not ports:
            return False, {}, "No protected ports were supplied"
        port_csv = ",".join(str(port) for port in ports)
        script = (
            f"Get-NetFirewallRule -Group '{group}' -ErrorAction SilentlyContinue | Remove-NetFirewallRule; "
            f"New-NetFirewallRule -DisplayName 'Onyx Quarantine Outbound' -Group '{group}' "
            f"-Direction Outbound -Action Block -Protocol TCP -RemotePort '{port_csv}' | Out-Null; "
            f"New-NetFirewallRule -DisplayName 'Onyx Quarantine Inbound' -Group '{group}' "
            f"-Direction Inbound -Action Block -Protocol TCP -LocalPort '{port_csv}' | Out-Null"
        )
        quarantined = True
    elif action == "restore":
        script = f"Get-NetFirewallRule -Group '{group}' -ErrorAction SilentlyContinue | Remove-NetFirewallRule"
        quarantined = False
    else:
        return False, {}, f"Unsupported response action: {action}"

    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        return False, {}, completed.stderr.strip() or "Firewall policy command failed"
    return True, {"protected_ports": ports, "firewall_group": group, "quarantined": quarantined}, ""


def acknowledge_command(
    cfg: ForwarderConfig,
    command: Dict[str, Any],
    succeeded: bool,
    result: Dict[str, Any],
    error_message: str,
    quarantined: bool,
) -> None:
    response = requests.post(
        f"{api_root(cfg)}/endpoints/{cfg.source_node}/commands/{command['command_id']}/ack",
        headers=agent_headers(cfg),
        json={
            "status": "succeeded" if succeeded else "failed",
            "quarantined": quarantined,
            "result": result,
            "error_message": error_message or None,
        },
        timeout=20,
    )
    response.raise_for_status()


def main() -> int:
    try:
        cfg = build_config()
    except Exception as exc:
        print(f"[ERROR] Config error: {exc}")
        return 1

    state = load_state(cfg.state_path)
    last_record_id = int(state.get("last_record_id", 0))
    last_defender_record_id = int(state.get("last_defender_record_id", 0))
    quarantined = bool(state.get("quarantined", False))

    print("Onyx Sysmon Forwarder")
    print(f"Ingest URL: {cfg.ingest_url}")
    print(f"Source Node: {cfg.source_node}")
    print(f"Topology: {cfg.topology}")
    print(f"Polling every {cfg.poll_seconds}s")
    print(f"State path: {cfg.state_path}")
    print(f"Protected service ports: {cfg.protected_ports}")

    while True:
        try:
            heartbeat = post_heartbeat(cfg, quarantined)
            heartbeat.raise_for_status()

            for command in get_pending_commands(cfg):
                succeeded, result, error_message = apply_response_command(cfg, command)
                if succeeded:
                    quarantined = bool(result.get("quarantined"))
                acknowledge_command(
                    cfg,
                    command,
                    succeeded,
                    result,
                    error_message,
                    quarantined,
                )
                print(
                    f"[RESPONSE] {command.get('action')} {command.get('command_id')}: "
                    f"{'succeeded' if succeeded else 'failed'}"
                )

            sysmon_events = get_sysmon_events()
            new_events = [evt for evt in sysmon_events if int(evt.get("RecordId", 0)) > last_record_id]
            new_events.sort(key=lambda e: int(e.get("RecordId", 0)))
            batches = [new_events[i:i + cfg.batch_size] for i in range(0, len(new_events), cfg.batch_size)]
            for batch in batches:
                mapped = [map_event_to_onyx(cfg, e) for e in batch]
                resp = post_events(cfg, mapped)
                resp.raise_for_status()
                batch_last = max(int(e.get("RecordId", 0)) for e in batch)
                last_record_id = max(last_record_id, batch_last)
                print(f"[OK] Sent {len(batch)} events. last_record_id={last_record_id}")

            try:
                defender_events = get_defender_events()
            except Exception as exc:
                defender_events = []
                print(f"[WARN] Microsoft Defender event query failed: {exc}")
            new_defender_events = [
                event
                for event in defender_events
                if int(event.get("RecordId", 0)) > last_defender_record_id
            ]
            new_defender_events.sort(key=lambda event: int(event.get("RecordId", 0)))
            for batch_start in range(0, len(new_defender_events), cfg.batch_size):
                batch = new_defender_events[batch_start : batch_start + cfg.batch_size]
                mapped = [map_defender_event(cfg, event) for event in batch]
                response = post_events(cfg, mapped)
                response.raise_for_status()
                last_defender_record_id = max(
                    last_defender_record_id,
                    max(int(event.get("RecordId", 0)) for event in batch),
                )
                print(
                    f"[DEFENDER] Sent {len(batch)} events. "
                    f"last_record_id={last_defender_record_id}"
                )

            save_json(
                cfg.state_path,
                {
                    "last_record_id": last_record_id,
                    "last_defender_record_id": last_defender_record_id,
                    "quarantined": quarantined,
                    "updated_at": utc_now_iso(),
                },
            )
            time.sleep(cfg.poll_seconds)

        except KeyboardInterrupt:
            print("\nStopping forwarder.")
            return 0
        except Exception as exc:
            print(f"[WARN] {exc}")
            try:
                post_heartbeat(cfg, quarantined, str(exc)[:1000])
            except Exception:
                pass
            time.sleep(cfg.poll_seconds)


if __name__ == "__main__":
    sys.exit(main())
