#!/usr/bin/env python3
"""Generate a judge-ready evidence bundle for Onyx.

The bundle captures:
- backend status
- telemetry status
- baseline simulation results
- comparison results using telemetry or hybrid mode
- patch optimization output
- a short variance summary and runnable demo commands
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import requests


DEFAULT_BACKEND_URL = "http://127.0.0.1:8020"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def request_json(
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    response = requests.request(method, url, params=params, json=json_body, timeout=120)
    response.raise_for_status()
    if not response.text.strip():
        return {}
    return response.json()


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def format_percent(value: Any) -> str:
    try:
        return f"{float(value) * 100.0:.1f}%"
    except (TypeError, ValueError):
        return "n/a"


def format_count(value: Any) -> str:
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return "n/a"


def pick_comparison_source(telemetry_status: Dict[str, Any]) -> str:
    if int(telemetry_status.get("event_count") or 0) > 0:
        return "telemetry"
    return "hybrid"


def build_demo_commands(
    backend_url: str,
    topology: str,
    episodes: int,
    telemetry_weight: float,
    comparison_source: str,
) -> str:
    return f"""# Start backend first
npm --prefix D:\\dehradun\\web run dev:backend

# Baseline and comparison bundle
python tools/evidence_bundle.py --backend-url {backend_url} --topology {topology} --episodes {episodes} --telemetry-weight {telemetry_weight} --comparison-source {comparison_source}

