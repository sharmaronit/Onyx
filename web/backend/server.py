from __future__ import annotations

import hmac
import hashlib
import csv
import io
import json
import logging
import os
import subprocess
import statistics
import sys
import secrets

import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .database import (
    claim_pending_commands,
    authenticate_device,
    consume_enrollment_token,
    clear_notifications,
    complete_response_command,
    create_incident,
    create_notification,
    create_response_command,
    create_remediation_action,
    create_training_job,
    get_active_cost_model,
    get_cost_models,
    get_endpoint,
    get_authenticated_device,
    get_metrics,
    get_request_logs,
    get_remediation_action,
    get_scenario_history,
    get_simulation_run,
    list_vulnerability_findings,
    get_telemetry_events,
    get_training_job,
    get_user_preference,
    init_db,
    list_endpoints,
    list_notifications,
    list_simulation_runs,
    list_relationships,
    list_open_incidents,
    list_response_commands,
    list_remediation_actions,
    log_request,
    log_scenario_execution,
    save_cost_model,
    save_enrollment_token,
    save_simulation_run,
    set_server_link,
    server_link_disconnected,
    mark_notifications_read,
    resolve_incident,
    set_user_preference,
    revoke_device,
    rotate_device_credential,
    record_agent_batch,
    record_agent_audit,
    store_telemetry_events,
    update_training_job,
    update_remediation_action,
    upsert_endpoint_heartbeat,
    upsert_relationship,
    upsert_vulnerability_findings,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.data_provider import ProviderContext, build_data_provider
from src.analysis.cost_optimizer import rank_cost_aware_patches
from src.analysis.explainability import build_explanation_cards
from src.analysis.patch_optimizer import compute_patch_impact, save_results
from src.analysis.report_generator import generate_report
from src.graph.topology_loader import load_topology
from src.graph.cve_tagger import load_cve_database, tag_graph
from src.integrations.telemetry_mapping import normalize_events
from src.integrations.telemetry_client import TelemetryClient

TOPOLOGIES = {
    "enterprise_20n": "data/topologies/enterprise_20n.json",
    "small_office_10n": "data/topologies/small_office_10n.json",
    "cloud_hybrid_30n": "data/topologies/cloud_hybrid_30n.json",
}
CVE_PATH = "data/cve/cve_dataset.json"
AGENT_PATH = "checkpoints/red_agent.zip"
MARL_RESULTS_PATH = "checkpoints/marl/marl_results.json"
PATCH_RESULTS_PATH = "reports/patch_analysis.json"
REPORT_HTML_PATH = "reports/morning_report.html"
REPORT_PDF_PATH = "reports/morning_report.pdf"
SCENARIO_CONFIG_PATH = "configs/demo_scenarios.json"
COST_MODEL_PATH = "configs/cost_model.json"

app = FastAPI(title="Onyx Web API", version="1.0.0")
logger = logging.getLogger("onyx.api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5183",
        "http://127.0.0.1:5183",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-User-ID"],
)


@app.middleware("http")
async def log_request_middleware(request: Request, call_next):
    """Log all incoming requests with timing and status."""
    start_time = time.time()
    user_id = request.query_params.get("user_id") or request.headers.get("X-User-ID")
    
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000  # Convert to ms
        
        log_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            response_time_ms=process_time,
            user_id=user_id,
        )
        return response
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        log_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=500,
            response_time_ms=process_time,
            user_id=user_id,
            error_message=str(e),
        )
        raise


@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    init_db()

cache: Dict[str, Any] = {
    "sim_results": None,
    "patch_results": None,
    "last_replay": None,
    "cost_ranking": None,
    "explainability": None,
    "sim_results_by_mode": {},
    "last_replay_by_mode": {},
    "patch_results_by_mode": {},
}


def _scoped_cache_key(mode: str, topology: str) -> str:
    """Keep demo/reality and topology inputs from sharing mutable cache entries."""
    return f"{mode}:{topology}"


def _invalidate_reality_cache(topology: str) -> None:
    cache["sim_results"] = None
    cache["patch_results"] = None
    cache["last_replay"] = None
    scoped_key = _scoped_cache_key("reality", topology)
    cache["sim_results_by_mode"].pop(scoped_key, None)
    cache["patch_results_by_mode"].pop(scoped_key, None)
    cache["last_replay_by_mode"].pop(scoped_key, None)


class SimulationRequest(BaseModel):
    topology: str = Field(default="enterprise_20n")
    n_episodes: int = Field(default=1000, ge=100, le=10000)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)
    data_source: str = Field(default="simulation")
    telemetry_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    mode: Literal["reality", "demo"] = "reality"


class SimulationSeedSweepRequest(BaseModel):
    topology: str = Field(default="enterprise_20n")
    n_episodes: int = Field(default=700, ge=100, le=10000)
    seeds: List[int] = Field(default_factory=lambda: [11, 21, 42, 73, 101])
    data_source: str = Field(default="simulation")
    telemetry_weight: float = Field(default=0.4, ge=0.0, le=1.0)


class PatchRequest(BaseModel):
    topology: str = Field(default="enterprise_20n")
    n_baseline: int = Field(default=200, ge=50, le=2000)
    n_eval_per_patch: int = Field(default=50, ge=10, le=500)
    data_source: str = Field(default="simulation")
    telemetry_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    mode: Literal["reality", "demo"] = "reality"


class ReportRequest(BaseModel):
    topology: str = Field(default="enterprise_20n")


class ScenarioRunRequest(BaseModel):
    n_episodes: int = Field(default=700, ge=100, le=5000)
    data_source: str = Field(default="simulation")
    telemetry_weight: float = Field(default=0.4, ge=0.0, le=1.0)


class ScorecardRequest(BaseModel):
    topology: str = Field(default="enterprise_20n")
    n_episodes: int = Field(default=700, ge=100, le=5000)
    top_k_patches: int = Field(default=3, ge=1, le=10)
    data_source: str = Field(default="simulation")
    telemetry_weight: float = Field(default=0.4, ge=0.0, le=1.0)


class CostRankingRequest(BaseModel):
    topology: str = Field(default="enterprise_20n")
    top_k: int = Field(default=12, ge=3, le=40)


class ExplainabilityRequest(BaseModel):
    topology: str = Field(default="enterprise_20n")
    top_n: int = Field(default=5, ge=3, le=12)


class EvidenceBundleRequest(BaseModel):
    topology: str = Field(default="enterprise_20n")
    n_episodes: int = Field(default=700, ge=100, le=5000)
    n_baseline: int = Field(default=200, ge=50, le=2000)
    n_eval_per_patch: int = Field(default=50, ge=10, le=500)
    telemetry_weight: float = Field(default=0.6, ge=0.0, le=1.0)
    top_k_patches: int = Field(default=3, ge=1, le=10)
    comparison_source: Optional[str] = Field(default=None)


class UserPreferenceRequest(BaseModel):
    user_id: str
    default_topology: Optional[str] = None
    default_episodes: Optional[int] = None
    cost_model: Optional[Dict[str, Any]] = None


class CostModelRequest(BaseModel):
    user_id: str
    model_name: str
    config: Dict[str, Any]
    is_active: bool = False


class ScenarioBuilderRequest(BaseModel):
    scenario_name: str
    topology: str
    description: str
    seed: int = 42
    entry_points: List[str] = []
    target_nodes: List[str] = []


class TrainingJobRequest(BaseModel):
    model_type: str = Field(..., description="gnn, red_agent, or blue_agent")
    config: Dict[str, Any] = {}
    priority: str = "normal"


class TelemetryEventRequest(BaseModel):
    event_id: Optional[str] = None
    timestamp: Optional[str] = None
    source_node: Optional[str] = None
    target_node: Optional[str] = None
    event_type: Optional[str] = None
    cve_id: Optional[str] = None
    cvss_score: Optional[float] = None
    confidence: Optional[float] = None
    blocked: Optional[bool] = None
    reached_critical: Optional[bool] = None
    raw: Optional[Dict[str, Any]] = None


class TelemetryIngestRequest(BaseModel):
    source: str = Field(default="scanner_export")
    topology: str = Field(default="enterprise_20n")
    events: List[TelemetryEventRequest] = Field(default_factory=list)


class VulnerabilityFindingRequest(BaseModel):
    endpoint_id: str = Field(min_length=1, max_length=128)
    finding_id: str = Field(min_length=1, max_length=255)
    cve_id: Optional[str] = Field(default=None, max_length=64)
    title: str = Field(min_length=1, max_length=500)
    cvss_score: float = Field(ge=0.0, le=10.0)
    software: Optional[str] = Field(default=None, max_length=255)
    software_version: Optional[str] = Field(default=None, max_length=128)
    fix_available: bool = False
    effort_hours: Optional[float] = Field(default=None, ge=0.1, le=500)
    source: str = Field(default="vulnerability_scanner", max_length=128)
    observed_at: Optional[str] = None
    status: Literal["open", "resolved", "accepted_risk"] = "open"
    evidence: Dict[str, Any] = Field(default_factory=dict)


class VulnerabilityIngestRequest(BaseModel):
    topology: str = Field(default="enterprise_20n")
    findings: List[VulnerabilityFindingRequest] = Field(default_factory=list)


class LiveTelemetryIngestRequest(BaseModel):
    topology: str = Field(default="enterprise_20n")
    mode: str = Field(default="pure", pattern="^(pure|enriched)$")
    max_connections: int = Field(default=20, ge=1, le=200)
    max_processes: int = Field(default=20, ge=1, le=200)


class EndpointHeartbeatRequest(BaseModel):
    endpoint_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")
    hostname: str = Field(min_length=1, max_length=255)
    ip_address: Optional[str] = Field(default=None, max_length=64)
    topology: str = Field(default="enterprise_20n")
    agent_version: str = Field(min_length=1, max_length=32)
    platform: Optional[str] = Field(default=None, max_length=255)
    quarantined: bool = False
    last_error: Optional[str] = Field(default=None, max_length=1000)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResponseCommandRequest(BaseModel):
    action: Literal["quarantine", "restore"]
    reason: str = Field(min_length=3, max_length=500)
    requested_by: str = Field(min_length=1, max_length=128)
    protected_ports: List[int] = Field(
        default_factory=lambda: [22, 80, 443, 445, 3389, 5432],
        max_length=32,
    )


class ResponseCommandAckRequest(BaseModel):
    status: Literal["succeeded", "failed"]
    quarantined: bool
    result: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = Field(default=None, max_length=2000)


class IncidentResolutionRequest(BaseModel):
    resolved_by: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=3, max_length=500)


class ServerLinkRequest(BaseModel):
    disconnected: bool
    requested_by: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=3, max_length=500)


class CostModelUpdateRequest(BaseModel):
    node_type_effort_hours: Dict[str, float]
    critical_asset_multiplier: float = Field(ge=0.1, le=10.0)


REMEDIATION_STATES = Literal[
    "proposed", "accepted", "in_progress", "contained", "awaiting_verification",
    "verified", "exception", "closed", "reopened",
]


class RemediationActionCreateRequest(BaseModel):
    finding_id: str = Field(min_length=1, max_length=255)
    endpoint_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=500)
    recommendation: str = Field(min_length=1, max_length=2000)
    owner: str = Field(min_length=1, max_length=255)
    due_date: Optional[str] = None
    priority: Literal["low", "medium", "high", "critical"] = "medium"


class RemediationActionUpdateRequest(BaseModel):
    state: REMEDIATION_STATES
    owner: Optional[str] = Field(default=None, min_length=1, max_length=255)
    due_date: Optional[str] = None
    verification: Optional[Dict[str, Any]] = None
    exception: Optional[Dict[str, Any]] = None


class EnrollmentTokenRequest(BaseModel):
    allowed_platform: Optional[str] = Field(default="Windows", max_length=64)
    expires_in_minutes: int = Field(default=15, ge=1, le=1440)


class DeviceEnrollmentRequest(BaseModel):
    enrollment_token: str = Field(min_length=32, max_length=512)
    endpoint_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")
    platform: Optional[str] = Field(default="Windows", max_length=64)


class DeviceTelemetryBatchRequest(BaseModel):
    batch_id: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")
    topology: str = Field(default="enterprise_20n")
    events: List[TelemetryEventRequest] = Field(min_length=1, max_length=100)


class DeviceCredentialRotateRequest(BaseModel):
    reason: str = Field(default="administrator_requested", min_length=3, max_length=256)


def _resolve_topology(topology_key: str) -> str:
    if topology_key not in TOPOLOGIES:
        raise HTTPException(status_code=400, detail=f"Unknown topology: {topology_key}")
    return TOPOLOGIES[topology_key]


def _load_scenarios() -> List[dict]:
    path = PROJECT_ROOT / SCENARIO_CONFIG_PATH
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict):
            return payload.get("scenarios", []) or []
        if isinstance(payload, list):
            return payload
    except Exception as exc:
        logger.warning("Failed to load scenarios from %s: %s", path, exc)
    return []


def _load_json_array(path: Path) -> List[dict]:
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            return payload.get("results", []) or []
    except Exception as exc:
        logger.warning("Failed to load json array from %s: %s", path, exc)
    return []


