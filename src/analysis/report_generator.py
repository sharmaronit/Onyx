"""
report_generator.py — Generates HTML and PDF morning reports.

Output: A professional one-page report with:
  - Executive summary (auto-filled with simulation results)
  - Network overview (node/CVE counts)
  - Top 5 patch recommendations (CVSS rank vs Simulation rank)
  - Attack path heatmap summary
  - Methodology section
"""

from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from jinja2 import Template


REPORT_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body { font-family: 'Segoe UI', Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 40px; color: #1a1a2e; }
  h1 { color: #16213e; border-bottom: 3px solid #e94560; padding-bottom: 10px; }
  h2 { color: #16213e; margin-top: 30px; border-left: 4px solid #e94560; padding-left: 12px; }
  .metric-row { display: flex; gap: 20px; margin: 20px 0; }
  .metric-box { background: #f8f9fa; border-radius: 8px; padding: 16px 24px; flex: 1; border-top: 4px solid #e94560; }
  .metric-value { font-size: 2em; font-weight: bold; color: #e94560; }
  .metric-label { font-size: 0.85em; color: #666; }
  table { width: 100%; border-collapse: collapse; margin-top: 16px; }
  th { background: #16213e; color: white; padding: 10px 14px; text-align: left; font-size: 0.9em; }
  td { padding: 9px 14px; border-bottom: 1px solid #eee; font-size: 0.88em; }
  tr:hover td { background: #f8f9fa; }
  .critical { color: #dc3545; font-weight: bold; }
  .high     { color: #fd7e14; font-weight: bold; }
  .medium   { color: #ffc107; }
  .low      { color: #28a745; }
  .badge-sim  { background: #16213e; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; }
  .badge-cvss { background: #e94560; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; }
  .divergence { background: #fff3cd; border: 1px solid #ffc107; padding: 6px 12px; border-radius: 4px; font-size: 0.85em; }
  footer { margin-top: 40px; text-align: center; color: #999; font-size: 0.8em; border-top: 1px solid #eee; padding-top: 16px; }
  .highlight { background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px 16px; border-radius: 4px; margin: 12px 0; }
</style>
</head>
<body>

<h1>🛡️ Onyx Morning Report</h1>
<p style="color:#666">Generated: {{ generated_at }} &nbsp;&nbsp;|&nbsp;&nbsp; Topology: <strong>{{ topology_name }}</strong></p>

<div class="highlight">
<strong>CRITICAL FINDING:</strong> Last night, Onyx simulated {{ n_episodes | number_format }} attacks against your network.
<strong>{{ baseline_pct }}% succeeded.</strong>
A single action — patching <strong>{{ top_fix_node }}</strong> — reduces this to {{ top_fix_pct }}%
(a <strong>{{ top_fix_reduction }}pp reduction</strong>).
</div>

<div class="metric-row">
  <div class="metric-box">
    <div class="metric-value">{{ baseline_pct }}%</div>
    <div class="metric-label">Baseline attack success rate</div>
  </div>
  <div class="metric-box">
    <div class="metric-value">{{ top_fix_pct }}%</div>
    <div class="metric-label">Success rate after top fix</div>
  </div>
  <div class="metric-box">
    <div class="metric-value">{{ top_fix_reduction }}pp</div>
    <div class="metric-label">Reduction from single patch</div>
  </div>
  <div class="metric-box">
    <div class="metric-value">{{ n_cves }}</div>
    <div class="metric-label">CVEs evaluated</div>
  </div>
</div>

<h2>Top 5 Patch Recommendations</h2>
<p style="font-size:0.9em;color:#666">
  <span class="badge-sim">SIM RANK</span> = Onyx priority (how much patching this reduces attack success)<br>
  <span class="badge-cvss">CVSS RANK</span> = Traditional CVSS priority (higher score = patch first)
</p>
<table>
  <tr>
    <th>Sim Rank</th><th>Node</th><th>CVE</th><th>CVSS Score</th><th>CVSS Rank</th>
    <th>Current Success</th><th>After Patch</th><th>Impact</th>
  </tr>
  {% for r in top5 %}
  <tr>
    <td><strong>#{{ r.simulation_rank }}</strong></td>
    <td>{{ r.node_id }}</td>
    <td style="font-family:monospace;font-size:0.85em">{{ r.cve_id }}</td>
    <td class="{{ r.cvss_severity | lower }}">{{ r.cvss_score }} ({{ r.cvss_severity }})</td>
    <td>
      #{{ r.cvss_rank }}
      {% if r.cvss_rank != r.simulation_rank %}
      <span class="divergence">Δ{{ (r.cvss_rank - r.simulation_rank) | abs }}</span>
      {% endif %}
    </td>
    <td>{{ (r.baseline_success_rate * 100) | round(1) }}%</td>
    <td>{{ (r.patched_success_rate * 100) | round(1) }}%</td>
    <td class="critical"><strong>-{{ (r.simulation_impact * 100) | round(1) }}pp</strong></td>
  </tr>
  {% endfor %}
</table>

{% if top_paths %}
<h2>Most Frequent Attack Paths</h2>
<table>
  <tr><th>#</th><th>Attack Path</th><th>Frequency</th></tr>
  {% for p in top_paths %}
  <tr>
    <td>{{ loop.index }}</td>
    <td style="font-family:monospace;font-size:0.85em">{{ p.path }}</td>
    <td>{{ (p.frequency * 100) | round(1) }}%</td>
  </tr>
  {% endfor %}
</table>
{% endif %}

<h2>Methodology</h2>
<p style="font-size:0.9em">Onyx uses a <strong>Graph Neural Network world model</strong> (GraphSAGE, 3 layers)
trained on 50,000 synthetic attack episodes to learn the transition dynamics of your network.
A <strong>Proximal Policy Optimization (PPO) agent</strong> trained via reinforcement learning discovers
optimal attack paths within this learned simulator. For each CVE, the patch optimizer runs
{{ n_eval_per_patch }} evaluation episodes after removing that vulnerability and measures the
resulting drop in attack success rate. This network-context-aware prioritisation differs from
generic CVSS scoring, which ranks vulnerabilities in isolation without considering your specific
network topology.</p>

<footer>
  Onyx v1.0 &nbsp;|&nbsp; Powered by PyTorch Geometric + Stable-Baselines3
  &nbsp;|&nbsp; {{ generated_at }}
</footer>
</body>
</html>
"""


def generate_report(
    patch_results: List[Dict],
    topology_name: str,
    n_episodes: int = 10000,
    top_paths: Optional[List[Dict]] = None,
    n_eval_per_patch: int = 100,
    output_html: Optional[str] = None,
    output_pdf: Optional[str] = None,
) -> str:
    """
    Generate HTML (and optionally PDF) report from patch optimizer results.

    Returns
    -------
    str
        HTML content
    """
    if not patch_results:
        return "<html><body><p>No patch results available.</p></body></html>"

    baseline = patch_results[0]["baseline_success_rate"]
    top = patch_results[0]

    def number_format(n):
        return f"{n:,}"

    from jinja2 import Environment
    env = Environment()
    env.filters["number_format"] = lambda x: f"{x:,}"
    env.filters["abs"] = abs

    template = env.from_string(REPORT_TEMPLATE)

    html = template.render(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        topology_name=topology_name,
        n_episodes=n_episodes,
        baseline_pct=round(baseline * 100, 1),
        top_fix_node=top["node_id"],
        top_fix_pct=round(top["patched_success_rate"] * 100, 1),
        top_fix_reduction=round(top["simulation_impact"] * 100, 1),
        n_cves=len(patch_results),
        top5=patch_results[:5],
        top_paths=top_paths or [],
        n_eval_per_patch=n_eval_per_patch,
    )

    if output_html:
        Path(output_html).parent.mkdir(parents=True, exist_ok=True)
        with open(output_html, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML report saved: {output_html}")

    if output_pdf:
        try:
            import weasyprint
            Path(output_pdf).parent.mkdir(parents=True, exist_ok=True)
            weasyprint.HTML(string=html).write_pdf(output_pdf)
            print(f"PDF report saved: {output_pdf}")
        except ImportError:
            print("[WARNING] weasyprint not installed. PDF not generated.")
        except Exception as e:
            print(f"[WARNING] PDF generation failed: {e}")

    return html