# Live telemetry check
Invoke-RestMethod -Uri {backend_url}/api/telemetry/status?topology={topology}
"""


def compare_results(
    baseline: Dict[str, Any],
    comparison: Dict[str, Any],
    telemetry_status: Dict[str, Any],
) -> Dict[str, Any]:
    baseline_rate = float(baseline.get("success_rate", 0.0) or 0.0)
    comparison_rate = float(comparison.get("success_rate", 0.0) or 0.0)
    top_paths_before = baseline.get("top_paths") or []
    top_paths_after = comparison.get("top_paths") or []

    return {
        "baseline_data_source": baseline.get("data_source", "simulation"),
        "comparison_data_source": comparison.get("data_source", "simulation"),
        "requested_comparison_source": comparison.get("requested_data_source"),
        "baseline_success_rate": baseline_rate,
        "comparison_success_rate": comparison_rate,
        "success_rate_delta_pp": round((baseline_rate - comparison_rate) * 100.0, 2),
        "baseline_top_paths": top_paths_before[:5],
        "comparison_top_paths": top_paths_after[:5],
        "telemetry_event_count": int(telemetry_status.get("event_count") or 0),
        "telemetry_blocked_events": int(telemetry_status.get("blocked_events") or 0),
        "telemetry_critical_reaches": int(telemetry_status.get("critical_reaches") or 0),
        "telemetry_source": telemetry_status.get("source"),
        "telemetry_updated_at": telemetry_status.get("updated_at"),
    }


def render_summary_markdown(
    manifest: Dict[str, Any],
    variance: Dict[str, Any],
    backend_status: Dict[str, Any],
    telemetry_status: Dict[str, Any],
    baseline: Dict[str, Any],
    comparison: Dict[str, Any],
    patch_results: Dict[str, Any],
) -> str:
    lines = []
    lines.append("# Onyx Evidence Bundle")
    lines.append("")
    lines.append(f"Generated at: {manifest['generated_at']}")
    lines.append(f"Backend: {manifest['backend_url']}")
    lines.append(f"Topology: {manifest['topology']}")
    lines.append("")
    lines.append("## Status")
    lines.append("")
    lines.append(f"- Red agent present: {backend_status.get('red_agent')}")
    lines.append(f"- GNN model present: {backend_status.get('gnn_model')}")
    lines.append(f"- MARL results present: {backend_status.get('marl_results')}")
    lines.append(f"- Patch report present: {backend_status.get('patch_report')}")
    lines.append(f"- Morning report present: {backend_status.get('morning_report')}")
    lines.append("")
    lines.append("## Telemetry")
    lines.append("")
    lines.append(f"- Source: {telemetry_status.get('source')}")
    lines.append(f"- Updated at: {telemetry_status.get('updated_at')}")
    lines.append(f"- Event count: {telemetry_status.get('event_count')}")
    lines.append(f"- Blocked events: {telemetry_status.get('blocked_events')}")
    lines.append(f"- Critical reaches: {telemetry_status.get('critical_reaches')}")
    lines.append("")
    lines.append("## Before / After")
    lines.append("")
    lines.append("| Metric | Baseline | Comparison | Delta |")
    lines.append("|---|---:|---:|---:|")
    lines.append(
        f"| Success rate | {format_percent(baseline.get('success_rate'))} | {format_percent(comparison.get('success_rate'))} | {variance.get('success_rate_delta_pp', 0.0):+.2f} pp |"
    )
    lines.append(
        f"| Attack paths | {format_count(len(baseline.get('top_paths') or []))} | {format_count(len(comparison.get('top_paths') or []))} | n/a |"
    )
    lines.append("")
    lines.append("## Patch Optimization")
    lines.append("")
    lines.append(f"- Requested source: {patch_results.get('requested_data_source')}")
    lines.append(f"- Data source: {patch_results.get('data_source')}")
    lines.append(f"- Note: {patch_results.get('data_source_note')}")
    lines.append(f"- Rows: {len(patch_results.get('results') or [])}")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("- If telemetry events are not present, the comparison source may fall back to hybrid or simulation.")
    lines.append("- This bundle records API outputs from the current backend state; it does not validate external lab safety or permissions.")
    lines.append("")
    lines.append("## Evidence Files")
    lines.append("")
    lines.append("- backend_status.json")
    lines.append("- telemetry_status.json")
    lines.append("- baseline_simulation.json")
    lines.append("- comparison_simulation.json")
    lines.append("- patch_results.json")
    lines.append("- variance.json")
    lines.append("- demo_commands.ps1")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Onyx judge evidence bundle.")
    parser.add_argument("--backend-url", default=DEFAULT_BACKEND_URL)
    parser.add_argument("--topology", default="enterprise_20n")
    parser.add_argument("--episodes", type=int, default=700)
    parser.add_argument("--baseline-episodes", type=int, default=200)
    parser.add_argument("--eval-per-patch", type=int, default=50)
    parser.add_argument("--telemetry-weight", type=float, default=0.6)
    parser.add_argument("--top-k-patches", type=int, default=3)
    parser.add_argument("--comparison-source", choices=["telemetry", "hybrid"], default=None)
    parser.add_argument("--output-dir", default="reports/evidence")
    args = parser.parse_args()

    backend_url = args.backend_url.rstrip("/")
    output_dir = Path(args.output_dir) / f"bundle-{utc_stamp()}"
    output_dir.mkdir(parents=True, exist_ok=True)

    backend_status = request_json("GET", f"{backend_url}/api/status")
    telemetry_status = request_json("GET", f"{backend_url}/api/telemetry/status", params={"topology": args.topology})
    comparison_source = args.comparison_source or pick_comparison_source(telemetry_status)

    baseline_payload = {
        "topology": args.topology,
        "n_episodes": args.episodes,
        "data_source": "simulation",
        "telemetry_weight": args.telemetry_weight,
    }
    comparison_payload = {
        "topology": args.topology,
        "n_episodes": args.episodes,
        "data_source": comparison_source,
        "telemetry_weight": args.telemetry_weight,
    }
    patch_payload = {
        "topology": args.topology,
        "n_baseline": args.baseline_episodes,
        "n_eval_per_patch": args.eval_per_patch,
        "data_source": comparison_source,
        "telemetry_weight": args.telemetry_weight,
    }

    baseline = request_json("POST", f"{backend_url}/api/simulate", json_body=baseline_payload)
    comparison = request_json("POST", f"{backend_url}/api/simulate", json_body=comparison_payload)
    patch_results = request_json("POST", f"{backend_url}/api/patch-optimize", json_body=patch_payload)

    variance = compare_results(baseline, comparison, telemetry_status)
    manifest = {
        "generated_at": iso_now(),
        "backend_url": backend_url,
        "topology": args.topology,
        "episodes": args.episodes,
        "telemetry_weight": args.telemetry_weight,
        "comparison_source": comparison_source,
        "output_dir": str(output_dir),
    }

    write_json(output_dir / "manifest.json", manifest)
    write_json(output_dir / "backend_status.json", backend_status)
    write_json(output_dir / "telemetry_status.json", telemetry_status)
    write_json(output_dir / "baseline_simulation.json", baseline)
    write_json(output_dir / "comparison_simulation.json", comparison)
    write_json(output_dir / "patch_results.json", patch_results)
    write_json(output_dir / "variance.json", variance)

    demo_commands = build_demo_commands(backend_url, args.topology, args.episodes, args.telemetry_weight, comparison_source)
    (output_dir / "demo_commands.ps1").write_text(demo_commands, encoding="utf-8")

    summary = render_summary_markdown(manifest, variance, backend_status, telemetry_status, baseline, comparison, patch_results)
    (output_dir / "summary.md").write_text(summary, encoding="utf-8")

    print(f"Evidence bundle written to: {output_dir}")
    print(f"Comparison source: {comparison_source}")
    print(f"Baseline success rate: {format_percent(baseline.get('success_rate'))}")
    print(f"Comparison success rate: {format_percent(comparison.get('success_rate'))}")
    print(f"Success rate delta: {variance['success_rate_delta_pp']:+.2f} pp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())