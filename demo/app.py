"""
app.py — Onyx Streamlit Demo Application

Run with:
    cd D:/dehradun
    streamlit run demo/app.py
"""

from __future__ import annotations
import json
import os
import sys
import pickle
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Onyx — AI Cyber War Games",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TOPOLOGIES = {
    "Enterprise (20 nodes) — Recommended": "data/topologies/enterprise_20n.json",
    "Small Office (10 nodes)": "data/topologies/small_office_10n.json",
    "Cloud Hybrid (30 nodes)": "data/topologies/cloud_hybrid_30n.json",
}
CVE_PATH = "data/cve/cve_dataset.json"
AGENT_PATH = "checkpoints/red_agent.zip"
MARL_RESULTS_PATH = "checkpoints/marl/marl_results.json"
CACHE_DIR = Path("data/demo_cache")


# ---------------------------------------------------------------------------
# Cached loaders
# ---------------------------------------------------------------------------

@st.cache_resource
def load_graph(topology_path: str):
    from src.graph.topology_loader import load_topology
    from src.graph.cve_tagger import load_cve_database, tag_graph
    graph = load_topology(topology_path)
    cve_db = load_cve_database(CVE_PATH)
    tag_graph(graph, cve_db)
    return graph, cve_db


@st.cache_resource
def load_agent(agent_path: str):
    if not Path(agent_path).exists():
        return None
    try:
        from sb3_contrib import MaskablePPO
        return MaskablePPO.load(agent_path)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Graph visualiser (Pyvis)
# ---------------------------------------------------------------------------

def build_network_html(graph, edge_freq: dict = None) -> str:
    try:
        from pyvis.network import Network
    except ImportError:
        return "<p>pyvis not installed.</p>"

    severity_color = {
        "CRITICAL": "#dc3545",
        "HIGH":     "#fd7e14",
        "MEDIUM":   "#ffc107",
        "LOW":      "#28a745",
        "NONE":     "#6c757d",
    }

    net = Network(height="450px", width="100%", directed=True, bgcolor="#0d1117", font_color="white")
    net.force_atlas_2based(gravity=-50, central_gravity=0.005, spring_length=100)

    for node in graph.nodes:
        sev = node.vulnerabilities[0].severity_label if node.vulnerabilities else "NONE"
        color = severity_color[sev]
        if node.is_critical_asset:
            color = "#9b59b6"
        if node.is_compromised:
            color = "#e74c3c"

        border = "#ffffff" if node.is_entry_point else color
        shape = "star" if node.is_critical_asset else "dot"
        size = 20 if node.is_critical_asset else 14

        title = (
            f"<b>{node.node_id}</b><br>"
            f"Type: {node.node_type}<br>"
            f"Software: {node.software} {node.version}<br>"
            f"CVEs: {node.num_vulns} (max CVSS: {node.max_cvss:.1f})<br>"
            f"Critical: {node.is_critical_asset}<br>"
            f"Entry point: {node.is_entry_point}"
        )

        net.add_node(node.node_id, label=node.node_id, color=color,
                     shape=shape, size=size, title=title, borderWidth=2,
                     borderWidthSelected=4, color_border=border)

    for edge in graph.edges:
        freq = 0.0
        if edge_freq:
            key = f"{edge.source}||{edge.target}"
            freq = edge_freq.get(key, 0.0)

        width = max(1, int(freq * 8))
        color = f"rgba(231,76,60,{min(0.9, freq + 0.1)})" if freq > 0.05 else "rgba(255,255,255,0.15)"

        net.add_edge(
            edge.source, edge.target,
            title=f"{edge.connection_type} ({edge.permission_level})",
            width=width, color=color, arrows="to",
        )

    net.set_options("""
    {
      "physics": { "enabled": true },
      "interaction": { "hover": true, "tooltipDelay": 100 }
    }
    """)

    import tempfile
    html_path = os.path.join(tempfile.gettempdir(), "onyx_graph.html")
    net.save_graph(html_path)
    with open(html_path) as f:
        return f.read()


# ---------------------------------------------------------------------------
# Run simulation
# ---------------------------------------------------------------------------

def run_simulation(topology_path: str, n_episodes: int = 1000) -> dict:
    """Run attack path analysis and return results dict."""
    from src.analysis.attack_path_analyzer import analyze_attack_paths
    agent_path = AGENT_PATH if Path(AGENT_PATH).exists() else None
    return analyze_attack_paths(
        topology_path=topology_path,
        cve_path=CVE_PATH,
        agent_path=agent_path,
        n_episodes=n_episodes,
        seed=42,
    )


