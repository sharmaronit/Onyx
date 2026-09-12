"""
attacker_env.py — Single-agent Gymnasium environment for the Red (attacker) agent.

Key design decisions:
- Observation: padded flat vector of shape (MAX_NODES * 11,)
  All topologies padded to MAX_NODES=50 with zeros.
- Action space: Discrete(MAX_NODES)
- Action masking: info["action_mask"] returned as boolean array —
  MaskablePPO (sb3-contrib) uses this to prevent invalid actions.
- Reward:
    +1.0 per node compromised
    +10.0 for critical asset
    -0.1 per step
    -0.5 for invalid action
"""

from __future__ import annotations
import random
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Optional, Tuple, Dict, Any

from src.graph.network_graph import NetworkGraph
from src.graph.topology_loader import load_topology
from src.graph.cve_tagger import load_cve_database, tag_graph
from src.simulator.rule_based import AttackSimulator

MAX_NODES = 50
NODE_FEAT_DIM = 11


def _build_obs(graph: NetworkGraph, node_order: list) -> np.ndarray:
    """
    Build a flat (MAX_NODES * NODE_FEAT_DIM,) observation vector.
    Entries beyond len(node_order) are zero-padded.
    """
    from src.graph.network_graph import NODE_TYPES
    _TYPE_ORDER = ["server", "workstation", "router", "firewall"]
    _MAX_VULNS = 5.0

    obs = np.zeros(MAX_NODES * NODE_FEAT_DIM, dtype=np.float32)
    dc = graph.degree_centrality()

    for i, nid in enumerate(node_order):
        n = graph.get_node(nid)
        type_idx = _TYPE_ORDER.index(n.node_type) if n.node_type in _TYPE_ORDER else 0
        oh = [0.0] * 4
        oh[type_idx] = 1.0

        feat = [
            float(n.is_compromised),
            n.max_cvss / 10.0,
            min(n.num_vulns / _MAX_VULNS, 1.0),
        ] + oh + [
            float(n.is_critical_asset),
            float(n.is_patched),
            float(n.is_isolated),
            dc.get(nid, 0.0),
        ]
        obs[i * NODE_FEAT_DIM: (i + 1) * NODE_FEAT_DIM] = feat

    return obs


def _build_action_mask(
    graph: NetworkGraph,
    node_order: list,
    compromised_set: set,
) -> np.ndarray:
    """
    Boolean mask of shape (MAX_NODES,).
    True  = valid action (reachable, not compromised, not isolated, not patched).
    False = invalid.
    """
    reachable = set(graph.reachable_from(list(compromised_set)))
    mask = np.zeros(MAX_NODES, dtype=bool)
    for i, nid in enumerate(node_order):
        node = graph.get_node(nid)
        if (
            nid in reachable
            and nid not in compromised_set
            and not node.is_isolated
            and not node.is_patched
        ):
            mask[i] = True
    return mask


class AttackerEnv(gym.Env):
    """
    Gymnasium environment for the single-agent Red (attacker) agent.

    Parameters
    ----------
    topology_path : str
        Path to a topology JSON file.
    cve_path : str
        Path to cve_dataset.json.
    max_steps : int
        Episode truncation limit.
    seed : int or None
    transition_model : TransitionModel or None
        If None, uses rule-based simulator.
        If GNNTransition, uses the learned world model.
    """

    metadata = {"render_modes": ["ansi"]}

    def __init__(
        self,
        topology_path: str,
        cve_path: str,
        max_steps: int = 50,
        seed: Optional[int] = None,
        transition_model=None,
    ):
        super().__init__()
        self.topology_path = topology_path
        self.cve_path = cve_path
        self.max_steps = max_steps
        self._seed = seed
        self._rng = random.Random(seed)

        # Load and tag graph
        self._base_graph = load_topology(topology_path)
        self._cve_db = load_cve_database(cve_path)
        tag_graph(self._base_graph, self._cve_db)

        # Node ordering is fixed for the lifetime of this env
        self._node_order = sorted(self._base_graph.node_ids)
        self._n_real = len(self._node_order)
        assert self._n_real <= MAX_NODES, f"Graph has {self._n_real} nodes > MAX_NODES={MAX_NODES}"

        # Simulator (will be reset each episode)
        self._sim: Optional[AttackSimulator] = None
        self._step_count = 0
        self._compromised: set = set()

        # Gymnasium spaces
        self.observation_space = spaces.Box(
            low=0.0, high=1.0,
            shape=(MAX_NODES * NODE_FEAT_DIM,),
            dtype=np.float32,
        )
        self.action_space = spaces.Discrete(MAX_NODES)

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

        # Deep-copy base graph so each episode is independent
        self._graph = self._base_graph.deep_copy()
        tag_graph(self._graph, self._cve_db)

        self._sim = AttackSimulator(self._graph, max_steps=self.max_steps, seed=self._rng.randint(0, 10**6))
        self._entry = self._sim.reset()
        self._compromised = set(self._sim.compromised)
        self._step_count = 0

        obs = _build_obs(self._graph, self._node_order)
        info = {
            "action_mask": _build_action_mask(self._graph, self._node_order, self._compromised),
            "entry_point": self._entry,
            "n_real_nodes": self._n_real,
        }
        return obs, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        self._step_count += 1
        terminated = False
        truncated = False

        # Map action index → node_id (guard out-of-range)
        if action >= self._n_real:
            reward = -0.5
        else:
            action_node_id = self._node_order[action]
            reward, done = self._sim.step(action_node_id)
            self._compromised = set(self._sim.compromised)

            terminated = done and self._step_count < self.max_steps
            # Check if critical asset captured
            for ca in self._graph.critical_assets:
                if ca in self._compromised:
                    terminated = True
                    break

        truncated = self._step_count >= self.max_steps

        obs = _build_obs(self._graph, self._node_order)
        info = {
            "action_mask": _build_action_mask(self._graph, self._node_order, self._compromised),
            "compromised": list(self._compromised),
            "n_real_nodes": self._n_real,
        }
        return obs, float(reward), terminated, truncated, info

    def action_masks(self) -> np.ndarray:
        """Called by MaskablePPO to get the valid action mask."""
        return _build_action_mask(self._graph, self._node_order, self._compromised)

    def render(self) -> str:
        lines = ["=== AttackerEnv State ==="]
        for nid in self._node_order:
            node = self._graph.get_node(nid)
            status = "COMPROMISED" if node.is_compromised else "clean"
            lines.append(f"  {nid:25s} cvss={node.max_cvss:.1f}  {status}")
        return "\n".join(lines)
