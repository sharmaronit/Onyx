"""
train_marl.py — 5-round alternating self-play training for Red vs Blue agents.

Each round:
  - Train Red  200K steps vs frozen Blue
  - Train Blue 200K steps vs frozen Red

This creates an arms-race dynamic visible in the evaluation curves.

Usage:
    python -m src.training.train_marl \
        --topology data/topologies/enterprise_20n.json \
        --cve_path data/cve/cve_dataset.json \
        --red_start checkpoints/red_agent.zip \
        --blue_start checkpoints/blue_agent.zip \
        --output_dir checkpoints/marl
"""

from __future__ import annotations
import argparse
import json
import random
import sys
from pathlib import Path
from typing import Optional

# Fix sys.path for absolute imports (Windows-compatible)
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import numpy as np
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv

try:
    from sb3_contrib import MaskablePPO
    HAS_SB3_CONTRIB = True
except ImportError:
    HAS_SB3_CONTRIB = False

from src.envs.attacker_env import AttackerEnv
from src.envs.defender_env import DefenderEnv
from src.envs.marl_env import OnyxMARLEnv


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------

def evaluate_red_vs_rule_based(
    red_model,
    topology_path: str,
    cve_path: str,
    n_episodes: int = 200,
) -> float:
    """Return attack success rate of red agent vs. rule-based defender."""
    env = AttackerEnv(topology_path=topology_path, cve_path=cve_path, max_steps=50)
    successes = 0
    for _ in range(n_episodes):
        obs, info = env.reset()
        done = False
        while not done:
            action, _ = red_model.predict(obs, action_masks=info["action_mask"], deterministic=True)
            obs, reward, terminated, truncated, info = env.step(int(action))
            done = terminated or truncated
            if terminated:
                successes += 1
    return successes / n_episodes


def evaluate_red_vs_blue(
    red_model,
    blue_model,
    topology_path: str,
    cve_path: str,
    n_episodes: int = 200,
) -> dict:
    """Evaluate red vs blue in the MARL environment. Returns win rates."""
    from src.graph.topology_loader import load_topology
    from src.graph.cve_tagger import load_cve_database, tag_graph
    from src.simulator.rule_based import AttackSimulator
    from src.envs.attacker_env import _build_obs, _build_action_mask, MAX_NODES
    from src.envs.defender_env import decode_defender_action

    graph = load_topology(topology_path)
    cve_db = load_cve_database(cve_path)

    red_wins = 0
    blue_wins = 0
    rng = random.Random(42)

    for ep_idx in range(n_episodes):
        g = graph.deep_copy()
        tag_graph(g, cve_db)
        node_order = sorted(g.node_ids)
        sim = AttackSimulator(g, max_steps=50, seed=rng.randint(0, 10**6))
        sim.reset()
        compromised = set(sim.compromised)

        done = False
        step = 0
        episode_result = "blue_win"

        while not done and step < 100:
            # Attacker turn
            obs = _build_obs(g, node_order)
            mask = _build_action_mask(g, node_order, compromised)
            if not mask.any():
                break
            action, _ = red_model.predict(obs, action_masks=mask, deterministic=False)
            before = set(sim.compromised)
            sim.step(node_order[int(action)] if int(action) < len(node_order) else node_order[0])
            compromised = set(sim.compromised)
            newly = compromised - before
            if any(g.get_node(n).is_critical_asset for n in newly):
                episode_result = "red_win"
                done = True
                break

            # Defender turn
            obs_def = _build_obs(g, node_order)
            def_mask = np.zeros(2 * MAX_NODES, dtype=bool)
            for i, nid in enumerate(node_order):
                node = g.get_node(nid)
                if node.num_vulns > 0 and not node.is_patched:
                    def_mask[i] = True
                if not node.is_isolated:
                    def_mask[MAX_NODES + i] = True

            def_action, _ = blue_model.predict(obs_def, action_masks=def_mask, deterministic=False)
            def_action = int(def_action)
            n = len(node_order)
            try:
                action_kind, action_index = decode_defender_action(def_action, n)
                nid = node_order[action_index]
                node = g.get_node(nid)
                if action_kind == "patch":
                    node.vulnerabilities = []
                    node.is_patched = True
                else:
                    g.get_node(nid).is_isolated = True
            except ValueError:
                pass

            step += 2

        if episode_result == "red_win":
            red_wins += 1
        else:
            blue_wins += 1

    return {
        "red_win_rate": red_wins / n_episodes,
        "blue_win_rate": blue_wins / n_episodes,
        "n_episodes": n_episodes,
    }


# ---------------------------------------------------------------------------
# Main alternating training loop
# ---------------------------------------------------------------------------