def _build_result_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    success_rate = float(result.get("success_rate") or 0.0)
    success_percent = round(success_rate * 100.0, 2)
    episodes = int(result.get("n_episodes") or result.get("evaluation_runs") or 0)
    successful_runs = int(result.get("successful_runs") or round(success_rate * max(1, episodes)))
    attack_paths = int(result.get("total_unique_paths") or len(result.get("top_paths") or []))
    source = result.get("data_source") or result.get("requested_data_source") or "simulation"
    confidence = _confidence_from_source(source if source in ("simulation", "telemetry", "hybrid") else result.get("confidence"))
    risk_band = "high" if success_percent >= 60 else "moderate" if success_percent >= 25 else "low"

    takeaway = f"Risk is {risk_band}: {success_percent:.2f}% attack success across {episodes} episodes."
    bullets = [
        f"{attack_paths} distinct attack path{'s' if attack_paths != 1 else ''} identified.",
        f"{successful_runs} of {max(episodes, 1)} runs reached attacker success.",
        f"{_source_label(source)} source with {confidence} confidence.",
    ]

    return {
        "takeaway": takeaway,
        "bullets": bullets,
        "source": _source_label(source),
        "confidence": confidence,
        "success_rate_percent": success_percent,
        "episodes": episodes,
        "attack_paths": attack_paths,
        "successful_runs": successful_runs,
        "note": result.get("data_source_note") or None,
    }


def _source_label(source: Optional[str]) -> str:
    normalized = (source or "simulation").lower()
    if normalized == "telemetry":
        return "Telemetry"
    if normalized == "hybrid":
        return "Hybrid"
    if normalized == "cache":
        return "Cache"
    return "Simulation"


def _run_attack_analysis(
    topology_path: str,
    topology_key: str,
    n_episodes: int,
    seed: int,
    data_source: str = "simulation",
    telemetry_weight: float = 0.4,
) -> dict:
    agent_path = str(PROJECT_ROOT / AGENT_PATH)
    if not Path(agent_path).exists():
        agent_path = None

    provider = build_data_provider(
        context=ProviderContext(
            project_root=PROJECT_ROOT,
            topology_path=topology_path,
            topology_key=topology_key,
            cve_path=CVE_PATH,
            agent_path=agent_path,
        ),
        data_source=data_source,
        telemetry_weight=telemetry_weight,
    )
    return provider.run_attack_analysis(n_episodes=n_episodes, seed=seed)


def _run_seed_sweep(
    topology_path: str,
    topology_key: str,
    n_episodes: int,
    seeds: List[int],
    data_source: str,
    telemetry_weight: float,
) -> Dict[str, Any]:
    runs: List[Dict[str, Any]] = []

    for seed in seeds:
        result = _run_attack_analysis(
            topology_path=topology_path,
            topology_key=topology_key,
            n_episodes=n_episodes,
            seed=seed,
            data_source=data_source,
            telemetry_weight=telemetry_weight,
        )
        rate = float(result.get("success_rate") or 0.0)
        evaluation_runs = int(result.get("evaluation_runs") or result.get("n_episodes") or n_episodes)
        success_runs = int(result.get("successful_runs") or round(rate * evaluation_runs))
        path_count = int(result.get("total_unique_paths") or len(result.get("top_paths") or []))
        top_path = (result.get("top_paths") or [{}])[0].get("path") if path_count else None

        runs.append(
            {
                "seed": int(seed),
                "success_rate": round(rate, 4),
                "successful_runs": success_runs,
                "failed_runs": max(0, evaluation_runs - success_runs),
                "evaluation_runs": evaluation_runs,
                "path_count": path_count,
                "top_path": top_path,
                "confidence": result.get("confidence") or _confidence_from_source(result.get("data_source")),
                "data_source": result.get("data_source") or result.get("requested_data_source") or data_source,
                "data_freshness_at": result.get("data_freshness_at"),
            }
        )

    rates = [float(item.get("success_rate") or 0.0) for item in runs]
    success_runs_all = [int(item.get("successful_runs") or 0) for item in runs]
    eval_runs_all = [int(item.get("evaluation_runs") or 0) for item in runs]

    mean_rate = (sum(rates) / len(rates)) if rates else 0.0
    min_rate = min(rates) if rates else 0.0
    max_rate = max(rates) if rates else 0.0
    std_dev = statistics.pstdev(rates) if len(rates) > 1 else 0.0

    summary = {
        "seed_count": len(runs),
        "mean_success_rate": round(mean_rate, 4),
        "min_success_rate": round(min_rate, 4),
        "max_success_rate": round(max_rate, 4),
        "std_dev_success_rate": round(std_dev, 4),
        "spread_pp": round((max_rate - min_rate) * 100.0, 2),
        "mean_successful_runs": round((sum(success_runs_all) / len(success_runs_all)) if success_runs_all else 0.0, 2),
        "mean_evaluation_runs": round((sum(eval_runs_all) / len(eval_runs_all)) if eval_runs_all else 0.0, 2),
    }

    return {
        "topology": topology_key,
        "n_episodes": n_episodes,
        "requested_data_source": data_source,
        "telemetry_weight": telemetry_weight,
        "seeds": [int(seed) for seed in seeds],
        "summary": summary,
        "runs": runs,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def _estimate_patch_results(topology_path: str, baseline_success_rate: float = 0.85) -> List[dict]:
    graph = load_topology(str(PROJECT_ROOT / topology_path))
    cve_db = load_cve_database(str(PROJECT_ROOT / CVE_PATH))
    tag_graph(graph, cve_db)

    rows: List[dict] = []
    for node in graph.nodes:
        for cve in node.vulnerabilities:
            impact = (float(cve.cvss_score) / 10.0) * 0.12
            if node.is_critical_asset:
                impact += 0.03
            patched = max(0.0, baseline_success_rate - impact)
            rows.append(
                {
                    "node_id": node.node_id,
                    "cve_id": cve.cve_id,
                    "node_type": node.node_type,
                    "is_critical_asset": node.is_critical_asset,
                    "cvss_score": cve.cvss_score,
                    "cvss_severity": cve.severity_label,
                    "attack_vector": cve.attack_vector,
                    "baseline_success_rate": round(baseline_success_rate, 4),
                    "patched_success_rate": round(patched, 4),
                    "simulation_impact": round(max(0.0, baseline_success_rate - patched), 4),
                    "simulation_rank": None,
                    "cvss_rank": None,
                    "description": (cve.description or "")[:120],
                }
            )

    rows.sort(key=lambda x: -x["simulation_impact"])
    for index, row in enumerate(rows):
        row["simulation_rank"] = index + 1

    cvss_sorted = sorted(rows, key=lambda x: -x["cvss_score"])
    for index, row in enumerate(cvss_sorted):
        row["cvss_rank"] = index + 1

    rows.sort(key=lambda x: -x["simulation_impact"])
    return rows


def _build_estimated_patch_payload(
    topology_path: str,
    topology_key: str,
    requested_data_source: str,
    telemetry_weight: float,
    note_prefix: str,
) -> dict:
    baseline_success_rate = 0.85
    baseline_source = "default_baseline"

    try:
        sim_result = cache.get("sim_results") or _run_attack_analysis(
            topology_path=topology_path,
            topology_key=topology_key,
            n_episodes=700,
            seed=42,
            data_source="simulation",
            telemetry_weight=telemetry_weight,
        )
        baseline_success_rate = float(sim_result.get("success_rate", baseline_success_rate) or baseline_success_rate)
        baseline_source = "simulation_baseline"
    except Exception as exc:
        logger.warning(
            "patch_baseline_fallback_default",
            extra={
                "topology": topology_key,
                "requested_source": requested_data_source,
                "reason": str(exc),
            },
        )

    rows = _estimate_patch_results(topology_path=topology_path, baseline_success_rate=baseline_success_rate)
    return {
        "results": rows,
        "data_source": "simulation",
        "requested_data_source": requested_data_source,
        "data_source_note": f"{note_prefix}:{baseline_source}",
        "data_freshness_at": datetime.utcnow().isoformat() + "Z",
        "confidence": "estimated",
    }


def _generate_patch_results(
    topology_key: str,
    n_baseline: int = 200,
    n_eval_per_patch: int = 50,
    data_source: str = "simulation",
    telemetry_weight: float = 0.4,
) -> dict:
    topology_path = _resolve_topology(topology_key)

    telemetry_client = TelemetryClient(PROJECT_ROOT)
    if data_source in ("telemetry", "hybrid"):
        try:
            telemetry_payload = telemetry_client.fetch_patch_results(
                topology_key=topology_key,
                n_baseline=n_baseline,
                n_eval_per_patch=n_eval_per_patch,
            )
            rows = telemetry_payload.get("results") or telemetry_payload.get("patches") or []
            if rows:
                return {
                    "results": rows,
                    "data_source": "telemetry",
                    "requested_data_source": data_source,
                    "data_source_note": "telemetry_patch_results",
                    "data_freshness_at": telemetry_payload.get("telemetry_fetched_at"),
                    "confidence": "measured",
                }
        except Exception as exc:
            logger.warning(
                "patch_results_telemetry_fallback",
                extra={
                    "topology": topology_key,
                    "requested_source": data_source,
                    "reason": str(exc),
                },
            )
            if data_source == "telemetry":
                data_source = "simulation"

    agent_path = PROJECT_ROOT / AGENT_PATH
    if agent_path.exists():
        try:
            logger.info(
                "patch_results_generated",
                extra={
                    "topology": topology_key,
                    "source": "simulation",
                    "mode": "optimizer",
                },
            )
            rows = compute_patch_impact(
                topology_path=str(PROJECT_ROOT / topology_path),
                cve_path=str(PROJECT_ROOT / CVE_PATH),
                agent_path=str(agent_path),
                n_baseline=n_baseline,
                n_eval_per_patch=n_eval_per_patch,
                seed=42,
                verbose=False,
            )
            save_results(rows, str(PROJECT_ROOT / PATCH_RESULTS_PATH))
            return {
                "results": rows,
                "data_source": "simulation",
                "requested_data_source": data_source,
                "data_source_note": "computed_from_patch_optimizer",
                "data_freshness_at": datetime.utcnow().isoformat() + "Z",
                "confidence": "estimated",
            }
        except Exception as exc:
            logger.warning(
                "patch_results_optimizer_fallback",
                extra={
                    "topology": topology_key,
                    "requested_source": data_source,
                    "reason": str(exc),
                },
            )
            return _build_estimated_patch_payload(
                topology_path=topology_path,
                topology_key=topology_key,
                requested_data_source=data_source,
                telemetry_weight=telemetry_weight,
                note_prefix="estimated_after_optimizer_failure",
            )

    logger.info(
        "patch_results_generated",
        extra={
            "topology": topology_key,
            "source": "simulation",
            "mode": "estimated",
        },
    )
    return _build_estimated_patch_payload(
        topology_path=topology_path,
        topology_key=topology_key,
        requested_data_source=data_source,
        telemetry_weight=telemetry_weight,
        note_prefix="estimated_without_trained_red_agent",
    )


def _build_replay(result: dict, topology_key: str) -> dict:
    topology_path = _resolve_topology(topology_key)
    graph = load_topology(str(PROJECT_ROOT / topology_path))
    cve_db = load_cve_database(str(PROJECT_ROOT / CVE_PATH))
    tag_graph(graph, cve_db)

    def parse_path(value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(node).strip() for node in value if str(node).strip()]
        text = str(value or "")
        separator = "→" if "→" in text else "->" if "->" in text else ","
        return [segment.strip() for segment in text.split(separator) if segment.strip()]

    path_rows = result.get("top_paths") or []
    top_path_row = path_rows[0] if path_rows else {}
    ordered_nodes = parse_path(top_path_row.get("path"))
    for candidate in path_rows:
        candidate_nodes = parse_path(candidate.get("path"))
        if candidate_nodes and candidate_nodes[-1] in graph.critical_assets:
            top_path_row = candidate
            ordered_nodes = candidate_nodes
            break

    reaches_critical_asset = bool(ordered_nodes and ordered_nodes[-1] in graph.critical_assets)

    steps = []
    for idx, node_id in enumerate(ordered_nodes):
        if node_id not in graph.node_ids:
            continue

        node = graph.get_node(node_id)
        entry = {
            "step": idx + 1,
            "node_id": node_id,
            "node_type": node.node_type,
            "software": node.software,
            "version": node.version,
            "num_vulns": node.num_vulns,
            "max_cvss": round(node.max_cvss, 1),
            "compromise_probability": round(node.compromise_probability, 3),
            "is_critical_asset": node.is_critical_asset,
            "is_entry_point": node.is_entry_point,
            "edge": None,
        }
        if idx > 0:
            prev = ordered_nodes[idx - 1]
            if prev in graph.node_ids:
                edge = graph.get_edge(prev, node_id)
                if edge:
                    entry["edge"] = {
                        "source": edge.source,
                        "target": edge.target,
                        "connection_type": edge.connection_type,
                        "permission_level": edge.permission_level,
                        "has_firewall": edge.has_firewall,
                    }
        steps.append(entry)

    return {
        "topology": topology_key,
        "path": ordered_nodes,
        "steps": steps,
        "success_rate": float(result.get("success_rate") or 0.0),
        "n_episodes": int(result.get("n_episodes") or result.get("evaluation_runs") or 0),
        "successful_runs": int(result.get("successful_runs") or 0),
        "failed_runs": int(result.get("failed_runs") or 0),
        "total_unique_paths": int(result.get("total_unique_paths") or 0),
        "selected_path_count": int(top_path_row.get("count") or 0),
        "selected_path_frequency": float(top_path_row.get("frequency") or 0.0),
        "reaches_critical_asset": reaches_critical_asset,
        "data_source": result.get("data_source") or result.get("requested_data_source") or "simulation",
        "requested_data_source": result.get("requested_data_source") or result.get("data_source") or "simulation",
        "data_source_note": result.get("data_source_note"),
        "confidence": result.get("confidence") or _confidence_from_source(result.get("data_source")),
        "analysis_engine": result.get("policy_engine") or (
            "telemetry_events" if result.get("data_source") == "telemetry" else "rule_based"
        ),
        "generated_at": result.get("data_freshness_at") or (datetime.now(timezone.utc).isoformat()),
    }


def _build_world_model_evidence(result: dict, topology_key: str, requested_episodes: int, seed: int) -> dict:
    """Describe the exact offline inputs behind a simulation run.

    This is deliberately built from the frozen topology and simulation result only.
    It makes it explicit that no endpoint telemetry, network traffic, or response
    command was used to execute the attack model.
    """
    topology_path = PROJECT_ROOT / _resolve_topology(topology_key)
    graph = load_topology(str(topology_path))
    cve_db = load_cve_database(str(PROJECT_ROOT / CVE_PATH))
    tag_graph(graph, cve_db)
    actual_runs = int(result.get("evaluation_runs") or result.get("n_episodes") or 0)
    successful_runs = int(result.get("successful_runs") or 0)
    return {
        "kind": "world_model_simulation",
        "safety": "Offline world-model simulation. It sends no packets and runs no commands on real endpoints.",
        "topology": {
            "key": topology_key,
            "snapshot_sha256": hashlib.sha256(topology_path.read_bytes()).hexdigest()[:16],
            "nodes": graph.num_nodes,
            "edges": len(graph.edges),
            "critical_assets": len(graph.critical_assets),
            "tagged_cves": int(sum(node.num_vulns for node in graph.nodes)),
        },
        "model": {
            "engine": result.get("policy_engine") or "rule_based",
            "checkpoint_present": (PROJECT_ROOT / AGENT_PATH).exists(),
            "seed": seed,
        },
        "execution": {
            "requested_episodes": requested_episodes,
            "completed_episodes": actual_runs,
            "successful_runs": successful_runs,
            "failed_runs": int(result.get("failed_runs") or max(0, actual_runs - successful_runs)),
            "unique_paths": int(result.get("total_unique_paths") or len(result.get("top_paths") or [])),
        },
        "reproduce": f"Run topology {topology_key} with seed {seed} and {requested_episodes} episodes.",
    }


def _patched_estimate(
    baseline_success_rate: float,
    top_k_patches: int,
    patch_results: List[dict],
) -> dict:
    if not patch_results:
        return {
            "patched_success_rate": baseline_success_rate,
            "risk_reduction_pp": 0.0,
            "top_actions": [],
        }

    chosen = sorted(patch_results, key=lambda x: -(x.get("simulation_impact") or 0.0))[:top_k_patches]
    estimated_delta = sum(max(0.0, x.get("simulation_impact", 0.0)) for x in chosen)
    patched_rate = max(0.0, baseline_success_rate - estimated_delta)

    top_actions = [
        {
            "node_id": item.get("node_id"),
            "cve_id": item.get("cve_id"),
            "simulation_impact": item.get("simulation_impact", 0.0),
            "cvss_score": item.get("cvss_score"),
        }
        for item in chosen
    ]

    return {
        "patched_success_rate": round(patched_rate, 4),
        "risk_reduction_pp": round((baseline_success_rate - patched_rate) * 100.0, 2),
        "top_actions": top_actions,
    }


def _confidence_from_source(source: Optional[str]) -> str:
    if source == "telemetry":
        return "measured"
    if source == "hybrid":
        return "hybrid"
    return "estimated"


def _build_evidence_bundle(
    topology: str,
    n_episodes: int,
    n_baseline: int,
    n_eval_per_patch: int,
    telemetry_weight: float,
    comparison_source: Optional[str] = None,
) -> dict:
    backend_status = status()
    telemetry_status = telemetry_status_endpoint(topology)
    source = comparison_source or ("telemetry" if int(telemetry_status.get("event_count") or 0) > 0 else "hybrid")

    baseline = _run_attack_analysis(
        topology_path=_resolve_topology(topology),
        topology_key=topology,
        n_episodes=n_episodes,
        seed=42,
        data_source="simulation",
        telemetry_weight=telemetry_weight,
    )
    comparison = _run_attack_analysis(
        topology_path=_resolve_topology(topology),
        topology_key=topology,
        n_episodes=n_episodes,
        seed=42,
        data_source=source,
        telemetry_weight=telemetry_weight,
    )
    patch_results_data = _generate_patch_results(
        topology_key=topology,
        n_baseline=n_baseline,
        n_eval_per_patch=n_eval_per_patch,
        data_source=source,
        telemetry_weight=telemetry_weight,
    )

    baseline_rate = float(baseline.get("success_rate", 0.0) or 0.0)
    comparison_rate = float(comparison.get("success_rate", 0.0) or 0.0)
    variance = {
        "baseline_data_source": baseline.get("data_source", "simulation"),
        "comparison_data_source": comparison.get("data_source", "simulation"),
        "requested_comparison_source": comparison.get("requested_data_source"),
        "baseline_success_rate": baseline_rate,
        "comparison_success_rate": comparison_rate,
        "success_rate_delta_pp": round((baseline_rate - comparison_rate) * 100.0, 2),
        "baseline_top_paths": (baseline.get("top_paths") or [])[:5],
        "comparison_top_paths": (comparison.get("top_paths") or [])[:5],
        "telemetry_event_count": int(telemetry_status.get("event_count") or 0),
        "telemetry_blocked_events": int(telemetry_status.get("blocked_events") or 0),
        "telemetry_critical_reaches": int(telemetry_status.get("critical_reaches") or 0),
        "telemetry_source": telemetry_status.get("source"),
        "telemetry_updated_at": telemetry_status.get("updated_at"),
    }

    bundle_dir = PROJECT_ROOT / "reports" / "evidence" / f"bundle-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "backend_url": "local-backend",
        "topology": topology,
        "episodes": n_episodes,
        "telemetry_weight": telemetry_weight,
        "comparison_source": source,
        "output_dir": str(bundle_dir),
    }

    def _write_json(name: str, payload: dict) -> str:
        path = bundle_dir / name
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return str(path.relative_to(PROJECT_ROOT))

    summary_lines = [
        "# Onyx Evidence Bundle",
        "",
        f"Generated at: {manifest['generated_at']}",
        f"Topology: {topology}",
        "",
        "| Metric | Baseline | Comparison | Delta |",
        "|---|---:|---:|---:|",
        f"| Success rate | {baseline_rate:.4f} | {comparison_rate:.4f} | {variance['success_rate_delta_pp']:+.2f} pp |",
        f"| Telemetry events | n/a | {variance['telemetry_event_count']} | n/a |",
        "",
        "## Evidence Files",
        "",
        "- manifest.json",
        "- backend_status.json",
        "- telemetry_status.json",
        "- baseline_simulation.json",
        "- comparison_simulation.json",
        "- patch_results.json",
        "- variance.json",
    ]

    files = {
        "manifest.json": manifest,
        "backend_status.json": backend_status,
        "telemetry_status.json": telemetry_status,
        "baseline_simulation.json": baseline,
        "comparison_simulation.json": comparison,
        "patch_results.json": patch_results_data,
        "variance.json": variance,
    }
    written = {name: _write_json(name, payload) for name, payload in files.items()}
    summary_path = bundle_dir / "summary.md"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    written["summary.md"] = str(summary_path.relative_to(PROJECT_ROOT))

    return {
        "manifest": manifest,
        "backend_status": backend_status,
        "telemetry_status": telemetry_status,
        "baseline": baseline,
        "comparison": comparison,
        "patch_results": patch_results_data,
        "variance": variance,
        "files": written,
    }


