"""
train_red.py — Train the Red (attacker) agent using MaskablePPO.

The attacker learns to find optimal paths to critical assets.
Action masking ensures it only selects reachable, vulnerable nodes.

Usage:
    python -m src.training.train_red \
        --topology data/topologies/enterprise_20n.json \
        --cve_path data/cve/cve_dataset.json \
        --output checkpoints/red_agent.zip \
        --timesteps 1000000

Target:
    Attack success rate 70-85% vs 30-40% random baseline
"""

from __future__ import annotations
import argparse
import os
from pathlib import Path

import numpy as np
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv

try:
    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.maskable.callbacks import MaskableEvalCallback
    HAS_SB3_CONTRIB = True
except ImportError:
    HAS_SB3_CONTRIB = False

from src.envs.attacker_env import AttackerEnv


def make_env(topology_path: str, cve_path: str, seed: int = 0):
    def _init():
        env = AttackerEnv(topology_path=topology_path, cve_path=cve_path, max_steps=50, seed=seed)
        env = Monitor(env)
        return env
    return _init


def evaluate_random_baseline(topology_path: str, cve_path: str, n_episodes: int = 200) -> float:
    """Compute random agent success rate for comparison."""
    env = AttackerEnv(topology_path=topology_path, cve_path=cve_path, max_steps=50)
    successes = 0
    for _ in range(n_episodes):
        obs, info = env.reset()
        done = False
        while not done:
            mask = info["action_mask"]
            valid = np.where(mask)[0]
            if len(valid) == 0:
                break
            action = int(np.random.choice(valid))
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            if terminated:
                successes += 1
    return successes / n_episodes


def main(args):
    if not HAS_SB3_CONTRIB:
        raise ImportError("sb3-contrib not installed. Run: pip install sb3-contrib")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.log_dir).mkdir(parents=True, exist_ok=True)

    # ---- Random baseline ----
    print("Computing random baseline...")
    baseline = evaluate_random_baseline(args.topology, args.cve_path, n_episodes=200)
    print(f"Random baseline attack success rate: {baseline*100:.1f}%")

    # ---- Environment ----
    n_envs = 4
    env = DummyVecEnv([make_env(args.topology, args.cve_path, seed=i) for i in range(n_envs)])

    eval_env = DummyVecEnv([make_env(args.topology, args.cve_path, seed=999)])

    # ---- Model ----
    model = MaskablePPO(
        policy="MlpPolicy",
        env=env,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        learning_rate=3e-4,
        ent_coef=0.01,
        clip_range=0.2,
        gamma=0.99,
        gae_lambda=0.95,
        verbose=1,
        tensorboard_log=args.log_dir,
        seed=42,
    )

    print(f"Training MaskablePPO red agent for {args.timesteps:,} steps...")
    print(f"  Topology: {args.topology}")
    print(f"  Output:   {args.output}")

    # ---- Callbacks ----
    eval_callback = MaskableEvalCallback(
        eval_env,
        best_model_save_path=str(Path(args.output).parent),
        log_path=args.log_dir,
        eval_freq=10000,
        n_eval_episodes=50,
        deterministic=True,
        verbose=1,
    )

    checkpoint_callback = CheckpointCallback(
        save_freq=50000,
        save_path=str(Path(args.output).parent / "checkpoints_red"),
        name_prefix="red_agent",
    )

    # ---- Train ----
    model.learn(
        total_timesteps=args.timesteps,
        callback=[eval_callback, checkpoint_callback],
        progress_bar=True,
    )
    model.save(args.output)
    print(f"Saved red agent to {args.output}")

    # ---- Final evaluation ----
    print("\nEvaluating trained agent...")
    eval_env_single = AttackerEnv(topology_path=args.topology, cve_path=args.cve_path, max_steps=50)
    successes = 0
    n_eval = 500
    for _ in range(n_eval):
        obs, info = eval_env_single.reset()
        done = False
        while not done:
            action, _ = model.predict(obs, action_masks=info["action_mask"], deterministic=True)
            obs, reward, terminated, truncated, info = eval_env_single.step(int(action))
            done = terminated or truncated
            if terminated:
                successes += 1
    success_rate = successes / n_eval
    print(f"Trained agent attack success rate: {success_rate*100:.1f}%")
    print(f"Improvement over random: +{(success_rate - baseline)*100:.1f}pp")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topology", default="data/topologies/enterprise_20n.json")
    parser.add_argument("--cve_path", default="data/cve/cve_dataset.json")
    parser.add_argument("--output",   default="checkpoints/red_agent.zip")
    parser.add_argument("--log_dir",  default="logs/red")
    parser.add_argument("--timesteps", default=1_000_000, type=int)
    args = parser.parse_args()
    main(args)
