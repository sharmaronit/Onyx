"""
patch_optimizer.py — THE USP: computes which single patch blocks the most attacks.

For each CVE on each node:
  1. Temporarily remove that CVE from the graph
  2. Run the trained Red agent on the patched graph (n_eval episodes)
  3. Compute success_rate_delta = baseline_rate - patched_rate
  4. Rank by simulation impact vs CVSS score

Output shows:
  - CVSS rank vs Simulation rank (the divergence = the USP claim)
  - "Patching node X blocks Y% of attacks — 6× more effective than CVSS priority"

Usage:
    python -m src.analysis.patch_optimizer \
        --topology data/topologies/enterprise_20n.json \
        --cve_path data/cve/cve_dataset.json \
        --agent checkpoints/red_agent.zip \
        --output reports/patch_analysis.json
"""

from __future__ import annotations
import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Sequence
from tqdm import tqdm

from src.graph.network_graph import NetworkGraph
from src.graph.topology_loader import load_topology
from src.graph.cve_tagger import load_cve_database, tag_graph


# ---------------------------------------------------------------------------
# Agent evaluation helper
# ---------------------------------------------------------------------------

def evaluate_agent_success_rate(
    agent,           # MaskablePPO instance
    graph: NetworkGraph,
    cve_db: list,
    n_episodes: int = 100,
    seed: int = 42,
    episode_seeds: Optional[Sequence[int]] = None,
) -> float:
    """Run episodes on an already prepared graph.

    The caller owns CVE tagging and interventions. This function deliberately
    does not call ``tag_graph`` because doing so would undo a simulated patch.
    Passing the same ``episode_seeds`` to baseline and intervention runs gives
    a paired, reproducible comparison.
    """

    from src.envs.attacker_env import _build_obs, _build_action_mask
    from src.simulator.rule_based import AttackSimulator, recommended_episode_limit
    node_order = sorted(graph.node_ids)
    n_real = len(node_order)
    max_steps = recommended_episode_limit(graph)
    if episode_seeds is None:
        rng = random.Random(seed)
        seeds = [rng.randrange(0, 2**31) for _ in range(n_episodes)]
    else:
        seeds = [int(value) for value in episode_seeds]
        if len(seeds) != n_episodes:
            raise ValueError("episode_seeds length must equal n_episodes")

    successes = 0
    for episode_seed in seeds:
        g = graph.deep_copy()
        sim = AttackSimulator(
            g,
            max_steps=max_steps,
            max_attempts_per_target=1,
            seed=episode_seed,
        )
        sim.reset()
        compromised = set(sim.compromised)
        done = False
        step = 0

        while not done and step < max_steps:
            obs = _build_obs(g, node_order)
            mask = _build_action_mask(g, node_order, compromised)
            if not mask.any():
                break
            action, _ = agent.predict(obs, action_masks=mask, deterministic=False)
            action_nid = node_order[int(action)] if int(action) < n_real else node_order[0]
            _, done = sim.step(action_nid)
            compromised = set(sim.compromised)

            if any(g.get_node(n).is_critical_asset for n in compromised):
                successes += 1
                done = True
            step += 1

    return successes / n_episodes


# ---------------------------------------------------------------------------
# Core optimizer
# ---------------------------------------------------------------------------