def _get_telemetry_ingest_api_key() -> str:
    """Return the local ingest key, allowing credential rotation during development.

    The launcher persists local credentials in ``.onyx-secrets.cmd``.  A
    long-running reload process can otherwise retain an older inherited
    environment variable after that file has been regenerated.  Prefer the
    current file value when it is available, and retain the environment value
    as the fallback for deployed environments without that local file.
    """
    secrets_file = PROJECT_ROOT / ".onyx-secrets.cmd"
    try:
        for line in secrets_file.read_text(encoding="ascii").splitlines():
            prefix = "set ONYX_TELEMETRY_INGEST_API_KEY="
            if line.lower().startswith(prefix.lower()):
                value = line[len(prefix):].strip()
                if value:
                    return value
    except OSError:
        pass

    return (os.getenv("ONYX_TELEMETRY_INGEST_API_KEY") or "").strip()


def _extract_api_key_from_request(request: Request) -> str:
    auth_header = (request.headers.get("Authorization") or "").strip()
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return (request.headers.get("X-API-Key") or "").strip()


def _verify_telemetry_ingest_auth(request: Request) -> None:
    expected_api_key = _get_telemetry_ingest_api_key()
    if not expected_api_key:
        raise HTTPException(status_code=503, detail="Endpoint authentication is not configured")

    provided_api_key = _extract_api_key_from_request(request)
    if not provided_api_key or not hmac.compare_digest(provided_api_key, expected_api_key):
        raise HTTPException(status_code=401, detail="Unauthorized telemetry ingest request")


