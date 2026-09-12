"""
attack_path_analyzer.py — Extracts and ranks attack paths from episode logs.
Computes edge frequency heatmap and top-N most common paths to critical assets.
"""

from __future__ import annotations
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import List, Optional

import numpy as np

from src.graph.network_graph import NetworkGraph
from src.graph.topology_loader import load_topology
from src.graph.cve_tagger import load_cve_database, tag_graph


def analyze_attack_paths(
    topology_path: str,
    cve_path: str,
    agent_path: Optional[str] = None,
    n_episodes: int = 1000,
    top_k_paths: int = 20,
    seed: int = 42,
) -> dict:
    """
    Run n_episodes and compute:
      - edge frequency: how often each edge is traversed
      - node visit frequency: how often each node is compromised
            - top-K complete attack paths to critical assets

    Parameters
    ----------
    agent_path : str or None
        If provided, uses trained Red agent. Otherwise, rule-based random.

    Returns
    -------
    dict with keys:
        edge_frequency    : {(src, dst): float} normalised [0,1]
        node_frequency    : {node_id: float}
        top_paths         : list of {path, count, success_rate}
        total_unique_paths: int
        success_rate      : float
        n_episodes        : int
    """
    graph = load_topology(topology_path)
    cve_db = load_cve_database(cve_path)
    tag_graph(graph, cve_db)

    # Load agent if provided
    agent = None
    if agent_path and Path(agent_path).exists():
        try:
            from sb3_contrib import MaskablePPO
            agent = MaskablePPO.load(agent_path)
        except Exception as e:
            print(f"[WARNING] Could not load agent: {e}. Using random policy.")

    from src.simulator.rule_based import AttackSimulator, recommended_episode_limit

    build_obs = None
    build_action_mask = None
    if agent:
        try:
            from src.envs.attacker_env import _build_obs, _build_action_mask

            build_obs = _build_obs
            build_action_mask = _build_action_mask
        except Exception as e:
            print(f"[WARNING] Could not import attacker env helpers: {e}. Using random policy.")
            agent = None

    node_order = sorted(graph.node_ids)
    policy_engine = "trained_red_agent" if agent else "rule_based"
    max_steps = recommended_episode_limit(graph)
    max_attempts_per_target = 1
    edge_counter: Counter = Counter()
    node_counter: Counter = Counter()
    path_counter: Counter = Counter()
    rng = random.Random(seed)
    successes = 0

    for ep_idx in range(n_episodes):
        g = graph.deep_copy()
        tag_graph(g, cve_db)
        sim = AttackSimulator(
            g,
            max_steps=max_steps,
            max_attempts_per_target=max_attempts_per_target,
            seed=rng.randint(0, 10**6),
        )
        sim.reset()
        compromised = set(sim.compromised)
        path = list(compromised)
        done = False
        step = 0

        while not done and step < max_steps:
            candidates = sim.reachable_targets
            if not candidates:
                break

            if agent and build_obs and build_action_mask:
                obs = build_obs(g, node_order)
                mask = build_action_mask(g, node_order, compromised)
                if not mask.any():
                    break
                action, _ = agent.predict(obs, action_masks=mask, deterministic=False)
                action_nid = node_order[int(action)] if int(action) < len(node_order) else rng.choice(candidates)
            else:
                action_nid = rng.choice(candidates)

            before = set(sim.compromised)
            _, done = sim.step(action_nid)
            compromised = set(sim.compromised)
            newly = compromised - before

            for new_node in newly:
                # Record which previously-compromised nodes could have led here
                for prev_node in before:
                    if g.G.has_edge(prev_node, new_node):
                        edge_counter[(prev_node, new_node)] += 1
                node_counter[new_node] += 1
                path.append(new_node)

            if any(g.get_node(n).is_critical_asset for n in newly):
                successes += 1
                done = True
            step += 1

        path_key = " → ".join(path)
        path_counter[path_key] += 1

    # Normalise
    total = n_episodes
    edge_freq = {k: v / total for k, v in edge_counter.items()}
    node_freq = {k: v / total for k, v in node_counter.items()}

    requested_top_k = max(1, int(top_k_paths))
    total_unique_paths = len(path_counter)

    top_paths = [
        {"path": path_str, "count": count, "frequency": count / total}
        for path_str, count in path_counter.most_common(requested_top_k)
    ]

    return {
        "edge_frequency": {f"{s}||{t}": v for (s, t), v in
                           sorted(edge_freq.items(), key=lambda x: -x[1])},
        "node_frequency": dict(sorted(node_freq.items(), key=lambda x: -x[1])),
        "top_paths": top_paths,
        "top_paths_returned": len(top_paths),
        "total_unique_paths": total_unique_paths,
        "success_rate": successes / n_episodes,
        "successful_runs": successes,
        "failed_runs": max(0, n_episodes - successes),
        "evaluation_runs": n_episodes,
        "n_episodes": n_episodes,
        "max_steps_per_episode": max_steps,
        "max_attempts_per_target": max_attempts_per_target,
        "policy_engine": policy_engine,
    }


def save_analysis(results: dict, output_path: str):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
