"""Telemetry connector with config-driven fallback behavior.

This module keeps external access read-only and safe. If telemetry is disabled
or unavailable, callers can explicitly fallback to simulation.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from urllib import error, request

from src.integrations.telemetry_mapping import (
    build_attack_analysis_from_events,
    build_patch_results_from_events,
    normalize_events,
)
from web.backend.database import get_telemetry_events


@dataclass
class TelemetrySettings:
    enabled: bool = False
    endpoint: str = ""
    api_key_env: str = "TELEMETRY_API_KEY"
    request_timeout_seconds: float = 8.0
    cache_ttl_seconds: int = 3600
    fallback_to_simulation: bool = True


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_yaml_payload(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}

    try:
        import yaml  # type: ignore

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        # Keep connector resilient even when PyYAML is unavailable.
        return {}


def load_telemetry_settings(project_root: Path) -> TelemetrySettings:
    payload = _load_yaml_payload(project_root / "configs" / "config.yaml")
    telemetry = payload.get("telemetry", {}) if isinstance(payload, dict) else {}

    return TelemetrySettings(
        enabled=bool(telemetry.get("enabled", False)),
        endpoint=str(telemetry.get("endpoint", "") or "").strip(),
        api_key_env=str(telemetry.get("api_key_env", "TELEMETRY_API_KEY")),
        request_timeout_seconds=float(telemetry.get("request_timeout_seconds", 8)),
        cache_ttl_seconds=int(telemetry.get("cache_ttl_seconds", 3600)),
        fallback_to_simulation=bool(telemetry.get("fallback_to_simulation", True)),
    )


class TelemetryClient:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.settings = load_telemetry_settings(project_root)

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        api_key = os.getenv(self.settings.api_key_env)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _post_json(self, route: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.settings.enabled or not self.settings.endpoint:
            raise RuntimeError("telemetry_disabled")

        base = self.settings.endpoint.rstrip("/")
        route_path = route if route.startswith("/") else f"/{route}"
        url = f"{base}{route_path}"

        req = request.Request(
            url=url,
            method="POST",
            headers=self._headers(),
            data=json.dumps(payload).encode("utf-8"),
        )

        try:
            with request.urlopen(req, timeout=self.settings.request_timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except (error.URLError, error.HTTPError, TimeoutError) as exc:
            raise RuntimeError(f"telemetry_request_failed:{exc}") from exc

    def _load_local_events(self, topology_key: str) -> list[Dict[str, Any]]:
        events = get_telemetry_events(topology_key, 5000)
        return normalize_events(events, default_topology=topology_key)

    def fetch_attack_analysis(
        self,
        topology_key: str,
        n_episodes: int,
        seed: int,
    ) -> Dict[str, Any]:
        local_events = self._load_local_events(topology_key)
        if local_events:
            result = build_attack_analysis_from_events(local_events, n_episodes=n_episodes)
            result["data_source"] = "telemetry"
            result["telemetry_fetched_at"] = _utc_now_iso()
            result["telemetry_mode"] = "local_ingest"
            return result

        payload = {
            "topology": topology_key,
            "n_episodes": n_episodes,
            "seed": seed,
        }
        result = self._post_json("/attack-analysis", payload)
        result["data_source"] = "telemetry"
        result["telemetry_fetched_at"] = _utc_now_iso()
        return result

    def fetch_patch_results(
        self,
        topology_key: str,
        n_baseline: int,
        n_eval_per_patch: int,
    ) -> Dict[str, Any]:
        local_events = self._load_local_events(topology_key)
        if local_events:
            rows = build_patch_results_from_events(local_events)
            return {
                "results": rows,
                "data_source": "telemetry",
                "telemetry_fetched_at": _utc_now_iso(),
                "telemetry_mode": "local_ingest",
            }

        payload = {
            "topology": topology_key,
            "n_baseline": n_baseline,
            "n_eval_per_patch": n_eval_per_patch,
        }
        result = self._post_json("/patch-impact", payload)
        result["data_source"] = "telemetry"
        result["telemetry_fetched_at"] = _utc_now_iso()
        return result