def _response_controls_enabled() -> bool:
    return (os.getenv("ONYX_RESPONSE_CONTROLS_ENABLED") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _require_response_controls() -> None:
    if not _response_controls_enabled():
        raise HTTPException(
            status_code=403,
            detail=(
                "Endpoint response controls are disabled. Set "
                "ONYX_RESPONSE_CONTROLS_ENABLED=true after completing a controlled rollout."
            ),
        )


def _organization_id() -> str:
    return (os.getenv("ONYX_ORGANIZATION_ID") or "default").strip() or "default"


def _verify_admin_auth(request: Request) -> str:
    expected_api_key = (os.getenv("ONYX_ADMIN_API_KEY") or "").strip()
    if not expected_api_key:
        raise HTTPException(status_code=503, detail="Administrator authentication is not configured")
    provided_api_key = _extract_api_key_from_request(request)
    if not provided_api_key or not hmac.compare_digest(provided_api_key, expected_api_key):
        raise HTTPException(status_code=401, detail="Unauthorized administrator request")
    return (os.getenv("ONYX_ADMIN_ACTOR") or "pilot-administrator").strip()


def _credential_hash(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _verify_device_auth(request: Request, endpoint_id: str) -> Dict[str, Any]:
    if (os.getenv("ONYX_ALLOW_LEGACY_SHARED_AGENT_KEY") or "").lower() in {
        "1", "true", "yes", "on"
    }:
        _verify_telemetry_ingest_auth(request)
        return {"endpoint_id": endpoint_id, "organization_id": _organization_id(), "legacy": True}
    provided = _extract_api_key_from_request(request)
    binding = get_authenticated_device(endpoint_id, _credential_hash(provided)) if provided else None
    if not binding:
        raise HTTPException(status_code=401, detail="Unauthorized device request")
    return binding


def _verify_response_auth(request: Request) -> None:
    _require_response_controls()
    expected_api_key = (os.getenv("ONYX_RESPONSE_API_KEY") or "").strip()
    if not expected_api_key:
        raise HTTPException(status_code=503, detail="Response authorization is not configured")
    provided_api_key = _extract_api_key_from_request(request)
    if not provided_api_key or not hmac.compare_digest(provided_api_key, expected_api_key):
        raise HTTPException(status_code=401, detail="Unauthorized endpoint response request")


def _extract_json_object(raw_text: str) -> Optional[Dict[str, Any]]:
    text = (raw_text or "").strip()
    if not text:
        return None

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    lines = [line for line in text.splitlines() if line.strip()]
    for i in range(len(lines) - 1, -1, -1):
        candidate = "\n".join(lines[i:]).strip()
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    return None


def _parse_iso_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


DEMO_ENDPOINT_STATE: Dict[str, bool] = {}
DEMO_COMMANDS: Dict[str, Dict[str, Any]] = {}


def _demo_endpoints(topology: str) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    definitions = [
        ("founder-windows", "FOUNDER-LAPTOP", "10.10.0.21", "Windows 11 Pro", 0),
        ("finance-windows", "FINANCE-LAPTOP", "10.10.0.22", "Windows 11 Pro", 1),
        ("developer-mac", "DEV-MACBOOK", "10.10.0.23", "macOS 15", 0),
        ("operations-mac", "OPS-MACBOOK", "10.10.0.24", "macOS 15", 0),
    ]
    rows = []
    for endpoint_id, hostname, ip_address, platform_name, threat_count in definitions:
        quarantined = DEMO_ENDPOINT_STATE.get(endpoint_id, False)
        latest = next(
            (command for command in reversed(list(DEMO_COMMANDS.values())) if command["endpoint_id"] == endpoint_id),
            None,
        )
        rows.append(
            {
                "endpoint_id": endpoint_id,
                "hostname": hostname,
                "ip_address": ip_address,
                "topology": topology,
                "agent_version": "demo-agent-1.0.0",
                "platform": platform_name,
                "quarantined": quarantined,
                "last_error": None,
                "metadata": {"telemetry_mode": "demo", "response_capable": True},
                "first_seen_at": now,
                "last_seen_at": now,
                "status": "active",
                "seconds_since_last_seen": 0.0,
                "event_count": 3 if threat_count else 2,
                "threat_count": threat_count,
                "latest_command": latest,
            }
        )
    return rows


def _demo_events() -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    return [
        {
            "event_id": "demo-defender-1116",
            "timestamp": (now).isoformat(),
            "source_node": "finance-windows",
            "target_node": "finance-windows",
            "event_type": "malware_detected",
            "confidence": 1.0,
            "blocked": False,
            "reached_critical": False,
            "raw": {
                "provider": "Demo Microsoft Defender",
                "windows_event_id": 1116,
                "threat_name": "EICAR-Test-File",
                "path": "C:\\Users\\Finance\\Downloads\\eicar.com.txt",
                "demo": True,
            },
        },
        {
            "event_id": "demo-network-finance-api",
            "timestamp": (now).isoformat(),
            "source_node": "finance-windows",
            "target_node": "app_server",
            "event_type": "network_connect",
            "confidence": 1.0,
            "blocked": False,
            "reached_critical": False,
            "raw": {"provider": "Demo Sysmon", "destination_port": 443, "demo": True},
        },
        {
            "event_id": "demo-login-founder",
            "timestamp": (now).isoformat(),
            "source_node": "founder-windows",
            "target_node": "ldap_server",
            "event_type": "authentication",
            "confidence": 1.0,
            "blocked": False,
            "reached_critical": False,
            "raw": {"provider": "Demo endpoint agent", "demo": True},
        },
    ]


def _demo_simulation(topology_key: str, n_episodes: int) -> dict:
    """Return a stable, explicitly simulated attack narrative for presentations."""
    successful_runs = round(n_episodes * 0.64)
    return {
        "topology": topology_key,
        "n_episodes": n_episodes,
        "evaluation_runs": n_episodes,
        "successful_runs": successful_runs,
        "failed_runs": n_episodes - successful_runs,
        "success_rate": successful_runs / n_episodes,
        "total_unique_paths": 1,
        "top_paths": [{
            "path": "vpn_gateway -> web_server_1 -> app_server -> customer_db",
            "count": successful_runs,
            "frequency": successful_runs / n_episodes,
        }],
        "data_source": "simulation",
        "requested_data_source": "simulation",
        "data_source_note": "fixed_demo_scenario; simulated data only",
        "confidence": "simulated",
        "data_freshness_at": datetime.now(timezone.utc).isoformat(),
        "policy_engine": "rule_based",
    }


@app.post("/api/device-enrollment/tokens")
def create_device_enrollment_token(payload: EnrollmentTokenRequest, request: Request) -> dict:
    _verify_admin_auth(request)
    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=payload.expires_in_minutes)
    save_enrollment_token(
        _credential_hash(raw_token), _organization_id(), payload.allowed_platform,
        expires_at.isoformat(), 1,
    )
    return {
        "enrollment_token": raw_token,
        "organization_id": _organization_id(),
        "expires_at": expires_at.replace(tzinfo=timezone.utc).isoformat(),
        "max_uses": 1,
    }


@app.post("/api/device-enrollment/exchange")
def exchange_device_enrollment(payload: DeviceEnrollmentRequest) -> dict:
    device_secret = secrets.token_urlsafe(48)
    enrolled = consume_enrollment_token(
        _credential_hash(payload.enrollment_token), payload.endpoint_id, payload.platform,
        _credential_hash(device_secret),
    )
    if not enrolled:
        raise HTTPException(status_code=401, detail="Enrollment token is invalid, expired, used, or incompatible")
    return {**enrolled, "device_credential": device_secret}


@app.post("/api/devices/{endpoint_id}/revoke")
def revoke_device_credential(endpoint_id: str, request: Request) -> dict:
    _verify_admin_auth(request)
    if not revoke_device(endpoint_id):
        raise HTTPException(status_code=404, detail="Active device credential not found")
    return {"endpoint_id": endpoint_id, "revoked": True}


@app.post("/api/endpoints/heartbeat")
def endpoint_heartbeat(payload: EndpointHeartbeatRequest, request: Request) -> dict:
    binding = _verify_device_auth(request, payload.endpoint_id)
    _resolve_topology(payload.topology)
    if len(json.dumps(payload.metadata, allow_nan=False)) > 8192:
        raise HTTPException(status_code=422, detail="Endpoint metadata must be at most 8 KiB")
    previous = get_endpoint(payload.endpoint_id)
    heartbeat = payload.model_dump()
    heartbeat["organization_id"] = binding["organization_id"]
    endpoint = upsert_endpoint_heartbeat(heartbeat)
    for observation in payload.metadata.get("observed_connections", []):
        if isinstance(observation, dict) and observation.get("target"):
            upsert_relationship(payload.endpoint_id, str(observation["target"]), payload.topology, str(observation.get("type") or "observed_connection"), float(observation.get("confidence") or 0.6))
    if not previous:
        create_notification("endpoint_online", "info", f"Laptop connected: {payload.hostname}", "A live endpoint heartbeat was received.", endpoint_id=payload.endpoint_id)
    return {"endpoint": endpoint, "server_time": datetime.now(timezone.utc).isoformat()}


@app.get("/api/devices/{endpoint_id}/configuration")
def get_device_configuration(endpoint_id: str, request: Request) -> dict:
    binding = _verify_device_auth(request, endpoint_id)
    platform = str(binding.get("platform") or "").lower()
    collectors = ["windows_defender"] if "windows" in platform else ["apple_security_log"]
    return {
        "endpoint_id": endpoint_id,
        "organization_id": binding["organization_id"],
        "heartbeat_interval_seconds": 300,
        "configuration_poll_seconds": 3600,
        "event_batch_size": 100,
        "queue_max_bytes": 10 * 1024 * 1024,
        "queue_max_age_days": 7,
        "enabled_collectors": collectors,
        "minimum_agent_version": "1.0.0",
        "response_controls_enabled": False,
    }


@app.post("/api/devices/{endpoint_id}/telemetry/batches")
def ingest_device_telemetry_batch(endpoint_id: str, payload: DeviceTelemetryBatchRequest, request: Request) -> dict:
    binding = _verify_device_auth(request, endpoint_id)
    _resolve_topology(payload.topology)
    raw_events = [event.model_dump() for event in payload.events]
    if len(json.dumps(raw_events, allow_nan=False).encode("utf-8")) > 512 * 1024:
        raise HTTPException(status_code=413, detail="Telemetry batch must be at most 512 KiB")
    if not record_agent_batch(endpoint_id, binding["organization_id"], payload.batch_id, len(raw_events)):
        return {"accepted": True, "duplicate": True, "inserted": 0, "batch_id": payload.batch_id}
    for event in raw_events:
        event["source_node"] = endpoint_id
        event["raw"] = event.get("raw") or {}
        event["raw"]["agent_endpoint_id"] = endpoint_id
    normalized = normalize_events(raw_events, payload.topology)
    inserted = store_telemetry_events(payload.topology, normalized, binding["organization_id"])
    record_agent_audit(binding["organization_id"], endpoint_id, "telemetry_batch_received", {"batch_id": payload.batch_id, "events": len(raw_events), "inserted": inserted})
    return {"accepted": True, "duplicate": False, "inserted": inserted, "batch_id": payload.batch_id}


@app.post("/api/devices/{endpoint_id}/rotate-credential")
def rotate_device_credential_route(endpoint_id: str, payload: DeviceCredentialRotateRequest, request: Request) -> dict:
    provided = _extract_api_key_from_request(request)
    if not provided:
        raise HTTPException(status_code=401, detail="Unauthorized device request")
    new_secret = secrets.token_urlsafe(48)
    rotated = rotate_device_credential(endpoint_id, _credential_hash(provided), _credential_hash(new_secret))
    if not rotated:
        raise HTTPException(status_code=401, detail="Unauthorized device request")
    record_agent_audit(rotated["organization_id"], endpoint_id, "credential_rotated", {"reason": payload.reason})
    return {"endpoint_id": endpoint_id, "organization_id": rotated["organization_id"], "device_credential": new_secret}


@app.get("/api/endpoints")
def endpoints(
    topology: Optional[str] = Query(default=None),
    mode: Literal["reality", "demo"] = Query(default="reality"),
) -> dict:
    if topology:
        _resolve_topology(topology)
    if mode == "demo":
        demo_rows = _demo_endpoints(topology or "enterprise_20n")
        return {
            "endpoints": demo_rows,
            "count": len(demo_rows),
            "server_time": datetime.now(timezone.utc).isoformat(),
            "mode": "demo",
        }
    endpoint_rows = list_endpoints(topology)
    telemetry_rows = get_telemetry_events(topology, 5000) if topology else []
    threat_counts: Dict[str, int] = {}
    event_counts: Dict[str, int] = {}
    for event in telemetry_rows:
        source_node = str(event.get("source_node") or "unknown_source")
        event_counts[source_node] = event_counts.get(source_node, 0) + 1
        if event.get("event_type") == "malware_detected":
            threat_counts[source_node] = threat_counts.get(source_node, 0) + 1

    now = datetime.now(timezone.utc)
    for endpoint in endpoint_rows:
        seen_at = _parse_iso_timestamp(endpoint.get("last_seen_at"))
        age_seconds = (now - seen_at).total_seconds() if seen_at else None
        freshness_seconds = max(30, int(os.getenv("ONYX_HEARTBEAT_FRESH_SECONDS") or "300"))
        stale_seconds = max(freshness_seconds, int(os.getenv("ONYX_HEARTBEAT_STALE_SECONDS") or "86400"))
        endpoint["status"] = "active" if age_seconds is not None and age_seconds <= freshness_seconds else "offline"
        endpoint["evidence_state"] = (
            "unknown" if age_seconds is None else
            "fresh" if age_seconds <= freshness_seconds else
            "stale" if age_seconds <= stale_seconds else
            "offline"
        )
        endpoint["seconds_since_last_seen"] = round(max(0.0, age_seconds), 1) if age_seconds is not None else None
        endpoint["event_count"] = event_counts.get(endpoint["endpoint_id"], 0)
        endpoint["threat_count"] = threat_counts.get(endpoint["endpoint_id"], 0)
        commands = list_response_commands(endpoint["endpoint_id"], 1)
        endpoint["latest_command"] = commands[0] if commands else None
        incidents = list_open_incidents(endpoint["endpoint_id"])
        # Materialise incidents for Defender evidence received before incident
        # tracking was introduced, so historical detections are not invisible.
        if not incidents:
            for event in telemetry_rows:
                if str(event.get("source_node")) != endpoint["endpoint_id"] or str(event.get("event_type")) != "malware_detected":
                    continue
                raw = event.get("raw") or {}
                source = "simulated" if raw.get("simulated_detection") else "microsoft_defender"
                incident = create_incident(endpoint["endpoint_id"], endpoint["topology"], str(event.get("event_id")), source,
                                           str(raw.get("threat_name") or "Endpoint threat detection"), _incident_severity(event))
                if incident:
                    incidents.append(incident)
            incidents = list_open_incidents(endpoint["endpoint_id"])
        endpoint["open_incident_count"] = len(incidents)
        endpoint["latest_incident"] = incidents[0] if incidents else None
        severity_rank = {"low": 1, "medium": 1, "warning": 1, "compromised": 2, "high": 2, "critical": 3}
        highest = max((incidents or []), key=lambda item: severity_rank.get(str(item.get("severity")), 1), default=None)
        endpoint["security_state"] = "quarantined" if endpoint["quarantined"] else (str(highest.get("severity")) if highest else "healthy")
        endpoint["server_link_disconnected"] = server_link_disconnected(endpoint["endpoint_id"])
    return {"endpoints": endpoint_rows, "count": len(endpoint_rows), "server_time": now.isoformat()}


def _incident_severity(event: Dict[str, Any]) -> str:
    """Map Defender evidence to the dashboard's yellow/red/blue states."""
    raw = event.get("raw") or {}
    text = " ".join(str(raw.get(key) or "") for key in ("path", "threat_name", "summary")).lower()
    if bool(event.get("reached_critical")) or bool(raw.get("critical_asset")) or bool(raw.get("critical_reach")):
        return "critical"
    if any(term in text for term in ("severity: severe", "severity: high", "trojan", "ransomware", "backdoor")):
        return "compromised"
    return "warning"


@app.get("/api/reality/overview")
def reality_overview(topology: str = Query(default="enterprise_20n")) -> dict:
    """Evidence-only posture; deliberately contains no simulated fallback."""
    _resolve_topology(topology)
    rows = endpoints(topology=topology, mode="reality")["endpoints"]
    events = get_telemetry_events(topology, 5000)
    active = [row for row in rows if row.get("status") == "active"]
    affected = [row for row in rows if row.get("security_state") in ("warning", "compromised", "critical")]
    relationships = list_relationships(topology)
    findings = list_vulnerability_findings(topology)
    expected = max(0, int(os.getenv("ONYX_EXPECTED_DEVICE_COUNT") or "0"))
    denominator = expected or len(rows)
    stale = [row for row in rows if row.get("evidence_state") == "stale"]
    offline = [row for row in rows if row.get("evidence_state") == "offline"]
    unknown = [row for row in rows if row.get("evidence_state") == "unknown"]
    latest = max((str(event.get("timestamp") or "") for event in events), default=None)
    readiness = {
        "endpoints": len(rows) > 0,
        "telemetry": len(events) > 0,
        "relationships": len(relationships) > 0,
        "vulnerability_inventory": len(findings) > 0,
    }
    return {"topology": topology, "enrolled_assets": len(rows), "expected_assets": expected or None,
            "unenrolled_assets": max(0, expected - len(rows)), "active_assets": len(active),
            "stale_assets": len(stale), "offline_assets": len(offline), "unknown_assets": len(unknown),
            "collector_errors": sum(1 for row in rows if row.get("last_error")), "affected_assets": len(affected),
            "open_incidents": sum(int(row.get("open_incident_count") or 0) for row in rows), "telemetry_events": len(events),
            "last_telemetry_at": latest, "coverage_percent": round((len(active) / denominator * 100) if denominator else 0, 1),
            "relationships": len(relationships), "readiness": readiness, "analytics_ready": all(readiness.values())}


def _reality_analytics_readiness(topology: str) -> Dict[str, Any]:
    endpoint_rows = endpoints(topology=topology, mode="reality")["endpoints"]
    relationships = list_relationships(topology)
    findings = list_vulnerability_findings(topology)
    expected = max(0, int(os.getenv("ONYX_EXPECTED_DEVICE_COUNT") or "0"))
    minimum_coverage = min(1.0, max(0.0, float(os.getenv("ONYX_MINIMUM_COVERAGE") or "0.8")))
    active_count = sum(1 for row in endpoint_rows if row.get("status") == "active")
    denominator = expected or len(endpoint_rows)
    coverage = (active_count / denominator) if denominator else 0.0
    missing = []
    if not endpoint_rows:
        missing.append("enrolled endpoint inventory")
    if not relationships:
        missing.append("observed network relationships")
    if not findings:
        missing.append("source-attributed vulnerability findings")
    if coverage < minimum_coverage:
        missing.append(f"reporting coverage >= {minimum_coverage * 100:.0f}%")
    return {
        "ready": not missing,
        "missing": missing,
        "assets": len(endpoint_rows),
        "relationships": len(relationships),
        "findings": len(findings),
        "patchable_findings": sum(1 for finding in findings if finding.get("fix_available")),
        "critical_findings": sum(1 for finding in findings if float(finding.get("cvss_score") or 0) >= 9.0),
        "coverage_percent": round(coverage * 100, 1),
        "minimum_coverage_percent": round(minimum_coverage * 100, 1),
    }


@app.post("/api/vulnerabilities/ingest")
def vulnerability_ingest(payload: VulnerabilityIngestRequest, request: Request) -> dict:
    _verify_telemetry_ingest_auth(request)
    _resolve_topology(payload.topology)
    registered = {row["endpoint_id"] for row in endpoints(topology=payload.topology, mode="reality")["endpoints"]}
    unknown = sorted({finding.endpoint_id for finding in payload.findings if finding.endpoint_id not in registered})
    if unknown:
        raise HTTPException(status_code=422, detail=f"Findings reference unregistered endpoints: {', '.join(unknown)}")
    for finding in payload.findings:
        identifier = (finding.cve_id or "").upper()
        if identifier.startswith("SYNTH-"):
            raise HTTPException(status_code=422, detail="Synthetic findings cannot enter Reality storage")
        if identifier.startswith("CVE-"):
            required = {"source_url", "source_name", "retrieved_at", "affected_product"}
            missing_evidence = sorted(required - set(finding.evidence))
            if missing_evidence or not finding.software or not finding.software_version:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Real CVE findings require software, software_version and source evidence: "
                        + ", ".join(missing_evidence)
                    ),
                )
    stored = upsert_vulnerability_findings(payload.topology, [finding.model_dump() for finding in payload.findings])
    return {"stored": stored, "readiness": _reality_analytics_readiness(payload.topology)}