def run_patch_optimizer(topology_path: str) -> list:
    """Run patch optimizer (requires trained agent)."""
    from src.analysis.patch_optimizer import compute_patch_impact
    return compute_patch_impact(
        topology_path=topology_path,
        cve_path=CVE_PATH,
        agent_path=AGENT_PATH,
        n_baseline=200,
        n_eval_per_patch=50,
        verbose=False,
    )


# ---------------------------------------------------------------------------
# Plotly charts
# ---------------------------------------------------------------------------

def divergence_chart(patch_results: list) -> go.Figure:
    """CVSS Rank vs Simulation Rank scatter — the USP chart."""
    if not patch_results:
        return go.Figure()

    sim_ranks  = [r["simulation_rank"] for r in patch_results]
    cvss_ranks = [r["cvss_rank"]        for r in patch_results]
    labels     = [f"{r['node_id']}<br>{r['cve_id']}" for r in patch_results]
    impacts    = [r["simulation_impact"] * 100 for r in patch_results]

    fig = go.Figure()

    # Diagonal reference line (y=x means no divergence)
    max_rank = max(max(sim_ranks), max(cvss_ranks))
    fig.add_trace(go.Scatter(
        x=[1, max_rank], y=[1, max_rank],
        mode="lines", line=dict(color="gray", dash="dash", width=1),
        name="No divergence", showlegend=True
    ))

    fig.add_trace(go.Scatter(
        x=cvss_ranks, y=sim_ranks,
        mode="markers",
        text=labels,
        marker=dict(
            size=[max(8, min(20, imp * 2)) for imp in impacts],
            color=impacts,
            colorscale="RdYlGn_r",
            showscale=True,
            colorbar=dict(title="Impact (pp)"),
            line=dict(width=1, color="white"),
        ),
        hovertemplate="<b>%{text}</b><br>CVSS Rank: %{x}<br>Sim Rank: %{y}<br>Impact: %{marker.color:.1f}pp<extra></extra>",
        name="Vulnerability",
        showlegend=False,
    ))

    # Highlight top divergers (above diagonal = CVSS underestimates)
    for r in patch_results[:3]:
        if abs(r["cvss_rank"] - r["simulation_rank"]) >= 3:
            fig.add_annotation(
                x=r["cvss_rank"], y=r["simulation_rank"],
                text=r["node_id"], showarrow=True,
                arrowhead=2, arrowsize=1, arrowwidth=1.5,
                arrowcolor="white", font=dict(color="white", size=10),
                bgcolor="rgba(231,76,60,0.8)", borderpad=3,
            )

    fig.update_layout(
        title="CVSS Priority vs Onyx Simulation Priority",
        xaxis_title="CVSS Rank (traditional)",
        yaxis_title="Simulation Rank (Onyx)",
        plot_bgcolor="#0d1117",
        paper_bgcolor="#0d1117",
        font=dict(color="white"),
        height=400,
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(0,0,0,0.3)")
    )
    return fig


def arms_race_chart(marl_results: list) -> go.Figure:
    """Red vs Blue win rate over training rounds."""
    rounds = [r["round"] for r in marl_results]
    red_rates   = [r["red_win_rate"]   * 100 for r in marl_results]
    blue_rates  = [r["blue_win_rate"]  * 100 for r in marl_results]
    baseline    = [r.get("red_vs_rule_based", 0) * 100 for r in marl_results]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rounds, y=red_rates,  mode="lines+markers",
                             name="Red Win %",  line=dict(color="#e74c3c", width=2)))
    fig.add_trace(go.Scatter(x=rounds, y=blue_rates, mode="lines+markers",
                             name="Blue Win %", line=dict(color="#3498db", width=2)))
    fig.add_trace(go.Scatter(x=rounds, y=baseline,   mode="lines+markers",
                             name="Red vs Rule-Based", line=dict(color="#f39c12", dash="dash")))

    fig.update_layout(
        title="Arms Race: Red vs Blue Agent Training",
        xaxis_title="Training Round",
        yaxis_title="Win Rate (%)",
        plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
        font=dict(color="white"), height=350,
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(0,0,0,0.3)"),
        yaxis=dict(range=[0, 100]),
    )
    return fig


def edge_heatmap(edge_freq: dict, top_n: int = 15) -> go.Figure:
    top_edges = sorted(edge_freq.items(), key=lambda x: -x[1])[:top_n]
    labels = [k.replace("||", " → ") for k, _ in top_edges]
    values = [v * 100 for _, v in top_edges]

    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=values, colorscale="Reds"),
    ))
    fig.update_layout(
        title="Most Traversed Attack Edges",
        xaxis_title="Frequency (%)",
        plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
        font=dict(color="white"), height=400,
        yaxis=dict(autorange="reversed"),
    )
    return fig


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------

