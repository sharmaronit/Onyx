from __future__ import annotations

from typing import Dict, List


def _path_mentions(top_paths: List[dict], node_id: str) -> int:
    count = 0
    for row in top_paths:
        if node_id in row.get("path", ""):
            count += 1
    return count


def build_explanation_cards(
    cost_recommendations: List[dict],
    sim_results: Dict,
    baseline_success_rate: float,
    top_n: int = 5,
) -> List[dict]:
    top_paths = sim_results.get("top_paths") or []
    cards: List[dict] = []

    for row in cost_recommendations[:top_n]:
        node_id = row.get("node_id")
        cve_id = row.get("cve_id")
        risk_reduction_pp = float(row.get("risk_reduction_pp") or 0.0)
        effort_hours = float(row.get("effort_hours") or 0.0)
        mentions = _path_mentions(top_paths, node_id)

        after_est = max(0.0, baseline_success_rate * 100.0 - risk_reduction_pp)
        cards.append(
            {
                "key": f"{node_id}:{cve_id}",
                "title": f"Patch {cve_id} on {node_id}",
                "summary": (
                    f"Estimated risk drops by {risk_reduction_pp:.1f}pp with about {effort_hours:.1f}h effort."
                ),
                "why_ranked": [
                    f"ROI score {row.get('roi_score')} balances risk reduction and engineering effort.",
                    f"Appears on {mentions} of the top simulated attack paths.",
                    (
                        "Marked critical asset in topology."
                        if row.get("is_critical_asset")
                        else "Mitigation is operationally lighter than other high-risk fixes."
                    ),
                ],
                "tradeoffs": [
                    f"Estimated implementation effort: {effort_hours:.1f} engineering hours.",
                    "Score is simulation-estimated and should be validated in production telemetry.",
                ],
                "impact_preview": {
                    "before": round(baseline_success_rate * 100.0, 1),
                    "after": round(after_est, 1),
                    "delta_pp": round(risk_reduction_pp, 1),
                },
            }
        )

    return cards