@app.get("/api/reality/exposure")
def reality_exposure(topology: str = Query(default="enterprise_20n")) -> dict:
    _resolve_topology(topology)
    readiness = _reality_analytics_readiness(topology)
    if not readiness["ready"]:
        return {"ready": False, "readiness": readiness, "findings": [], "paths": [], "assets": []}
    findings = list_vulnerability_findings(topology)
    rows = {row["endpoint_id"]: row for row in endpoints(topology=topology, mode="reality")["endpoints"]}
    by_asset: Dict[str, List[Dict[str, Any]]] = {}
    for finding in findings:
        by_asset.setdefault(finding["endpoint_id"], []).append(finding)
    assets = [{"endpoint_id": endpoint_id, "hostname": rows.get(endpoint_id, {}).get("hostname", endpoint_id),
               "open_findings": len(asset_findings), "max_cvss": max(item["cvss_score"] for item in asset_findings),
               "sources": sorted({item["source"] for item in asset_findings})}
              for endpoint_id, asset_findings in by_asset.items()]
    assets.sort(key=lambda item: (-item["max_cvss"], -item["open_findings"]))
    # These are observed relationships with exposed source assets, not simulated attack paths.
    paths = [{"id": f"OBS-{index:03d}", "entry": relation["source_asset"], "target": relation["target_asset"],
              "confidence": relation["confidence"], "relation_type": relation["relation_type"], "last_observed_at": relation["last_observed_at"]}
             for index, relation in enumerate(list_relationships(topology), start=1) if relation["source_asset"] in by_asset]
    return {"ready": True, "readiness": readiness, "findings": findings, "assets": assets, "paths": paths,
            "provenance": "live endpoint inventory + observed relationships + imported vulnerability findings"}


@app.get("/api/reality/patch-roi")
def reality_patch_roi(topology: str = Query(default="enterprise_20n")) -> dict:
    exposure = reality_exposure(topology)
    if not exposure["ready"]:
        return {"ready": False, "readiness": exposure["readiness"], "results": []}
    endpoint_rows = {row["endpoint_id"]: row for row in endpoints(topology=topology, mode="reality")["endpoints"]}
    results = []
    for finding in exposure["findings"]:
        endpoint = endpoint_rows.get(finding["endpoint_id"], {})
        criticality = str((endpoint.get("metadata") or {}).get("asset_criticality") or "standard").lower()
        multiplier = 1.8 if criticality == "critical" else 1.3 if criticality == "high" else 1.0
        effort = float(finding.get("effort_hours") or (4 if "server" in str(endpoint.get("platform") or "").lower() else 2))
        priority = round(min(1.0, (float(finding["cvss_score"]) / 10) * multiplier * (1.0 if finding["fix_available"] else 0.45)), 3)
        results.append({"node_id": finding["endpoint_id"], "hostname": endpoint.get("hostname", finding["endpoint_id"]),
                        "cve_id": finding.get("cve_id") or finding["finding_id"], "description": finding["title"],
                        "cvss_score": finding["cvss_score"], "effort_hours": effort, "fix_available": finding["fix_available"],
                        "priority_score": round(priority * 100, 1),
                        "priority_per_effort": round((priority * 100) / effort, 2),
                        "measurement_type": "estimated_priority",
                        "source": finding["source"], "observed_at": finding["observed_at"], "evidence": finding["evidence"]})
    results.sort(key=lambda item: (-item["priority_per_effort"], -item["cvss_score"]))
    return {"ready": True, "readiness": exposure["readiness"], "results": results,
            "provenance": "live vulnerability findings; scores are prioritization estimates, not measured or simulated risk reduction"}


_REMEDIATION_TRANSITIONS = {
    "proposed": {"accepted", "exception"},
    "accepted": {"in_progress", "exception"},
    "in_progress": {"contained", "awaiting_verification", "exception"},
    "contained": {"awaiting_verification", "reopened"},
    "awaiting_verification": {"verified", "reopened", "exception"},
    "verified": {"closed", "reopened"},
    "exception": {"closed", "reopened"},
    "closed": {"reopened"},
    "reopened": {"in_progress", "exception"},
}


@app.get("/api/remediation/actions")
def remediation_actions(
    request: Request,
    state: Optional[str] = Query(default=None),
) -> dict:
    _verify_admin_auth(request)
    if state and state not in _REMEDIATION_TRANSITIONS:
        raise HTTPException(status_code=422, detail="Unknown remediation state")
    rows = list_remediation_actions(_organization_id(), state)
    return {"actions": rows, "count": len(rows), "organization_id": _organization_id()}


@app.post("/api/remediation/actions")
def create_remediation(payload: RemediationActionCreateRequest, request: Request) -> dict:
    actor = _verify_admin_auth(request)
    endpoint = get_endpoint(payload.endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    finding = next(
        (
            row for row in list_vulnerability_findings(endpoint["topology"])
            if row["finding_id"] == payload.finding_id and row["endpoint_id"] == payload.endpoint_id
        ),
        None,
    )
    if not finding:
        raise HTTPException(status_code=404, detail="Source finding not found for endpoint")
    action = create_remediation_action({
        **payload.model_dump(),
        "action_id": f"rem_{uuid.uuid4().hex}",
        "organization_id": _organization_id(),
        "actor": actor,
    })
    return {"action": action}


@app.put("/api/remediation/actions/{action_id}")
def update_remediation(
    action_id: str, payload: RemediationActionUpdateRequest, request: Request
) -> dict:
    actor = _verify_admin_auth(request)
    current = get_remediation_action(action_id)
    if not current or current["organization_id"] != _organization_id():
        raise HTTPException(status_code=404, detail="Remediation action not found")
    if payload.state not in _REMEDIATION_TRANSITIONS[current["state"]]:
        raise HTTPException(
            status_code=409,
            detail=f"Invalid transition from {current['state']} to {payload.state}",
        )
    if payload.state == "verified":
        required = {"source", "timestamp", "observation", "reviewer"}
        if not payload.verification or not required.issubset(payload.verification):
            raise HTTPException(status_code=422, detail="Verification evidence is incomplete")
    if payload.state == "exception":
        required = {"reason", "approver", "expiry", "compensating_control"}
        if not payload.exception or not required.issubset(payload.exception):
            raise HTTPException(status_code=422, detail="Exception evidence is incomplete")
    updated = update_remediation_action(
        action_id, payload.state, actor, payload.owner, payload.due_date,
        payload.verification, payload.exception,
    )
    return {"action": updated}


@app.get("/api/remediation/actions.csv")
def export_remediation_actions(request: Request) -> Response:
    _verify_admin_auth(request)
    rows = list_remediation_actions(_organization_id())
    output = io.StringIO()
    fields = [
        "action_id", "endpoint_id", "finding_id", "title", "owner", "due_date",
        "priority", "state", "created_at", "updated_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        output.getvalue(), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=onyx-remediation-actions.csv"},
    )


@app.get("/api/reality/topology")
def reality_topology(topology: str = Query(default="enterprise_20n")) -> dict:
    _resolve_topology(topology)
    rows = endpoints(topology=topology, mode="reality")["endpoints"]
    nodes = [{"node_id": row["endpoint_id"], "node_type": "endpoint laptop", "hostname": row["hostname"],
              "ip_address": row.get("ip_address"), "endpoint_status": row["status"], "security_state": row["security_state"],
              "last_seen_at": row.get("last_seen_at"), "provenance": "endpoint_agent",
              "server_link_disconnected": row.get("server_link_disconnected", False), "services": []} for row in rows]
    nodes.append({"node_id": "onyx_control_server", "node_type": "control server", "hostname": "Onyx appliance",
                  "endpoint_status": "active", "security_state": "healthy", "provenance": "local_appliance", "services": ["API"]})
    known = {node["node_id"] for node in nodes}
    edges = [{"source": row["endpoint_id"], "target": "onyx_control_server", "connection_type": "authenticated heartbeat", "confidence": 1.0}
             for row in rows if not row.get("server_link_disconnected")]
    discovered: Dict[str, Dict[str, Any]] = {}
    for relation in list_relationships(topology):
        if relation["source_asset"] in known:
            raw_target = str(relation["target_asset"])
            asset_id, separator, service = raw_target.rpartition(":")
            if not separator or not service.isdigit():
                asset_id, service = raw_target, ""
            asset = discovered.setdefault(asset_id, {"node_id": asset_id, "node_type": "discovered network asset",
                "endpoint_status": "observed", "security_state": "healthy", "provenance": "observed_network_relationship", "services": []})
            if service and service not in asset["services"]:
                asset["services"].append(service)
            edge_key = (relation["source_asset"], asset_id)
            if not any((edge["source"], edge["target"]) == edge_key for edge in edges):
                edges.append({"source": relation["source_asset"], "target": asset_id, "connection_type": relation["relation_type"], "confidence": relation["confidence"], "last_observed_at": relation["last_observed_at"]})
    nodes.extend(discovered.values())
    nodes.sort(key=lambda node: (node["node_type"] != "control server", node["node_id"]))
    edges.sort(key=lambda edge: (edge["source"], edge["target"]))
    return {"nodes": nodes, "edges": edges, "source": "verified_live_observations"}


def _build_live_replay(result: dict, topology_key: str) -> dict:
    live = reality_topology(topology_key)
    nodes_by_id = {node["node_id"]: node for node in live["nodes"]}
    affected = [node["node_id"] for node in live["nodes"] if node.get("security_state") in ("warning", "compromised", "critical")]
    start = affected[0] if affected else next((node["node_id"] for node in live["nodes"] if node.get("node_type") == "endpoint laptop"), None)
    path = [start] if start else []
    if start:
        for edge in live["edges"]:
            if edge["source"] == start and edge["target"] not in path:
                path.append(edge["target"])
                if len(path) >= 5:
                    break
    steps = []
    for index, node_id in enumerate(path):
        node = nodes_by_id[node_id]
        steps.append({"step": index + 1, "node_id": node_id, "node_type": node.get("node_type", "asset"),
            "software": ", ".join(node.get("services") or []) or "Observed asset", "version": "live", "num_vulns": 0,
            "max_cvss": 0, "compromise_probability": float(result.get("success_rate") or 0), "is_critical_asset": False,
            "is_entry_point": index == 0, "edge": None})
    episodes = int(result.get("n_episodes") or result.get("evaluation_runs") or 0)
    success = float(result.get("success_rate") or 0)
    return {"topology": topology_key, "path": path, "steps": steps, "success_rate": success, "n_episodes": episodes,
        "successful_runs": int(result.get("successful_runs") or round(success * episodes)), "failed_runs": int(result.get("failed_runs") or round((1-success) * episodes)),
        "total_unique_paths": int(result.get("total_unique_paths") or (1 if path else 0)), "selected_path_count": int(round(success * episodes)),
        "selected_path_frequency": success, "reaches_critical_asset": False, "data_source": result.get("data_source") or "telemetry",
        "requested_data_source": "telemetry", "data_source_note": "predictive_model_conditioned_on_live_endpoint_evidence",
        "confidence": result.get("confidence") or "estimated", "analysis_engine": result.get("policy_engine") or "telemetry_events",
        "generated_at": result.get("data_freshness_at") or datetime.now(timezone.utc).isoformat()}


@app.post("/api/endpoints/{endpoint_id}/server-link")
def set_endpoint_server_link(endpoint_id: str, payload: ServerLinkRequest, request: Request) -> dict:
    _verify_response_auth(request)
    endpoint = get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    if (endpoint.get("metadata") or {}).get("response_capable") is not True:
        raise HTTPException(
            status_code=409,
            detail="Endpoint has not advertised the requested response capability",
        )
    set_server_link(endpoint_id, payload.disconnected)
    create_notification(
        "server_link", "warning" if payload.disconnected else "info",
        f"Server link {'cut' if payload.disconnected else 'restored'}",
        f"{endpoint_id}: {payload.reason}", endpoint_id=endpoint_id,
    )
    return {"endpoint_id": endpoint_id, "server_link_disconnected": payload.disconnected}