def compute_patch_impact(
    topology_path: str,
    cve_path: str,
    agent_path: str,
    n_baseline: int = 500,
    n_eval_per_patch: int = 100,
    seed: int = 42,
    verbose: bool = True,
) -> List[Dict]:
    """
    Main patch optimizer.

    Returns
    -------
    list of dict, sorted by simulation_impact descending:
        node_id, cve_id, cvss_score, cvss_rank,
        baseline_success_rate, patched_success_rate,
        simulation_impact, simulation_rank
    """
    try:
        from sb3_contrib import MaskablePPO
    except ImportError:
        raise ImportError("sb3-contrib not installed.")

    graph = load_topology(topology_path)
    cve_db = load_cve_database(cve_path)
    tag_graph(graph, cve_db)

    # Load agent
    agent = MaskablePPO.load(agent_path)

    if verbose:
        print(f"Loaded agent from {agent_path}")
        print(f"Computing baseline ({n_baseline} episodes)...")

    seed_rng = random.Random(seed)
    baseline_seeds = [seed_rng.randrange(0, 2**31) for _ in range(n_baseline)]
    comparison_seeds = [seed_rng.randrange(0, 2**31) for _ in range(n_eval_per_patch)]
    input_snapshot = hashlib.sha256(Path(topology_path).read_bytes()).hexdigest()
    seed_set_sha256 = hashlib.sha256(
        json.dumps(comparison_seeds, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    model_snapshot = hashlib.sha256(Path(agent_path).read_bytes()).hexdigest()
    baseline_rate = evaluate_agent_success_rate(
        agent,
        graph,
        cve_db,
        n_episodes=n_baseline,
        episode_seeds=baseline_seeds,
    )
    paired_baseline_rate = evaluate_agent_success_rate(
        agent,
        graph,
        cve_db,
        n_episodes=n_eval_per_patch,
        episode_seeds=comparison_seeds,
    )

    if verbose:
        print(f"Baseline attack success rate: {baseline_rate*100:.1f}%")
        print("Computing per-patch impact...")

    results = []
    all_cves = []

    for node in graph.nodes:
        for cve in node.vulnerabilities:
            all_cves.append((node.node_id, cve))

    if verbose:
        iterator = tqdm(all_cves, desc="Evaluating patches")
    else:
        iterator = all_cves

    for node_id, cve in iterator:
        # Create patched copy: remove this CVE from this node
        patched_graph = graph.deep_copy()
        pnode = patched_graph.get_node(node_id)
        pnode.vulnerabilities = [v for v in pnode.vulnerabilities if v.cve_id != cve.cve_id]

        patched_rate = evaluate_agent_success_rate(
            agent, patched_graph, cve_db,
            n_episodes=n_eval_per_patch,
            episode_seeds=comparison_seeds,
        )

        impact = paired_baseline_rate - patched_rate

        results.append({
            "node_id": node_id,
            "cve_id": cve.cve_id,
            "node_type": patched_graph.get_node(node_id).node_type,
            "is_critical_asset": patched_graph.get_node(node_id).is_critical_asset,
            "cvss_score": cve.cvss_score,
            "cvss_severity": cve.severity_label,
            "attack_vector": cve.attack_vector,
            "baseline_success_rate": round(paired_baseline_rate, 4),
            "patched_success_rate": round(patched_rate, 4),
            "simulation_impact": round(impact, 4),
            "simulation_rank": None,    # filled below
            "cvss_rank": None,          # filled below
            "description": cve.description[:120],
            "measurement_type": "simulated_counterfactual",
            "evidence": {
                "topology_sha256": input_snapshot,
                "model_sha256": model_snapshot,
                "seed_set_sha256": seed_set_sha256,
                "episode_count": n_eval_per_patch,
                "intervention": {"type": "remove_cve", "node_id": node_id, "cve_id": cve.cve_id},
                "engine_version": "paired-counterfactual-v2",
            },
        })

    # ---- Assign simulation ranks ----
    results.sort(key=lambda x: -x["simulation_impact"])
    for i, r in enumerate(results):
        r["simulation_rank"] = i + 1

    # ---- Assign CVSS ranks ----
    results_by_cvss = sorted(results, key=lambda x: -x["cvss_score"])
    for i, r in enumerate(results_by_cvss):
        r["cvss_rank"] = i + 1

    # ---- Re-sort by simulation impact ----
    results.sort(key=lambda x: -x["simulation_impact"])

    if verbose:
        print(f"\n{'='*70}")
        print("TOP 5 PATCH RECOMMENDATIONS (by Simulation Impact):")
        print(f"{'='*70}")
        print(f"{'Rank':>4}  {'Node':25s}  {'CVE':18s}  {'CVSS Rank':>9}  {'Impact':>8}")
        print("-" * 70)
        for r in results[:5]:
            print(f"{r['simulation_rank']:>4}  {r['node_id']:25s}  {r['cve_id']:18s}  "
                  f"{r['cvss_rank']:>9}  {r['simulation_impact']*100:>7.1f}%")
        print(f"\nBaseline: {paired_baseline_rate*100:.1f}% attack success")
        print(f"Top fix: Patching '{results[0]['node_id']}' drops success to "
              f"{results[0]['patched_success_rate']*100:.1f}% "
              f"({results[0]['simulation_impact']*100:.1f}pp reduction)")

    return results


def save_results(results: list, output_path: str):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Patch analysis saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topology",   default="data/topologies/enterprise_20n.json")
    parser.add_argument("--cve_path",   default="data/cve/cve_dataset.json")
    parser.add_argument("--agent",      default="checkpoints/red_agent.zip")
    parser.add_argument("--output",     default="reports/patch_analysis.json")
    parser.add_argument("--baseline",   default=500, type=int)
    parser.add_argument("--eval",       default=100, type=int)
    args = parser.parse_args()

    results = compute_patch_impact(
        topology_path=args.topology,
        cve_path=args.cve_path,
        agent_path=args.agent,
        n_baseline=args.baseline,
        n_eval_per_patch=args.eval,
        verbose=True,
    )
    save_results(results, args.output)
