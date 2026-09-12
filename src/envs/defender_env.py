"""
defender_env.py — Single-agent Gymnasium environment for the Blue (defender) agent.

Action space: Discrete(2 * MAX_NODES)
  Actions 0..MAX_NODES-1:              patch node i
  Actions MAX_NODES..2*MAX_NODES-1:    isolate node i

Observation: same padded flat vector (MAX_NODES * 11,) as AttackerEnv —
  the defender observes the same graph state, including which nodes the
  attacker has compromised.

Reward:
  -1.0  per node the attacker compromises on its turn
  +10.0 if episode ends without critical asset compromised
  -0.05 per step (encourages decisive actions)
"""

from __future__ import annotations
import random
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Optional, Tuple, Dict

from src.graph.network_graph import NetworkGraph
from src.graph.topology_loader import load_topology
from src.graph.cve_tagger import load_cve_database, tag_graph
from src.simulator.rule_based import AttackSimulator
from src.envs.attacker_env import (
    MAX_NODES, NODE_FEAT_DIM,
    _build_obs, _build_action_mask
)


def encode_patch(node_index: int) -> int:
    if not 0 <= node_index < MAX_NODES:
        raise ValueError(f"Invalid patch node index {node_index}")
    return node_index


def encode_isolate(node_index: int) -> int:
    if not 0 <= node_index < MAX_NODES:
        raise ValueError(f"Invalid isolate node index {node_index}")
    return MAX_NODES + node_index


def decode_defender_action(action: int, n_real: int) -> Tuple[str, int]:
    """Decode the shared padded defender action space.

    Raises ``ValueError`` for padded or out-of-range actions so masks and
    execution cannot silently disagree.
    """
    if 0 <= action < n_real:
        return "patch", action
    if MAX_NODES <= action < MAX_NODES + n_real:
        return "isolate", action - MAX_NODES
    raise ValueError(f"Invalid defender action {action} for {n_real} nodes")


class DefenderEnv(gym.Env):
    """
    Gymnasium environment for the single-agent Blue (defender) agent.
    The attacker is a fixed rule-based simulator (replaced by trained
    Red agent in train_marl.py).

    Parameters
    ----------
    topology_path : str
    cve_path : str
    max_steps : int
        Total episode steps (each step = 1 attacker move + 1 defender move).
    seed : int or None
    """

    metadata = {"render_modes": ["ansi"]}

    def __init__(
        self,
        topology_path: str,
        cve_path: str,
        max_steps: int = 50,
        seed: Optional[int] = None,
    ):
        super().__init__()
        self.topology_path = topology_path
        self.cve_path = cve_path
        self.max_steps = max_steps
        self._rng = random.Random(seed)

        self._base_graph = load_topology(topology_path)
        self._cve_db = load_cve_database(cve_path)
        tag_graph(self._base_graph, self._cve_db)

        self._node_order = sorted(self._base_graph.node_ids)
        self._n_real = len(self._node_order)
        assert self._n_real <= MAX_NODES

        self.observation_space = spaces.Box(
            low=0.0, high=1.0,
            shape=(MAX_NODES * NODE_FEAT_DIM,),
            dtype=np.float32,
        )
        # First N: patch, next N: isolate
        self.action_space = spaces.Discrete(2 * MAX_NODES)

        self._graph = None
        self._sim = None
        self._compromised = set()
        self._step_count = 0

    # ------------------------------------------------------------------
    # Gymnasium interface
    # ------------------------------------------------------------------

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None,
    ) -> Tuple[np.ndarray, Dict]:
        if seed is not None:
            self._rng = random.Random(seed)

        self._graph = self._base_graph.deep_copy()
        tag_graph(self._graph, self._cve_db)
        self._sim = AttackSimulator(self._graph, max_steps=self.max_steps, seed=self._rng.randint(0, 10**6))
        self._sim.reset()
        self._compromised = set(self._sim.compromised)
        self._step_count = 0

        obs = _build_obs(self._graph, self._node_order)
        info = {
            "action_mask": self._defender_action_mask(),
            "n_real_nodes": self._n_real,
        }
        return obs, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        self._step_count += 1
        terminated = False
        truncated = False
        reward = -0.05  # step penalty

        # --- Attacker move (rule-based) ---
        candidates = self._sim.reachable_targets
        if candidates:
            atk_action = self._rng.choice(candidates)
            compromised_before = set(self._sim.compromised)
            self._sim.step(atk_action)
            self._compromised = set(self._sim.compromised)
            newly_compromised = self._compromised - compromised_before
            reward += -1.0 * len(newly_compromised)

            # Check if critical asset taken
            for ca in self._graph.critical_assets:
                if ca in self._compromised:
                    terminated = True

        # --- Defender move ---
        if not terminated:
            self._apply_defender_action(action)

        truncated = self._step_count >= self.max_steps

        if truncated or terminated:
            # Bonus if critical assets protected
            critical_intact = all(
                ca not in self._compromised
                for ca in self._graph.critical_assets
            )
            if critical_intact:
                reward += 10.0

        obs = _build_obs(self._graph, self._node_order)
        info = {
            "action_mask": self._defender_action_mask(),
            "compromised": list(self._compromised),
            "n_real_nodes": self._n_real,
        }
        return obs, float(reward), terminated, truncated, info

    # ------------------------------------------------------------------
    # Defender action helpers
    # ------------------------------------------------------------------

    def _apply_defender_action(self, action: int):
        """Apply a mask-compatible patch or isolation action."""
        try:
            action_kind, idx = decode_defender_action(int(action), self._n_real)
        except ValueError:
            return
        nid = self._node_order[idx]
        node = self._graph.get_node(nid)
        if action_kind == "patch":
            # Patch: remove all vulnerabilities from node
            node.vulnerabilities = []
            node.is_patched = True
        else:
            # Isolate: mark node as isolated (no edges traversed)
            node.is_isolated = True

    def _defender_action_mask(self) -> np.ndarray:
        """
        Valid defender actions:
         - Patch: node has vulnerabilities and is not already patched
         - Isolate: node is not already isolated
        """
        mask = np.zeros(2 * MAX_NODES, dtype=bool)
        for i, nid in enumerate(self._node_order):
            node = self._graph.get_node(nid)
            # Patch valid
            if node.num_vulns > 0 and not node.is_patched:
                mask[encode_patch(i)] = True
            # Isolate valid
            if not node.is_isolated:
                mask[encode_isolate(i)] = True
        return mask

    def action_masks(self) -> np.ndarray:
        return self._defender_action_mask()

    def render(self) -> str:
        lines = ["=== DefenderEnv State ==="]
        for nid in self._node_order:
            node = self._graph.get_node(nid)
            tags = []
            if node.is_compromised:
                tags.append("COMPROMISED")
            if node.is_patched:
                tags.append("PATCHED")
            if node.is_isolated:
                tags.append("ISOLATED")
            lines.append(f"  {nid:25s}  {' '.join(tags) or 'ok'}")
        return "\n".join(lines)