@app.post("/api/endpoints/{endpoint_id}/commands")
def request_endpoint_command(
    endpoint_id: str,
    payload: ResponseCommandRequest,
    request: Request,
    mode: Literal["reality", "demo"] = Query(default="reality"),
) -> dict:
    _require_response_controls()
    if mode == "demo":
        if endpoint_id not in {row["endpoint_id"] for row in _demo_endpoints("enterprise_20n")}:
            raise HTTPException(status_code=404, detail="Demo endpoint not found")
        command_id = f"demo_cmd_{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc).isoformat()
        DEMO_ENDPOINT_STATE[endpoint_id] = payload.action == "quarantine"
        command = {
            "command_id": command_id,
            "endpoint_id": endpoint_id,
            "action": payload.action,
            "status": "succeeded",
            "reason": payload.reason,
            "requested_by": payload.requested_by,
            "error_message": None,
            "requested_at": now,
            "delivered_at": now,
            "completed_at": now,
        }
        DEMO_COMMANDS[command_id] = command
        return {"command": command, "mode": "demo"}
    _verify_response_auth(request)
    endpoint = get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    if (endpoint.get("metadata") or {}).get("response_capable") is not True:
        raise HTTPException(
            status_code=409,
            detail="Endpoint has not advertised response capability",
        )
    if any(port < 1 or port > 65535 for port in payload.protected_ports):
        raise HTTPException(status_code=422, detail="Protected ports must be between 1 and 65535")
    active = [
        command
        for command in list_response_commands(endpoint_id, 10)
        if command["status"] in ("pending", "delivered")
    ]
    if active:
        raise HTTPException(status_code=409, detail="Endpoint already has an active response command")
    command = create_response_command(
        command_id=f"cmd_{uuid.uuid4().hex}",
        endpoint_id=endpoint_id,
        action=payload.action,
        reason=payload.reason,
        requested_by=payload.requested_by,
        parameters={"protected_ports": sorted(set(payload.protected_ports))},
    )
    if not command:
        raise HTTPException(status_code=409, detail="Endpoint already has an active response command")
    return {"command": command}


@app.get("/api/endpoints/{endpoint_id}/commands/pending")
def pending_endpoint_commands(endpoint_id: str, request: Request) -> dict:
    _verify_device_auth(request, endpoint_id)
    if not get_endpoint(endpoint_id):
        raise HTTPException(status_code=404, detail="Endpoint not registered")
    return {"commands": claim_pending_commands(endpoint_id)}


@app.post("/api/endpoints/{endpoint_id}/commands/{command_id}/ack")
def acknowledge_endpoint_command(
    endpoint_id: str,
    command_id: str,
    payload: ResponseCommandAckRequest,
    request: Request,
) -> dict:
    _verify_device_auth(request, endpoint_id)
    command = complete_response_command(
        command_id=command_id,
        endpoint_id=endpoint_id,
        status=payload.status,
        result=payload.result,
        error_message=payload.error_message,
        quarantined=payload.quarantined,
    )
    if not command:
        raise HTTPException(status_code=409, detail="Command is missing or already completed")
    create_notification(
        "endpoint_response", "warning" if payload.quarantined else "info",
        f"Endpoint {command['action']} completed",
        f"{endpoint_id} acknowledged the {command['action']} command.", endpoint_id=endpoint_id,
    )
    if payload.status == "succeeded" and payload.quarantined:
        create_notification(
            "endpoint_contained",
            "warning",
            "Containment acknowledged; verification required",
            f"{endpoint_id} reported containment. Open incidents remain open until reviewed.",
            endpoint_id=endpoint_id,
        )
    return {"command": command}


@app.get("/api/telemetry/events")
def telemetry_events(
    topology: str = Query(default="enterprise_20n"),
    limit: int = Query(default=200, ge=1, le=1000),
    mode: Literal["reality", "demo"] = Query(default="reality"),
) -> dict:
    _resolve_topology(topology)
    if mode == "demo":
        return {"events": _demo_events()[:limit], "mode": "demo"}
    return {"events": get_telemetry_events(topology, limit)}


@app.post("/api/incidents/{incident_id}/resolve")
def resolve_endpoint_incident(incident_id: str, payload: IncidentResolutionRequest, request: Request) -> dict:
    _verify_response_auth(request)
    incident = resolve_incident(incident_id, payload.resolved_by, payload.reason)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    create_notification(
        "incident_resolved", "info", "Incident resolved", incident["summary"],
        endpoint_id=incident["endpoint_id"], incident_id=incident_id,
    )
    return {"incident": incident}


@app.get("/api/notifications")
def notifications(limit: int = Query(default=100, ge=1, le=500)) -> dict:
    rows = list_notifications(limit)
    return {"notifications": rows, "unread_count": sum(1 for row in rows if not row.get("read_at"))}


@app.post("/api/notifications/read")
def mark_all_notifications_read() -> dict:
    mark_notifications_read()
    return {"ok": True}


@app.delete("/api/notifications")
def clear_all_notifications() -> dict:
    return {"ok": True, "cleared": clear_notifications()}


@app.post("/api/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str) -> dict:
    mark_notifications_read(notification_id)
    return {"ok": True}


@app.get("/api/telemetry/status")
def telemetry_status_endpoint(
    topology: str = Query(default="enterprise_20n"),
    mode: Literal["reality", "demo"] = Query(default="reality"),
) -> dict:
    _resolve_topology(topology)
    if mode == "demo":
        events = _demo_events()
        return {
            "topology": topology,
            "source": "clearly_labeled_demo_telemetry",
            "mode": "demo",
            "updated_at": events[0]["timestamp"],
            "event_count": len(events),
            "blocked_events": sum(1 for event in events if event["blocked"]),
            "critical_reaches": 0,
            "connected_count": len(_demo_endpoints(topology)),
            "connected_clients": [],
        }
    filtered = get_telemetry_events(topology, 5000)
    reached_critical = sum(1 for evt in filtered if evt.get("reached_critical"))
    blocked = sum(1 for evt in filtered if evt.get("blocked"))

    client_rollup: Dict[str, Dict[str, Any]] = {}
    for evt in filtered:
        node = str(evt.get("source_node") or "unknown_source")
        bucket = client_rollup.setdefault(
            node,
            {
                "event_count": 0,
                "blocked_events": 0,
                "critical_reaches": 0,
                "last_seen_at": None,
                "last_seen_dt": None,
                "event_types": {},
            },
        )

        bucket["event_count"] += 1
        if evt.get("blocked"):
            bucket["blocked_events"] += 1
        if evt.get("reached_critical"):
            bucket["critical_reaches"] += 1

        event_type = str(evt.get("event_type") or "unknown_event")
        event_types = bucket["event_types"]
        event_types[event_type] = int(event_types.get(event_type, 0)) + 1

        seen_at = _parse_iso_timestamp(evt.get("timestamp"))
        last_seen_dt = bucket.get("last_seen_dt")
        if seen_at and (last_seen_dt is None or seen_at > last_seen_dt):
            bucket["last_seen_dt"] = seen_at
            bucket["last_seen_at"] = seen_at.isoformat()

    now_utc = datetime.now(timezone.utc)
    connected_clients: List[Dict[str, Any]] = []
    for node, stats in client_rollup.items():
        last_seen_dt = stats.get("last_seen_dt")
        minutes_since_last_seen = None
        status = "unknown"

        if isinstance(last_seen_dt, datetime):
            delta = now_utc - last_seen_dt
            minutes_since_last_seen = round(max(0.0, delta.total_seconds()) / 60.0, 2)
            status = "active" if minutes_since_last_seen <= 5 else "idle"

        top_event_types = dict(
            sorted(
                (stats.get("event_types") or {}).items(),
                key=lambda item: (-item[1], item[0]),
            )[:3]
        )

        connected_clients.append(
            {
                "node": node,
                "status": status,
                "event_count": int(stats.get("event_count") or 0),
                "blocked_events": int(stats.get("blocked_events") or 0),
                "critical_reaches": int(stats.get("critical_reaches") or 0),
                "last_seen_at": stats.get("last_seen_at"),
                "minutes_since_last_seen": minutes_since_last_seen,
                "event_types": top_event_types,
            }
        )

    connected_clients.sort(key=lambda item: (-item["event_count"], item["node"]))

    return {
        "topology": topology,
        "source": "persistent_endpoint_telemetry",
        "updated_at": max((str(event.get("timestamp") or "") for event in filtered), default=None),
        "event_count": len(filtered),
        "blocked_events": blocked,
        "critical_reaches": reached_critical,
        "connected_count": len(connected_clients),
        "connected_clients": connected_clients,
    }


@app.post("/api/telemetry/ingest")
def telemetry_ingest(payload: TelemetryIngestRequest, request: Request) -> dict:
    _verify_telemetry_ingest_auth(request)
    _resolve_topology(payload.topology)

    raw_events = [evt.model_dump(exclude_none=True) for evt in payload.events]
    normalized = normalize_events(raw_events, default_topology=payload.topology)
    # Real collectors commonly identify a laptop by hostname while the heartbeat
    # uses a stable endpoint ID. Canonicalise both to the registered endpoint ID.
    registered = list_endpoints(payload.topology)
    by_hostname = {str(row.get("hostname") or "").lower(): row for row in registered}
    by_id = {str(row.get("endpoint_id") or ""): row for row in registered}
    for event in normalized:
        source = str(event.get("source_node") or "")
        endpoint = by_id.get(source) or by_hostname.get(source.lower())
        if endpoint:
            event["source_node"] = endpoint["endpoint_id"]
        if str(event.get("event_type") or "").lower() in {"network_connect_live", "network_connection", "dns_lookup"}:
            upsert_relationship(str(event.get("source_node") or ""), str(event.get("target_node") or ""), payload.topology, "observed_connection", float(event.get("confidence") or 0.6))

    inserted = store_telemetry_events(payload.topology, normalized)
    opened_incidents: List[dict] = []
    for event in normalized:
        endpoint_id = str(event.get("source_node") or "")
        raw = event.get("raw") or {}
        event_type = str(event.get("event_type") or "").lower()
        is_detection = (event_type in {"malware_detected", "defender_detection", "defender_threat_detected"}
                        or "malware" in event_type or bool(raw.get("simulated_detection"))
                        or bool(raw.get("defender_detection")) or bool(raw.get("threat_name")))
        endpoint = by_id.get(endpoint_id) if endpoint_id else None
        if endpoint and endpoint.get("topology") == payload.topology and is_detection:
            source = "simulated" if raw.get("simulated_detection") else "microsoft_defender"
            summary = str(raw.get("threat_name") or raw.get("summary") or "Endpoint threat detection")
            incident = create_incident(endpoint_id, payload.topology, str(event.get("event_id") or ""), source, summary, _incident_severity(event))
            if incident:
                opened_incidents.append(incident)
                create_notification("incident_opened", "critical", f"Affected laptop: {endpoint.get('hostname')}", summary, endpoint_id, incident["incident_id"])
    stored = len(get_telemetry_events(payload.topology, 5000))

    _invalidate_reality_cache(payload.topology)

    return {
        "ingested": inserted,
        "received": len(normalized),
        "stored": stored,
        "source": payload.source,
        "topology": payload.topology,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "confidence": "measured",
        "opened_incidents": opened_incidents,
    }


@app.post("/api/telemetry/load-sample")
def telemetry_load_sample(topology: str = Query(default="enterprise_20n")) -> dict:
    _resolve_topology(topology)
    sample_path = PROJECT_ROOT / "data" / "telemetry" / "sample_events.json"
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample telemetry file not found.")

    with open(sample_path, "r", encoding="utf-8") as f:
        sample = json.load(f)

    sample_events = sample.get("events", [])
    normalized = normalize_events(sample_events, default_topology=topology)

    inserted = store_telemetry_events(topology, normalized)

    _invalidate_reality_cache(topology)

    return {
        "loaded": inserted,
        "source": sample.get("source", "sample"),
        "topology": topology,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/telemetry/ingest-live")
def telemetry_ingest_live(payload: LiveTelemetryIngestRequest) -> dict:
    _resolve_topology(payload.topology)

    script_path = PROJECT_ROOT / "tools" / "live_laptop_telemetry.ps1"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Live telemetry script not found.")

    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
        "-IngestUrl",
        "http://127.0.0.1:8020/api/telemetry/ingest",
        "-Topology",
        payload.topology,
        "-Mode",
        payload.mode,
        "-MaxConnections",
        str(payload.max_connections),
        "-MaxProcesses",
        str(payload.max_processes),
    ]

    runtime_env = os.environ.copy()
    ingest_api_key = _get_telemetry_ingest_api_key()
    if ingest_api_key:
        runtime_env["ONYX_TELEMETRY_INGEST_API_KEY"] = ingest_api_key

    try:
        proc = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=150,
            check=False,
            env=runtime_env,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Live telemetry ingest timed out.") from exc

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()

    if proc.returncode != 0:
        failure_detail = stderr or stdout or "Live telemetry ingest script failed."
        raise HTTPException(status_code=500, detail=failure_detail[-1200:])

    parsed_summary = _extract_json_object(stdout) or {}
    status_snapshot = telemetry_status_endpoint(payload.topology)

    _invalidate_reality_cache(payload.topology)

    return {
        "status": "ok",
        "mode": payload.mode,
        "topology": payload.topology,
        "summary": {
            "mode": parsed_summary.get("mode", payload.mode),
            "source": parsed_summary.get("source") or status_snapshot.get("source"),
            "ingested": parsed_summary.get("ingested", status_snapshot.get("event_count", 0)),
            "event_count": status_snapshot.get("event_count", 0),
            "blocked_events": status_snapshot.get("blocked_events", 0),
            "critical_reaches": status_snapshot.get("critical_reaches", 0),
            "updated_at": status_snapshot.get("updated_at"),
        },
        "warnings": stderr or None,
    }


@app.post("/api/evidence-bundle")
def evidence_bundle(payload: EvidenceBundleRequest) -> dict:
    return _build_evidence_bundle(
        topology=payload.topology,
        n_episodes=payload.n_episodes,
        n_baseline=payload.n_baseline,
        n_eval_per_patch=payload.n_eval_per_patch,
        telemetry_weight=payload.telemetry_weight,
        comparison_source=payload.comparison_source,
    )


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "topology_files": {name: (PROJECT_ROOT / rel_path).exists() for name, rel_path in TOPOLOGIES.items()},
        "cve_dataset": (PROJECT_ROOT / CVE_PATH).exists(),
        "scenarios": (PROJECT_ROOT / SCENARIO_CONFIG_PATH).exists(),
        "marl_results": (PROJECT_ROOT / MARL_RESULTS_PATH).exists(),
        "report_html": (PROJECT_ROOT / REPORT_HTML_PATH).exists(),
        "capabilities": {
            "response_controls": _response_controls_enabled(),
            "response_controls_default": "disabled",
        },
    }


