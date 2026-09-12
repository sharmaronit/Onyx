from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from src.graph.topology_loader import load_topology
from src.graph.cve_tagger import load_cve_database, tag_graph


DEFAULT_MODEL = {
    "node_type_effort_hours": {
        "server": 6.0,
        "workstation": 2.5,
        "router": 4.5,
        "firewall": 5.5,
        "database": 8.0,
        "cloud": 3.5,
    },
    "critical_asset_multiplier": 1.7,
    "severity_effort_multiplier": {
        "CRITICAL": 1.25,
        "HIGH": 1.15,
        "MEDIUM": 1.0,
        "LOW": 0.9,
        "NONE": 1.0,
    },
}


def load_cost_model(path: Optional[str] = None) -> dict:
    if not path:
        return DEFAULT_MODEL
    p = Path(path)
    if not p.exists():
        return DEFAULT_MODEL
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Keep defaults for missing keys.
    merged = dict(DEFAULT_MODEL)
    merged.update(data)
    merged["node_type_effort_hours"] = {
        **DEFAULT_MODEL["node_type_effort_hours"],
        **data.get("node_type_effort_hours", {}),
    }
    merged["severity_effort_multiplier"] = {
        **DEFAULT_MODEL["severity_effort_multiplier"],
        **data.get("severity_effort_multiplier", {}),
    }
    return merged


def rank_cost_aware_patches(
    patch_results: List[dict],
    topology_path: str,
    cve_path: str,
    cost_model_path: Optional[str] = None,
    top_k: int = 15,
) -> Dict:
    model = load_cost_model(cost_model_path)

    graph = load_topology(topology_path)
    cve_db = load_cve_database(cve_path)
    tag_graph(graph, cve_db)
    node_map = {node.node_id: node for node in graph.nodes}

    ranked = []
    for item in patch_results:
        node_id = item.get("node_id")
        node = node_map.get(node_id)
        if not node:
            continue

        severity = item.get("cvss_severity") or "MEDIUM"
        base_hours = float(model["node_type_effort_hours"].get(node.node_type, 4.0))
        severity_mult = float(model["severity_effort_multiplier"].get(severity, 1.0))
        critical_mult = float(model["critical_asset_multiplier"] if node.is_critical_asset else 1.0)

        effort_hours = max(0.5, round(base_hours * severity_mult * critical_mult, 2))
        risk_reduction_pp = max(0.0, float(item.get("simulation_impact", 0.0)) * 100.0)
        roi_score = round(risk_reduction_pp / effort_hours, 3)

        ranked.append(
            {
                "node_id": node_id,
                "cve_id": item.get("cve_id"),
                "node_type": node.node_type,
                "is_critical_asset": node.is_critical_asset,
                "cvss_score": item.get("cvss_score"),
                "cvss_severity": severity,
                "simulation_impact": item.get("simulation_impact", 0.0),
                "risk_reduction_pp": round(risk_reduction_pp, 2),
                "effort_hours": effort_hours,
                "roi_score": roi_score,
                "rationale_hint": (
                    "Critical asset + high impact" if node.is_critical_asset else "Fast mitigation with strong impact"
                ),
            }
        )

    ranked.sort(key=lambda x: (-x["roi_score"], -x["risk_reduction_pp"], x["effort_hours"]))
    for idx, row in enumerate(ranked):
        row["cost_rank"] = idx + 1

    return {
        "top_recommendations": ranked[:top_k],
        "all_recommendations": ranked,
        "cost_model": model,
    }