def main(args):
    if not HAS_SB3_CONTRIB:
        raise ImportError("sb3-contrib not installed.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---- Load or create initial agents ----
    red_path = args.red_start
    blue_path = args.blue_start

    def make_red_env(seed=0):
        def _init():
            return Monitor(AttackerEnv(args.topology, args.cve_path, max_steps=50, seed=seed))
        return _init

    def make_blue_env(seed=0):
        def _init():
            return Monitor(DefenderEnv(args.topology, args.cve_path, max_steps=50, seed=seed))
        return _init

    # Initialise red agent
    red_env = DummyVecEnv([make_red_env(i) for i in range(4)])
    if red_path and Path(red_path).exists():
        print(f"Loading red agent from {red_path}")
        red_model = MaskablePPO.load(red_path, env=red_env)
    else:
        print("Creating new red agent")
        red_model = MaskablePPO("MlpPolicy", red_env, n_steps=2048, batch_size=64,
                                n_epochs=10, learning_rate=3e-4, ent_coef=0.01,
                                verbose=0, seed=42, tensorboard_log=str(output_dir / "tb"))

    # Initialise blue agent
    blue_env = DummyVecEnv([make_blue_env(i) for i in range(4)])
    if blue_path and Path(blue_path).exists():
        print(f"Loading blue agent from {blue_path}")
        blue_model = MaskablePPO.load(blue_path, env=blue_env)
    else:
        print("Creating new blue agent")
        blue_model = MaskablePPO("MlpPolicy", blue_env, n_steps=2048, batch_size=64,
                                 n_epochs=10, learning_rate=3e-4, ent_coef=0.01,
                                 verbose=0, seed=42, tensorboard_log=str(output_dir / "tb"))

    # ---- Alternating training ----
    round_results = []
    steps_per_round = args.steps_per_round

    for round_num in range(1, args.n_rounds + 1):
        print(f"\n{'='*60}")
        print(f"  MARL ROUND {round_num}/{args.n_rounds}")
        print(f"{'='*60}")

        # --- Train Red (freeze Blue) ---
        print(f"  [Round {round_num}] Training Red for {steps_per_round:,} steps...")
        red_model.set_env(red_env)
        red_model.learn(total_timesteps=steps_per_round, reset_num_timesteps=False, progress_bar=True)

        red_success = evaluate_red_vs_rule_based(red_model, args.topology, args.cve_path)
        print(f"  Red success rate (vs rule-based): {red_success*100:.1f}%")

        red_model.save(str(output_dir / f"red_round_{round_num}.zip"))

        # --- Train Blue (freeze Red) ---
        print(f"  [Round {round_num}] Training Blue for {steps_per_round:,} steps...")
        blue_model.set_env(blue_env)
        blue_model.learn(total_timesteps=steps_per_round, reset_num_timesteps=False, progress_bar=True)

        blue_model.save(str(output_dir / f"blue_round_{round_num}.zip"))

        # --- Evaluate Red vs Blue ---
        print(f"  [Round {round_num}] Evaluating Red vs Blue...")
        results = evaluate_red_vs_blue(
            red_model, blue_model,
            args.topology, args.cve_path,
            n_episodes=100,
        )
        results["round"] = round_num
        results["red_vs_rule_based"] = red_success
        round_results.append(results)

        print(f"  Red win rate:  {results['red_win_rate']*100:.1f}%")
        print(f"  Blue win rate: {results['blue_win_rate']*100:.1f}%")

    # ---- Save final agents and results ----
    red_model.save(str(output_dir / "red_final.zip"))
    blue_model.save(str(output_dir / "blue_final.zip"))

    results_path = output_dir / "marl_results.json"
    with open(results_path, "w") as f:
        json.dump(round_results, f, indent=2)

    print(f"\nMARL training complete.")
    print(f"Final agents: {output_dir}/red_final.zip, {output_dir}/blue_final.zip")
    print(f"Round results: {results_path}")
    print("\nArms-race summary:")
    for r in round_results:
        print(f"  Round {r['round']}: Red={r['red_win_rate']*100:.1f}%  Blue={r['blue_win_rate']*100:.1f}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topology",      default="data/topologies/enterprise_20n.json")
    parser.add_argument("--cve_path",      default="data/cve/cve_dataset.json")
    parser.add_argument("--red_start",     default="checkpoints/red_agent.zip")
    parser.add_argument("--blue_start",    default="checkpoints/blue_agent.zip")
    parser.add_argument("--output_dir",    default="checkpoints/marl")
    parser.add_argument("--n_rounds",      default=5, type=int)
    parser.add_argument("--steps_per_round", default=200_000, type=int)
    args = parser.parse_args()
    main(args)