def main():
    # Header
    st.markdown("""
    <div style='background: linear-gradient(135deg, #16213e, #1a1a2e); padding: 24px; border-radius: 10px; margin-bottom: 20px;'>
        <h1 style='color: white; margin: 0;'>🛡️ Onyx</h1>
        <p style='color: #aaa; margin: 6px 0 0 0; font-size:1.1em;'>
            The AI that fights cyber-wars in its sleep.<br>
            <em>GNN World Model + Multi-Agent RL adversarial simulation</em>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")

        topo_label = st.selectbox("Network Topology", list(TOPOLOGIES.keys()))
        topology_path = TOPOLOGIES[topo_label]

        st.divider()

        n_sim_episodes = st.slider("Simulation Episodes", 100, 10000, 1000, step=100)

        st.divider()
        st.markdown("**Agent Status**")
        agent_ok = Path(AGENT_PATH).exists()
        gnn_ok = Path("checkpoints/gnn_world_model.pt").exists()
        marl_ok = Path(MARL_RESULTS_PATH).exists()
        st.markdown(f"{'✅' if agent_ok else '⚠️'} Red Agent {'(loaded)' if agent_ok else '(not trained)'}")
        st.markdown(f"{'✅' if gnn_ok else '⚠️'} GNN World Model {'(loaded)' if gnn_ok else '(not trained)'}")
        st.markdown(f"{'✅' if marl_ok else '⚠️'} MARL Results {'(available)' if marl_ok else '(not available)'}")

        st.divider()
        run_sim = st.button("🚀 Run Attack Simulation", type="primary", use_container_width=True)
        run_patch = st.button("🔍 Run Patch Optimizer", use_container_width=True,
                              disabled=not agent_ok,
                              help="Requires trained Red Agent")
        gen_report = st.button("📄 Generate Report", use_container_width=True)

    # Load graph
    graph, cve_db = load_graph(topology_path)

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Network Map", "📊 Attack Analysis", "⚔️ Red vs Blue", "📄 Report"])

    # ---- Tab 1: Network Map ----
    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Nodes", graph.num_nodes)
        col2.metric("Edges", graph.num_edges)
        col3.metric("CVEs Found", sum(n.num_vulns for n in graph.nodes))
        col4.metric("Critical Assets", len(graph.critical_assets))

        # Check for simulation results (edge frequency)
        edge_freq = st.session_state.get("edge_freq", {})
        graph_html = build_network_html(graph, edge_freq if edge_freq else None)
        if graph_html:
            components.html(graph_html, height=470, scrolling=False)
        else:
            st.info("Graph visualization requires pyvis. Install it with: pip install pyvis")

        # Node vulnerability table
        with st.expander("📋 Node Vulnerability Details"):
            import pandas as pd
            rows = []
            for node in sorted(graph.nodes, key=lambda n: -n.max_cvss):
                rows.append({
                    "Node": node.node_id,
                    "Type": node.node_type,
                    "Software": f"{node.software} {node.version}",
                    "# CVEs": node.num_vulns,
                    "Max CVSS": node.max_cvss,
                    "Severity": node.vulnerabilities[0].severity_label if node.vulnerabilities else "NONE",
                    "Critical Asset": "★" if node.is_critical_asset else "",
                    "Entry Point": "↗" if node.is_entry_point else "",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ---- Tab 2: Attack Analysis ----
    with tab2:
        if run_sim:
            with st.spinner(f"Running {n_sim_episodes:,} simulated attacks..."):
                sim_results = run_simulation(topology_path, n_episodes=n_sim_episodes)
                st.session_state["sim_results"] = sim_results
                st.session_state["edge_freq"] = sim_results.get("edge_frequency", {})

        sim_results = st.session_state.get("sim_results")

        if sim_results:
            col1, col2, col3 = st.columns(3)
            col1.metric("Attack Success Rate", f"{sim_results['success_rate']*100:.1f}%")
            col2.metric("Episodes Run", f"{sim_results['n_episodes']:,}")
            col3.metric("Unique Paths Found", f"{len(sim_results.get('top_paths', []))}")

            if run_patch and agent_ok:
                with st.spinner("Running patch optimizer (this may take a few minutes)..."):
                    patch_results = run_patch_optimizer(topology_path)
                    st.session_state["patch_results"] = patch_results
            elif run_patch:
                st.error("Train the Red Agent first (run `python -m src.training.train_red`)")

            patch_results = st.session_state.get("patch_results")

            if patch_results:
                st.subheader("🎯 Patch Recommendations")

                # Top fix callout
                top = patch_results[0]
                st.success(
                    f"**FIX TODAY:** Patch `{top['node_id']}` ({top['cve_id']}, CVSS {top['cvss_score']}) → "
                    f"drops attack success from **{top['baseline_success_rate']*100:.1f}%** to "
                    f"**{top['patched_success_rate']*100:.1f}%** "
                    f"(**-{top['simulation_impact']*100:.1f}pp**)"
                )

                # Divergence chart
                st.plotly_chart(divergence_chart(patch_results), use_container_width=True)

                # Table
                import pandas as pd
                table_rows = []
                for r in patch_results[:15]:
                    table_rows.append({
                        "Sim Rank": r["simulation_rank"],
                        "Node": r["node_id"],
                        "CVE": r["cve_id"],
                        "CVSS": r["cvss_score"],
                        "CVSS Rank": r["cvss_rank"],
                        "Rank Δ": r["cvss_rank"] - r["simulation_rank"],
                        "Impact": f"-{r['simulation_impact']*100:.1f}pp",
                    })
                st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

            # Edge heatmap
            edge_freq = sim_results.get("edge_frequency", {})
            if edge_freq:
                st.subheader("🔥 Attack Edge Heatmap")
                st.plotly_chart(edge_heatmap(edge_freq), use_container_width=True)

            # Top paths
            top_paths = sim_results.get("top_paths", [])
            if top_paths:
                st.subheader("🛤️ Most Common Attack Paths")
                for i, p in enumerate(top_paths[:5], 1):
                    st.markdown(f"**#{i}** ({p['frequency']*100:.1f}%) — `{p['path']}`")

        else:
            st.info("Click **Run Attack Simulation** in the sidebar to start.")

    # ---- Tab 3: Red vs Blue ----
    with tab3:
        st.subheader("⚔️ MARL Arms Race — Red vs Blue Agent Training")

        if marl_ok:
            with open(MARL_RESULTS_PATH) as f:
                marl_results = json.load(f)
            st.plotly_chart(arms_race_chart(marl_results), use_container_width=True)

            # Summary table
            import pandas as pd
            rows = []
            for r in marl_results:
                rows.append({
                    "Round": r["round"],
                    "Red Win %": f"{r['red_win_rate']*100:.1f}%",
                    "Blue Win %": f"{r['blue_win_rate']*100:.1f}%",
                    "Red vs Rule-Based": f"{r.get('red_vs_rule_based', 0)*100:.1f}%",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info(
                "Multi-agent training not yet completed. Run:\n```\npython -m src.training.train_marl\n```"
            )
            # Demo placeholder chart
            demo_data = [
                {"round": 1, "red_win_rate": 0.42, "blue_win_rate": 0.58, "red_vs_rule_based": 0.51},
                {"round": 2, "red_win_rate": 0.55, "blue_win_rate": 0.45, "red_vs_rule_based": 0.63},
                {"round": 3, "red_win_rate": 0.61, "blue_win_rate": 0.39, "red_vs_rule_based": 0.71},
                {"round": 4, "red_win_rate": 0.58, "blue_win_rate": 0.42, "red_vs_rule_based": 0.74},
                {"round": 5, "red_win_rate": 0.65, "blue_win_rate": 0.35, "red_vs_rule_based": 0.79},
            ]
            st.caption("Preview (simulated data — run training to get real curves):")
            st.plotly_chart(arms_race_chart(demo_data), use_container_width=True)

    # ---- Tab 4: Report ----
    with tab4:
        st.subheader("📄 Onyx Morning Report")

        patch_results = st.session_state.get("patch_results")
        sim_results = st.session_state.get("sim_results")

        if gen_report and patch_results:
            from src.analysis.report_generator import generate_report
            from src.analysis.attack_path_analyzer import analyze_attack_paths

            # Topo name from path
            topo_name = Path(topology_path).stem

            html_out = "reports/morning_report.html"
            pdf_out = "reports/morning_report.pdf"

            html = generate_report(
                patch_results=patch_results,
                topology_name=topo_name,
                n_episodes=sim_results["n_episodes"] if sim_results else 1000,
                top_paths=sim_results.get("top_paths") if sim_results else None,
                output_html=html_out,
                output_pdf=pdf_out,
            )
            st.session_state["report_html"] = html
            st.success(f"Report generated: {html_out}")

        report_html = st.session_state.get("report_html")
        if report_html:
            components.html(report_html, height=800, scrolling=True)
            col1, col2 = st.columns(2)
            with col1:
                if Path("reports/morning_report.html").exists():
                    with open("reports/morning_report.html", "rb") as f:
                        st.download_button("⬇️ Download HTML", f.read(),
                                           file_name="onyx_report.html",
                                           mime="text/html")
            with col2:
                if Path("reports/morning_report.pdf").exists():
                    with open("reports/morning_report.pdf", "rb") as f:
                        st.download_button("⬇️ Download PDF", f.read(),
                                           file_name="onyx_report.pdf",
                                           mime="application/pdf")
        else:
            st.info(
                "Run the Patch Optimizer first, then click **Generate Report**."
            )


if __name__ == "__main__":
    main()