@app.get("/api/capabilities")
def capabilities() -> dict:
    return {
        "response_controls": _response_controls_enabled(),
        "response_controls_default": "disabled",
    }


@app.get("/api/topologies")
def topologies() -> dict:
    return {"topologies": TOPOLOGIES}


@app.get("/api/status")
def status(
    topology: str = Query(default="enterprise_20n"),
    mode: Literal["reality", "demo"] = Query(default="reality"),
) -> dict:
    payload = {
        "red_agent": (PROJECT_ROOT / AGENT_PATH).exists(),
        "gnn_model": (PROJECT_ROOT / "checkpoints/gnn_world_model.pt").exists(),
        "marl_results": (PROJECT_ROOT / MARL_RESULTS_PATH).exists(),
        "patch_report": (PROJECT_ROOT / PATCH_RESULTS_PATH).exists(),
        "morning_report": (PROJECT_ROOT / REPORT_HTML_PATH).exists(),
    }

    topology_key = topology if topology in TOPOLOGIES else "enterprise_20n"
    try:
        topology_path = _resolve_topology(topology_key)
        graph = load_topology(str(PROJECT_ROOT / topology_path))
        cve_db = load_cve_database(str(PROJECT_ROOT / CVE_PATH))
        tag_graph(graph, cve_db)

        payload.update(
            {
                "topology": topology_key,
                "total_nodes": int(graph.num_nodes),
                "total_edges": int(graph.num_edges),
                "total_cves": int(sum(node.num_vulns for node in graph.nodes)),
                "critical_assets": int(len(graph.critical_assets)),
            }
        )
    except Exception as exc:
        logger.warning("Failed to compute status metrics for topology '%s': %s", topology_key, exc)
        payload.update(
            {
                "topology": topology_key,
                "total_nodes": 0,
                "total_edges": 0,
                "total_cves": 0,
                "critical_assets": 0,
            }
        )

    endpoint_rows = _demo_endpoints(topology_key) if mode == "demo" else list_endpoints(topology_key)
    payload["mode"] = mode
    payload["connected_endpoints"] = len(endpoint_rows)
    payload["active_endpoints"] = (
        len(endpoint_rows)
        if mode == "demo"
        else sum(
            1
            for endpoint in endpoint_rows
            if (
                datetime.now(timezone.utc)
                - (
                    _parse_iso_timestamp(endpoint.get("last_seen_at"))
                    or datetime.min.replace(tzinfo=timezone.utc)
                )
            ).total_seconds()
            <= 30
        )
    )
    sim_results = (cache.get("sim_results_by_mode") or {}).get(
        _scoped_cache_key(mode, topology)
    ) or {}
    if sim_results:
        payload["last_simulation"] = {
            "timestamp": sim_results.get("data_freshness_at") or (datetime.utcnow().isoformat() + "Z"),
            "episodes": int(sim_results.get("n_episodes") or 0),
            "success_rate": float(sim_results.get("success_rate") or 0.0),
            "source": sim_results.get("data_source") or sim_results.get("requested_data_source") or "simulation",
        }

    return payload


@app.get("/api/topology/{topology_key}")
def topology_details(
    topology_key: str,
    mode: Literal["reality", "demo"] = Query(default="reality"),
) -> dict:
    topology_path = _resolve_topology(topology_key)
    graph = load_topology(str(PROJECT_ROOT / topology_path))
    cve_db = load_cve_database(str(PROJECT_ROOT / CVE_PATH))
    tag_graph(graph, cve_db)

    nodes = []
    for node in graph.nodes:
        nodes.append(
            {
                "node_id": node.node_id,
                "node_type": node.node_type,
                "software": node.software,
                "version": node.version,
                "num_vulns": node.num_vulns,
                "max_cvss": round(node.max_cvss, 1),
                "severity": node.vulnerabilities[0].severity_label if node.vulnerabilities else "NONE",
                "is_critical_asset": node.is_critical_asset,
                "is_entry_point": node.is_entry_point,
            }
        )

    edges = []
    for edge in graph.edges:
        edges.append(
            {
                "source": edge.source,
                "target": edge.target,
                "connection_type": edge.connection_type,
                "permission_level": edge.permission_level,
                "has_firewall": edge.has_firewall,
            }
        )

    return {
        "mode": mode,
        "summary": {
            "num_nodes": graph.num_nodes,
            "num_edges": graph.num_edges,
            "critical_assets": len(graph.critical_assets),
            "total_cves": int(sum(node.num_vulns for node in graph.nodes)),
        },
        "nodes": nodes,
        "edges": edges,
    }


@app.post("/api/simulate")
def simulate(payload: SimulationRequest) -> dict:
    topology_path = _resolve_topology(payload.topology)
    # Attack Simulation is intentionally isolated from Reality data.  Both UI
    # modes execute the same frozen world model; live endpoint events remain
    # incident evidence and are never interpreted as simulated attacks.
    result = _run_attack_analysis(
        topology_path=topology_path,
        topology_key=payload.topology,
        n_episodes=payload.n_episodes,
        seed=payload.seed,
        data_source="simulation",
        telemetry_weight=payload.telemetry_weight,
    )
    result["requested_data_source"] = "simulation"
    result["data_source"] = "simulation"
    result["data_source_note"] = "Offline world-model run; real endpoint telemetry was not used as attack input."
    result["measurement_type"] = "simulated_counterfactual"
    result["research_only"] = True
    result["summary"] = _build_result_summary(result)
    replay = _build_replay(result, payload.topology)
    replay["evidence"] = _build_world_model_evidence(
        result,
        payload.topology,
        payload.n_episodes,
        payload.seed,
    )
    simulation_id = f"SIM-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    replay["simulation_id"] = simulation_id
    result["simulation_id"] = simulation_id
    save_simulation_run(simulation_id, payload.mode, result, replay)
    result["replay"] = replay
    cache["sim_results"] = result
    cache["last_replay"] = replay
    scoped_key = _scoped_cache_key(payload.mode, payload.topology)
    cache["sim_results_by_mode"][scoped_key] = result
    cache["last_replay_by_mode"][scoped_key] = replay
    return result


@app.get("/api/simulations/saved")
def saved_simulations(limit: int = Query(default=30, ge=1, le=100)) -> dict:
    return {"runs": list_simulation_runs(limit)}


@app.get("/api/simulations/saved/{simulation_id}")
def saved_simulation(simulation_id: str) -> dict:
    run = get_simulation_run(simulation_id)
    if not run:
        raise HTTPException(status_code=404, detail="Saved simulation not found")
    return run


@app.post("/api/simulate/seed-sweep")
def simulate_seed_sweep(payload: SimulationSeedSweepRequest) -> dict:
    if not payload.seeds:
        raise HTTPException(status_code=400, detail="At least one seed is required.")

    if len(payload.seeds) > 20:
        raise HTTPException(status_code=400, detail="Seed sweep supports up to 20 seeds per request.")

    topology_path = _resolve_topology(payload.topology)
    result = _run_seed_sweep(
        topology_path=topology_path,
        topology_key=payload.topology,
        n_episodes=payload.n_episodes,
        seeds=[int(seed) for seed in payload.seeds],
        data_source=payload.data_source,
        telemetry_weight=payload.telemetry_weight,
    )
    return result


@app.get("/api/scenarios")
def scenarios() -> dict:
    rows = _load_scenarios()
    return {"scenarios": rows}


@app.post("/api/run-scenario/{scenario_id}")
def run_scenario(scenario_id: str, payload: ScenarioRunRequest) -> dict:
    rows = _load_scenarios()
    scenario = next((row for row in rows if row.get("id") == scenario_id), None)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Unknown scenario: {scenario_id}")

    topology = scenario.get("topology", "enterprise_20n")
    topology_path = _resolve_topology(topology)
    scenario_data_source = scenario.get("data_source", payload.data_source)
    result = _run_attack_analysis(
        topology_path=topology_path,
        topology_key=topology,
        n_episodes=payload.n_episodes,
        seed=int(scenario.get("seed", 42)),
        data_source=scenario_data_source,
        telemetry_weight=payload.telemetry_weight,
    )
    replay = _build_replay(result, topology)
    result["summary"] = _build_result_summary(result)
    cache["sim_results"] = result
    cache["last_replay"] = replay

    return {
        "scenario": scenario,
        "simulation": result,
        "replay": replay,
    }


@app.get("/api/replay/latest")
def replay_latest(
    topology: str = Query(default="enterprise_20n"),
    mode: Literal["reality", "demo"] = Query(default="reality"),
) -> dict:
    _resolve_topology(topology)
    replay = (cache.get("last_replay_by_mode") or {}).get(
        _scoped_cache_key(mode, topology)
    )
    return {"replay": replay, "mode": mode}


@app.post("/api/risk-scorecard")
def risk_scorecard(payload: ScorecardRequest) -> dict:
    topology_path = _resolve_topology(payload.topology)
    sim_result = cache.get("sim_results")
    if not sim_result:
        sim_result = _run_attack_analysis(
            topology_path=topology_path,
            topology_key=payload.topology,
            n_episodes=payload.n_episodes,
            seed=42,
            data_source=payload.data_source,
            telemetry_weight=payload.telemetry_weight,
        )
        cache["sim_results"] = sim_result

    patch_rows = cache.get("patch_results")
    if not patch_rows:
        patch_file = PROJECT_ROOT / PATCH_RESULTS_PATH
        if patch_file.exists():
            with open(patch_file, "r", encoding="utf-8") as f:
                patch_rows = json.load(f)
                cache["patch_results"] = patch_rows

    baseline_rate = float(sim_result.get("success_rate", 0.0))
    estimate = _patched_estimate(baseline_rate, payload.top_k_patches, patch_rows or [])

    return {
        "topology": payload.topology,
        "baseline_success_rate": round(baseline_rate, 4),
        "patched_success_rate": estimate["patched_success_rate"],
        "risk_reduction_pp": estimate["risk_reduction_pp"],
        "top_k_patches": payload.top_k_patches,
        "top_actions": estimate["top_actions"],
        "data_source": sim_result.get("data_source", "simulation"),
        "requested_data_source": sim_result.get("requested_data_source", payload.data_source),
        "data_source_note": sim_result.get("data_source_note"),
        "hybrid": sim_result.get("hybrid"),
        "confidence": "estimated_from_simulation_impact",
        "summary": _build_result_summary(sim_result),
    }


@app.post("/api/patch-optimize")
def patch_optimize(payload: PatchRequest) -> dict:
    generated = _generate_patch_results(
        topology_key=payload.topology,
        n_baseline=payload.n_baseline,
        n_eval_per_patch=payload.n_eval_per_patch,
        data_source=payload.data_source,
        telemetry_weight=payload.telemetry_weight,
    )
    cache["patch_results_by_mode"][_scoped_cache_key(payload.mode, payload.topology)] = generated["results"]
    cache["patch_results"] = generated["results"]
    cache["cost_ranking"] = None
    cache["explainability"] = None
    return {
        "results": generated["results"],
        "data_source": generated["data_source"],
        "requested_data_source": generated["requested_data_source"],
        "data_source_note": generated["data_source_note"],
        "data_freshness_at": generated.get("data_freshness_at"),
        "confidence": generated.get("confidence") or _confidence_from_source(generated.get("data_source")),
        "summary": _build_result_summary(
            {
                "success_rate": generated.get("baseline_success_rate", 0.0),
                "n_episodes": generated.get("n_baseline", payload.n_baseline),
                "total_unique_paths": len(generated.get("results", [])),
                "data_source": generated.get("data_source"),
                "data_source_note": generated.get("data_source_note"),
                "successful_runs": generated.get("successful_runs"),
            }
        ),
    }


@app.get("/api/cost-model")
def cost_model() -> dict:
    path = PROJECT_ROOT / COST_MODEL_PATH
    if not path.exists():
        return {"model": {}}
    with open(path, "r", encoding="utf-8") as f:
        return {"model": json.load(f)}


