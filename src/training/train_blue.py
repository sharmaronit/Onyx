"""
train_blue.py — Train the Blue (defender) agent using MaskablePPO.

The defender learns to patch and isolate nodes to prevent the attacker
from reaching critical assets. The attacker in this phase is the
rule-based simulator (replaced by trained Red agent in train_marl.py).

Usage:
    python -m src.training.train_blue \
        --topology data/topologies/enterprise_20n.json \
        --cve_path data/cve/cve_dataset.json \
        --output checkpoints/blue_agent.zip \
        --timesteps 1000000
"""

from __future__ import annotations
import argparse
from pathlib import Path

from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback

try:
    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.maskable.callbacks import MaskableEvalCallback
    HAS_SB3_CONTRIB = True
except ImportError:
    HAS_SB3_CONTRIB = False

from src.envs.defender_env import DefenderEnv


def make_env(topology_path: str, cve_path: str, seed: int = 0):
    def _init():
        env = DefenderEnv(topology_path=topology_path, cve_path=cve_path, max_steps=50, seed=seed)
        env = Monitor(env)
        return env
    return _init


def main(args):
    if not HAS_SB3_CONTRIB:
        raise ImportError("sb3-contrib not installed.")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.log_dir).mkdir(parents=True, exist_ok=True)

    n_envs = 4
    env = DummyVecEnv([make_env(args.topology, args.cve_path, seed=i) for i in range(n_envs)])
    eval_env = DummyVecEnv([make_env(args.topology, args.cve_path, seed=888)])

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

    print(f"Training MaskablePPO blue (defender) agent for {args.timesteps:,} steps...")
    print(f"  Topology: {args.topology}")
    print(f"  Output:   {args.output}")

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
        save_path=str(Path(args.output).parent / "checkpoints_blue"),
        name_prefix="blue_agent",
    )

    model.learn(
        total_timesteps=args.timesteps,
        callback=[eval_callback, checkpoint_callback],
        progress_bar=True,
    )
    model.save(args.output)
    print(f"Saved blue agent to {args.output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topology", default="data/topologies/enterprise_20n.json")
    parser.add_argument("--cve_path", default="data/cve/cve_dataset.json")
    parser.add_argument("--output",   default="checkpoints/blue_agent.zip")
    parser.add_argument("--log_dir",  default="logs/blue")
    parser.add_argument("--timesteps", default=1_000_000, type=int)
    args = parser.parse_args()
    main(args)
