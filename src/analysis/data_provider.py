"""Data providers for simulation, telemetry, and hybrid attack analysis.

Phase 1 adds a stable abstraction boundary so API handlers can choose a
source without changing response shape. Telemetry mode currently falls back
to simulation and tags provenance for transparent judge demos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from src.analysis.attack_path_analyzer import analyze_attack_paths
from src.integrations.telemetry_client import TelemetryClient


logger = logging.getLogger(__name__)


class DataSource(str, Enum):
    SIMULATION = "simulation"
    TELEMETRY = "telemetry"
    HYBRID = "hybrid"


@dataclass
class ProviderContext:
    project_root: Path
    topology_path: str
    topology_key: str
    cve_path: str
    agent_path: Optional[str]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_data_source(value: Optional[str]) -> DataSource:
    if not value:
        return DataSource.SIMULATION

    cleaned = value.strip().lower()
    if cleaned in ("simulation", "sim"):
        return DataSource.SIMULATION
    if cleaned in ("telemetry", "real", "real-data", "real_data"):
        return DataSource.TELEMETRY
    if cleaned in ("hybrid", "mix", "blended"):
        return DataSource.HYBRID

    return DataSource.SIMULATION


class BaseDataProvider:
    source: DataSource

    def __init__(self, context: ProviderContext):
        self.context = context

    def run_attack_analysis(self, n_episodes: int, seed: int) -> Dict[str, Any]:
        raise NotImplementedError


class SimulationProvider(BaseDataProvider):
    source = DataSource.SIMULATION

    def run_attack_analysis(self, n_episodes: int, seed: int) -> Dict[str, Any]:
        result = analyze_attack_paths(
            topology_path=str(self.context.project_root / self.context.topology_path),
            cve_path=str(self.context.project_root / self.context.cve_path),
            agent_path=self.context.agent_path,
            n_episodes=n_episodes,
            seed=seed,
        )
        eval_runs = int(result.get("evaluation_runs") or result.get("n_episodes") or n_episodes)
        success_runs = int(result.get("successful_runs") or round(float(result.get("success_rate", 0.0)) * eval_runs))
        result["data_source"] = self.source.value
        result["data_source_note"] = "simulated_attack_paths"
        result["data_freshness_at"] = _utc_now_iso()
        result["confidence"] = result.get("confidence") or "estimated"
        result["evaluation_runs"] = eval_runs
        result["successful_runs"] = success_runs
        result["failed_runs"] = max(0, eval_runs - success_runs)
        return result


class TelemetryProvider(BaseDataProvider):
    source = DataSource.TELEMETRY

    def run_attack_analysis(self, n_episodes: int, seed: int) -> Dict[str, Any]:
        client = TelemetryClient(self.context.project_root)
        try:
            telemetry_result = client.fetch_attack_analysis(
                topology_key=self.context.topology_key,
                n_episodes=n_episodes,
                seed=seed,
            )
            telemetry_result["requested_data_source"] = self.source.value
            telemetry_result["data_source_note"] = "telemetry_attack_analysis"
            telemetry_result["data_freshness_at"] = telemetry_result.get("telemetry_fetched_at", _utc_now_iso())
            eval_runs = int(telemetry_result.get("evaluation_runs") or telemetry_result.get("n_episodes") or n_episodes)
            success_runs = int(telemetry_result.get("successful_runs") or round(float(telemetry_result.get("success_rate", 0.0)) * eval_runs))
            telemetry_result["confidence"] = telemetry_result.get("confidence") or "measured"
            telemetry_result["evaluation_runs"] = eval_runs
            telemetry_result["successful_runs"] = success_runs
            telemetry_result["failed_runs"] = max(0, eval_runs - success_runs)
            return telemetry_result
        except Exception as exc:
            logger.warning(
                "telemetry_fallback",
                extra={
                    "requested_source": self.source.value,
                    "topology": self.context.topology_key,
                    "reason": str(exc),
                },
            )
            sim = SimulationProvider(self.context).run_attack_analysis(n_episodes=n_episodes, seed=seed)
            sim["requested_data_source"] = self.source.value
            sim["data_source"] = DataSource.SIMULATION.value
            sim["data_source_note"] = f"telemetry_unavailable_fallback:{exc}"
            return sim


class HybridProvider(BaseDataProvider):
    source = DataSource.HYBRID

    def __init__(self, context: ProviderContext, telemetry_weight: float = 0.4):
        super().__init__(context)
        self.telemetry_weight = max(0.0, min(1.0, telemetry_weight))

    def run_attack_analysis(self, n_episodes: int, seed: int) -> Dict[str, Any]:
        sim = SimulationProvider(self.context).run_attack_analysis(n_episodes=n_episodes, seed=seed)
        client = TelemetryClient(self.context.project_root)

        telemetry_success_rate: Optional[float] = None
        telemetry_note = "telemetry_not_used"
        try:
            telemetry_result = client.fetch_attack_analysis(
                topology_key=self.context.topology_key,
                n_episodes=n_episodes,
                seed=seed,
            )
            telemetry_success_rate = telemetry_result.get("success_rate")
            telemetry_note = "telemetry_attack_analysis"
        except Exception as exc:
            logger.info(
                "hybrid_telemetry_unavailable",
                extra={
                    "requested_source": self.source.value,
                    "topology": self.context.topology_key,
                    "reason": str(exc),
                },
            )
            telemetry_note = f"telemetry_unavailable:{exc}"

        sim_rate = float(sim.get("success_rate", 0.0))
        if telemetry_success_rate is not None:
            blended_rate = (
                float(telemetry_success_rate) * self.telemetry_weight
                + sim_rate * (1.0 - self.telemetry_weight)
            )
            sim["success_rate"] = round(blended_rate, 4)

        eval_runs = int(sim.get("evaluation_runs") or sim.get("n_episodes") or n_episodes)
        success_runs = int(round(float(sim.get("success_rate", 0.0)) * eval_runs))
        sim["evaluation_runs"] = eval_runs
        sim["successful_runs"] = success_runs
        sim["failed_runs"] = max(0, eval_runs - success_runs)

        sim["requested_data_source"] = self.source.value
        sim["data_source"] = DataSource.HYBRID.value if telemetry_success_rate is not None else DataSource.SIMULATION.value
        sim["data_source_note"] = telemetry_note
        sim["data_freshness_at"] = _utc_now_iso()
        sim["confidence"] = "hybrid" if telemetry_success_rate is not None else sim.get("confidence", "estimated")
        sim["hybrid"] = {
            "telemetry_weight": round(self.telemetry_weight, 3),
            "simulation_weight": round(1.0 - self.telemetry_weight, 3),
            "telemetry_available": telemetry_success_rate is not None,
        }
        return sim


def build_data_provider(
    context: ProviderContext,
    data_source: Optional[str],
    telemetry_weight: float = 0.4,
) -> BaseDataProvider:
    source = normalize_data_source(data_source)
    if source == DataSource.TELEMETRY:
        return TelemetryProvider(context)
    if source == DataSource.HYBRID:
        return HybridProvider(context, telemetry_weight=telemetry_weight)
    return SimulationProvider(context)
