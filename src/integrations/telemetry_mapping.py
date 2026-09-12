"""Normalize external telemetry and map it into Onyx analysis shapes."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_event(raw: Dict[str, Any], default_topology: str) -> Dict[str, Any]:
    source_node = (
        raw.get("source_node")
        or raw.get("src")
        or raw.get("host")
        or raw.get("source")
        or "unknown_source"
    )
    target_node = (
        raw.get("target_node")
        or raw.get("dst")
        or raw.get("destination")
        or raw.get("target")
        or source_node
    )
    cve_id = (raw.get("cve_id") or raw.get("vulnerability") or raw.get("cve") or "UNKNOWN-CVE").upper()
    event_type = (raw.get("event_type") or raw.get("type") or "attack_event").lower()
    timestamp = raw.get("timestamp") or _utc_now_iso()
    topology = raw.get("topology") or default_topology

    cvss_score = _to_float(raw.get("cvss_score") or raw.get("severity_score") or raw.get("cvss"), 0.0)
    confidence_value = raw.get("confidence")
    if confidence_value is None:
        confidence_value = raw.get("signal_confidence")
    confidence = _to_float(confidence_value, 0.7)
    was_blocked = bool(raw.get("blocked") or raw.get("was_blocked") or False)
    reached_critical = bool(raw.get("reached_critical") or raw.get("critical_asset_hit") or False)

    original_raw = raw.get("raw")
    if not isinstance(original_raw, dict):
        original_raw = {key: value for key, value in raw.items() if key != "raw"}
    canonical = json.dumps(original_raw, sort_keys=True, separators=(",", ":"), default=str)
    generated_id = "evt_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]

    return {
        "event_id": raw.get("event_id") or raw.get("id") or generated_id,
        "timestamp": timestamp,
        "topology": topology,
        "source_node": str(source_node),
        "target_node": str(target_node),
        "event_type": event_type,
        "cve_id": str(cve_id),
        "cvss_score": round(cvss_score, 2),
        "confidence": max(0.0, min(1.0, confidence)),
        "blocked": was_blocked,
        "reached_critical": reached_critical,
        "raw": original_raw,
    }


def normalize_events(raw_events: List[Dict[str, Any]], default_topology: str) -> List[Dict[str, Any]]:
    return [normalize_event(item, default_topology) for item in raw_events]


def build_attack_analysis_from_events(
    normalized_events: List[Dict[str, Any]],
    n_episodes: int,
    top_k_paths: int = 20,
) -> Dict[str, Any]:
    if not normalized_events:
        return {
            "edge_frequency": {},
            "node_frequency": {},
            "top_paths": [],
            "top_paths_returned": 0,
            "total_unique_paths": 0,
            "success_rate": 0.0,
            "successful_runs": 0,
            "failed_runs": 0,
            "evaluation_runs": 0,
            "n_episodes": n_episodes,
            "confidence": "measured",
            "data_source": "telemetry",
            "data_source_note": "telemetry_events_empty",
            "data_freshness_at": _utc_now_iso(),
        }

    edge_counter: Counter = Counter()
    node_counter: Counter = Counter()
    path_counter: Counter = Counter()

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for event in normalized_events:
        key = event.get("event_id") or event["timestamp"]
        grouped[str(key)].append(event)

    observed_critical_reaches = 0
    projected_risk_total = 0.0
    sequences = []

    for _, events in grouped.items():
        ordered = sorted(events, key=lambda x: str(x.get("timestamp", "")))
        path_nodes: List[str] = []
        for evt in ordered:
            src = evt["source_node"]
            dst = evt["target_node"]
            if not path_nodes:
                path_nodes.append(src)
            if path_nodes[-1] != dst:
                path_nodes.append(dst)
            edge_counter[(src, dst)] += 1
            node_counter[dst] += 1

        # A critical reach is observed success. Defender detections without a
        # crown-jewel reach still represent evidence of compromise, so project
        # their risk rather than reporting a misleading 0% simulation rate.
        evidence_score = 0.0
        for evt in ordered:
            raw = evt.get("raw") or {}
            text = " ".join(str(raw.get(key) or "") for key in ("path", "threat_name", "summary")).lower()
            if evt.get("reached_critical") or raw.get("critical_asset") or raw.get("critical_reach"):
                evidence_score = max(evidence_score, 1.0)
            elif any(term in text for term in ("severity: severe", "severity: high", "trojan", "ransomware", "backdoor")):
                evidence_score = max(evidence_score, 0.65)
            elif evt.get("event_type") == "malware_detected" or raw.get("defender_detection"):
                evidence_score = max(evidence_score, 0.25)
        if evidence_score >= 1.0:
            observed_critical_reaches += 1
        projected_risk_total += evidence_score

        if path_nodes:
            sequences.append(path_nodes)
            path_counter[" → ".join(path_nodes)] += 1

    total = max(1, len(sequences))
    edge_freq = {f"{src}||{dst}": count / total for (src, dst), count in edge_counter.items()}
    node_freq = {node: count / total for node, count in node_counter.items()}

    requested_top_k = max(1, int(top_k_paths))
    total_unique_paths = len(path_counter)

    top_paths = [
        {
            "path": path,
            "count": count,
            "frequency": round(count / total, 4),
        }
        for path, count in path_counter.most_common(requested_top_k)
    ]

    success_rate = round(min(1.0, projected_risk_total / total), 4)
    projected_successes = int(round(success_rate * n_episodes))
    return {
        "edge_frequency": dict(sorted(edge_freq.items(), key=lambda x: -x[1])),
        "node_frequency": dict(sorted(node_freq.items(), key=lambda x: -x[1])),
        "top_paths": top_paths,
        "top_paths_returned": len(top_paths),
        "total_unique_paths": total_unique_paths,
        "success_rate": success_rate,
        "successful_runs": projected_successes,
        "failed_runs": max(0, n_episodes - projected_successes),
        "evaluation_runs": total,
        "n_episodes": n_episodes,
        "confidence": "measured" if observed_critical_reaches else "estimated",
        "data_source": "telemetry",
        "data_source_note": "telemetry_observed_critical_reach" if observed_critical_reaches else "telemetry_conditioned_risk_projection",
        "data_freshness_at": _utc_now_iso(),
    }


def build_patch_results_from_events(normalized_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not normalized_events:
        return []

    grouped: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for event in normalized_events:
        key = (event["target_node"], event["cve_id"])
        grouped[key].append(event)

    total = max(1, len(normalized_events))
    rows: List[Dict[str, Any]] = []

    for (node_id, cve_id), events in grouped.items():
        exposure_ratio = len(events) / total
        avg_cvss = sum(evt.get("cvss_score", 0.0) for evt in events) / max(1, len(events))
        critical_hits = sum(1 for evt in events if evt.get("reached_critical"))

        baseline = 0.8
        impact = min(0.5, exposure_ratio * 0.6 + critical_hits * 0.03 + (avg_cvss / 10.0) * 0.08)
        patched = max(0.0, baseline - impact)

        rows.append(
            {
                "node_id": node_id,
                "cve_id": cve_id,
                "node_type": "unknown",
                "is_critical_asset": critical_hits > 0,
                "cvss_score": round(avg_cvss, 2),
                "cvss_severity": "HIGH" if avg_cvss >= 7.0 else "MEDIUM" if avg_cvss >= 4.0 else "LOW",
                "attack_vector": "telemetry-observed",
                "baseline_success_rate": round(baseline, 4),
                "patched_success_rate": round(patched, 4),
                "simulation_impact": round(impact, 4),
                "simulation_rank": None,
                "cvss_rank": None,
                "description": "Derived from telemetry event frequency and critical-asset hits.",
            }
        )

    rows.sort(key=lambda x: -x["simulation_impact"])
    for i, row in enumerate(rows):
        row["simulation_rank"] = i + 1

    cvss_sorted = sorted(rows, key=lambda x: -x["cvss_score"])
    for i, row in enumerate(cvss_sorted):
        row["cvss_rank"] = i + 1

    rows.sort(key=lambda x: -x["simulation_impact"])
    return rows