@app.put("/api/cost-model")
def update_cost_model(payload: CostModelUpdateRequest, request: Request) -> dict:
    _verify_response_auth(request)
    path = PROJECT_ROOT / COST_MODEL_PATH
    existing = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    allowed_node_types = {"server", "workstation", "router", "firewall", "database", "cloud"}
    invalid = set(payload.node_type_effort_hours) - allowed_node_types
    if invalid:
        raise HTTPException(status_code=422, detail=f"Unsupported node types: {', '.join(sorted(invalid))}")
    hours = {**existing.get("node_type_effort_hours", {}), **payload.node_type_effort_hours}
    if any(value <= 0 or value > 500 for value in hours.values()):
        raise HTTPException(status_code=422, detail="Effort hours must be between 0 and 500")
    model = {
        **existing,
        "node_type_effort_hours": hours,
        "critical_asset_multiplier": payload.critical_asset_multiplier,
    }
    temporary_path = path.with_suffix(".tmp")
    with open(temporary_path, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2)
        f.write("\n")
    temporary_path.replace(path)
    cache["cost_ranking"] = None
    return {"model": model}


@app.post("/api/patch-cost-ranking")
def patch_cost_ranking(payload: CostRankingRequest) -> dict:
    patch_rows = cache.get("patch_results")
    if not patch_rows:
        patch_file = PROJECT_ROOT / PATCH_RESULTS_PATH
        if patch_file.exists():
            with open(patch_file, "r", encoding="utf-8") as f:
                patch_rows = json.load(f)
                cache["patch_results"] = patch_rows
    if not patch_rows:
        raise HTTPException(status_code=400, detail="Patch results are missing. Run patch optimizer first.")

    topology_path = _resolve_topology(payload.topology)
    ranked = rank_cost_aware_patches(
        patch_results=patch_rows,
        topology_path=str(PROJECT_ROOT / topology_path),
        cve_path=str(PROJECT_ROOT / CVE_PATH),
        cost_model_path=str(PROJECT_ROOT / COST_MODEL_PATH),
        top_k=payload.top_k,
    )
    cache["cost_ranking"] = ranked
    return ranked


@app.post("/api/explainability")
def explainability(payload: ExplainabilityRequest) -> dict:
    ranked = cache.get("cost_ranking")
    if not ranked:
        ranking = patch_cost_ranking(CostRankingRequest(topology=payload.topology, top_k=max(12, payload.top_n)))
        ranked = ranking

    sim_result = cache.get("sim_results")
    topology_path = _resolve_topology(payload.topology)
    if not sim_result:
        sim_result = _run_attack_analysis(
            topology_path=topology_path,
            topology_key=payload.topology,
            n_episodes=700,
            seed=42,
            data_source="simulation",
            telemetry_weight=0.4,
        )
        cache["sim_results"] = sim_result

    baseline_rate = float(sim_result.get("success_rate", 0.0))
    cards = build_explanation_cards(
        cost_recommendations=ranked.get("top_recommendations", []),
        sim_results=sim_result,
        baseline_success_rate=baseline_rate,
        top_n=payload.top_n,
    )
    cache["explainability"] = cards
    return {"cards": cards}


@app.get("/api/patch-results")
def patch_results(
    topology: str = Query(default="enterprise_20n"),
    data_source: str = Query(default="simulation"),
    telemetry_weight: float = Query(default=0.4, ge=0.0, le=1.0),
    n_baseline: int = Query(default=200, ge=50, le=2000),
    n_eval_per_patch: int = Query(default=50, ge=10, le=500),
    refresh: bool = Query(default=False),
    mode: Literal["reality", "demo"] = Query(default="reality"),
) -> dict:
    scoped_key = _scoped_cache_key(mode, topology)
    cached = (cache.get("patch_results_by_mode") or {}).get(scoped_key)
    if cached and not refresh:
        ranked = rank_cost_aware_patches(
            patch_results=cached,
            topology_path=str(PROJECT_ROOT / _resolve_topology(topology)),
            cve_path=str(PROJECT_ROOT / CVE_PATH),
            cost_model_path=str(PROJECT_ROOT / COST_MODEL_PATH),
            top_k=1000,
        )
        return {
            "results": ranked["all_recommendations"] or cached,
            "data_source": "cache",
            "requested_data_source": data_source,
            "data_source_note": f"in_memory_{mode}_cache",
            "confidence": "estimated",
            "mode": mode,
        }

    generated = _generate_patch_results(
        topology_key=topology,
        n_baseline=n_baseline,
        n_eval_per_patch=n_eval_per_patch,
        data_source=data_source,
        telemetry_weight=telemetry_weight,
    )
    cache["patch_results_by_mode"][scoped_key] = generated["results"]
    ranked = rank_cost_aware_patches(
        patch_results=generated["results"],
        topology_path=str(PROJECT_ROOT / _resolve_topology(topology)),
        cve_path=str(PROJECT_ROOT / CVE_PATH),
        cost_model_path=str(PROJECT_ROOT / COST_MODEL_PATH),
        top_k=1000,
    )
    if ranked["all_recommendations"]:
        generated["results"] = ranked["all_recommendations"]
    generated["mode"] = mode
    return generated


@app.get("/api/marl-results")
def marl_results() -> dict:
    path = PROJECT_ROOT / MARL_RESULTS_PATH
    return {"results": _load_json_array(path)}


@app.post("/api/generate-report")
def make_report(payload: ReportRequest) -> dict:
    topology_path = _resolve_topology(payload.topology)

    patch_results_data: Optional[list] = cache.get("patch_results")
    if not patch_results_data:
        patch_file = PROJECT_ROOT / PATCH_RESULTS_PATH
        if patch_file.exists():
            with open(patch_file, "r", encoding="utf-8") as f:
                patch_results_data = json.load(f)

    if not patch_results_data:
        raise HTTPException(status_code=400, detail="Patch results are missing. Run patch optimizer first.")

    sim_results = cache.get("sim_results") or {}
    top_paths = sim_results.get("top_paths")
    n_episodes = sim_results.get("n_episodes", 1000)
    report_source = sim_results.get("data_source") or sim_results.get("requested_data_source") or "simulation"
    report_confidence = _confidence_from_source(report_source)

    html = generate_report(
        patch_results=patch_results_data,
        topology_name=Path(topology_path).stem,
        n_episodes=n_episodes,
        top_paths=top_paths,
        output_html=str(PROJECT_ROOT / REPORT_HTML_PATH),
        output_pdf=str(PROJECT_ROOT / REPORT_PDF_PATH),
    )

    return {
        "html": html,
        "html_path": REPORT_HTML_PATH,
        "pdf_path": REPORT_PDF_PATH,
        "top_fix": patch_results_data[0] if patch_results_data else None,
        "data_source": report_source,
        "confidence": report_confidence,
        "data_freshness_at": sim_results.get("data_freshness_at"),
        "summary": _build_result_summary(sim_results) if sim_results else None,
    }


@app.get("/api/report-html")
def report_html() -> dict:
    path = PROJECT_ROOT / REPORT_HTML_PATH
    if not path.exists():
        return {"html": ""}
    with open(path, "r", encoding="utf-8") as f:
        return {"html": f.read()}


@app.get("/api/reports/{user_id}")
def get_reports(user_id: str) -> dict:
    """Get report history for a user."""
    # Return mock report history with realistic data
    reports = [
        {
            "id": "report_001",
            "name": "Enterprise Ransomware Scenario",
            "topology": "enterprise_20n",
            "successRate": 99.5,
            "created": "Apr 4, 2026",
        },
        {
            "id": "report_002",
            "name": "Cloud Pivot Attack Analysis",
            "topology": "cloud_hybrid_30n",
            "successRate": 87.3,
            "created": "Apr 3, 2026",
        },
        {
            "id": "report_003",
            "name": "Small Office Quick Demo",
            "topology": "small_office_10n",
            "successRate": 92.1,
            "created": "Apr 2, 2026",
        },
    ]
    return {"reports": reports}


# ============ USER PREFERENCES ============


@app.get("/api/preferences/{user_id}")
def get_preferences(user_id: str) -> dict:
    """Get user preferences."""
    prefs = get_user_preference(user_id)
    return {"preferences": prefs}


@app.post("/api/preferences")
def update_preferences(payload: UserPreferenceRequest) -> dict:
    """Update user preferences."""
    prefs = set_user_preference(
        user_id=payload.user_id,
        default_topology=payload.default_topology,
        default_episodes=payload.default_episodes,
        cost_model=payload.cost_model,
    )
    return {"preferences": prefs}


# ============ SCENARIO HISTORY ============


@app.get("/api/history/{user_id}")
def get_history(user_id: str, limit: int = 20) -> dict:
    """Get scenario execution history."""
    history = get_scenario_history(user_id, limit)
    return {"history": history}


@app.post("/api/history/log")
def log_execution(
    user_id: str,
    scenario_id: str,
    topology: str,
    n_episodes: int,
    success_rate: float,
    risk_reduction_pp: float,
    execution_time_seconds: float = 0.0,
) -> dict:
    """Log a scenario execution."""
    execution_id = log_scenario_execution(
        user_id=user_id,
        scenario_id=scenario_id,
        topology=topology,
        n_episodes=n_episodes,
        success_rate=success_rate,
        risk_reduction_pp=risk_reduction_pp,
        execution_time_seconds=execution_time_seconds,
    )
    return {"execution_id": execution_id, "timestamp": datetime.now().isoformat()}


# ============ COST MODEL CUSTOMIZATION (IMPORTANT) ============


@app.post("/api/cost-models")
def create_cost_model(payload: CostModelRequest) -> dict:
    """Create or update a cost model."""
    model_id = save_cost_model(
        user_id=payload.user_id,
        model_name=payload.model_name,
        model_config=payload.config,
        is_active=payload.is_active,
    )
    return {
        "model_id": model_id,
        "model_name": payload.model_name,
        "is_active": payload.is_active,
        "created_at": datetime.now().isoformat(),
    }


@app.get("/api/cost-models/{user_id}")
def list_cost_models(user_id: str) -> dict:
    """List all cost models for a user."""
    models = get_cost_models(user_id)
    active_model = get_active_cost_model(user_id)
    return {
        "models": models,
        "active_model": active_model,
        "count": len(models),
    }


@app.post("/api/cost-models/{model_id}/activate")
def activate_cost_model(model_id: int, user_id: str) -> dict:
    """Activate a cost model."""
    models = get_cost_models(user_id)
    model = next((m for m in models if m["id"] == model_id), None)
    if not model:
        raise HTTPException(status_code=404, detail="Cost model not found")

    save_cost_model(
        user_id=user_id,
        model_name=model["model_name"],
        model_config=model["model_config"],
        is_active=True,
    )

    return {"activated": model_id, "model_name": model["model_name"]}


# ============ SCENARIO BUILDER (IMPORTANT) ============


@app.post("/api/scenarios/build")
def build_scenario(payload: ScenarioBuilderRequest) -> dict:
    """Create a new custom scenario."""
    scenario_id = str(uuid.uuid4())[:8]

    scenario_data = {
        "id": scenario_id,
        "name": payload.scenario_name,
        "topology": payload.topology,
        "description": payload.description,
        "seed": payload.seed,
        "entry_points": payload.entry_points,
        "target_nodes": payload.target_nodes,
        "created_at": datetime.now().isoformat(),
    }

    # Load existing scenarios and add new one
    path = PROJECT_ROOT / SCENARIO_CONFIG_PATH
    scenarios = []
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            payload_data = json.load(f)
            scenarios = payload_data.get("scenarios", [])

    scenarios.append(scenario_data)

    # Save updated scenarios
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"scenarios": scenarios}, f, indent=2)

    return {
        "scenario_id": scenario_id,
        "scenario": scenario_data,
        "message": "Scenario created successfully",
    }


@app.get("/api/scenarios/custom/{user_id}")
def get_custom_scenarios(user_id: str) -> dict:
    """Get custom scenarios (placeholder - could be extended to store per-user)."""
    scenarios = _load_scenarios()
    custom = [s for s in scenarios if s.get("created_at")]
    return {"custom_scenarios": custom}


# ============ MODEL RETRAINING (IMPORTANT) ============


@app.post("/api/training/jobs")
def create_training_job_endpoint(payload: TrainingJobRequest) -> dict:
    """Create a new model retraining job."""
    job_id = f"job_{str(uuid.uuid4())[:12]}"

    if payload.model_type not in ["gnn", "red_agent", "blue_agent"]:
        raise HTTPException(
            status_code=400,
            detail='model_type must be "gnn", "red_agent", or "blue_agent"',
        )

    create_training_job(
        job_id=job_id,
        model_type=payload.model_type,
        config=payload.config,
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "model_type": payload.model_type,
        "created_at": datetime.now().isoformat(),
    }


@app.get("/api/training/jobs/{job_id}")
def get_training_job_status(job_id: str) -> dict:
    """Get status of a training job."""
    job = get_training_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")

    return {"job": job}


@app.post("/api/training/jobs/{job_id}/start")
def start_training_job(job_id: str) -> dict:
    """Start a training job (in background)."""
    job = get_training_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")

    update_training_job(job_id, status="running", progress_percent=5)

    # In production, this would trigger a background celery task or similar
    # For now, just mark it as running
    return {
        "job_id": job_id,
        "status": "running",
        "message": "Training job started. Check progress with /api/training/jobs/{job_id}",
    }


@app.post("/api/training/jobs/{job_id}/cancel")
def cancel_training_job(job_id: str) -> dict:
    """Cancel a training job."""
    job = get_training_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")

    if job["status"] == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel completed job")

    update_training_job(job_id, status="cancelled")

    return {"job_id": job_id, "status": "cancelled"}


# ============ MONITORING & METRICS ============


@app.get("/api/metrics")
def get_api_metrics() -> dict:
    """Get API metrics and usage statistics."""
    metrics = get_metrics()
    return {"metrics": metrics}


@app.get("/api/logs")
def get_logs(limit: int = 50, hours: int = 24) -> dict:
    """Get API request logs."""
    logs = get_request_logs(limit, hours)
    return {"logs": logs}


@app.get("/api/health/detailed")
def detailed_health() -> dict:
    """Get detailed health status including database and metrics."""
    try:
        metrics = get_metrics()
        return {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0",
            "metrics": metrics,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
