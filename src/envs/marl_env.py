"""
marl_env.py — PettingZoo AECEnv for Onyx Multi-Agent RL.

Turn order: attacker acts, then defender acts, repeat.
Both agents observe the same full graph state.

Attacker: Discrete(MAX_NODES)       + action masking
Defender: Discrete(2 * MAX_NODES)   + action masking
  Defender actions 0..N-1:   patch node i
  Defender actions N..2N-1:  isolate node i
"""

from __future__ import annotations
import random
import numpy as np
from typing import Optional, Dict, Any

try:
    import gymnasium as gym
    from gymnasium import spaces
    from pettingzoo import AECEnv
    from pettingzoo.utils.agent_selector import agent_selector
    HAS_PETTINGZOO = True
except ImportError:
    HAS_PETTINGZOO = False

from src.graph.topology_loader import load_topology
from src.graph.cve_tagger import load_cve_database, tag_graph
from src.simulator.rule_based import AttackSimulator
from src.envs.attacker_env import (
    MAX_NODES, NODE_FEAT_DIM,
    _build_obs, _build_action_mask,
)
from src.envs.defender_env import DefenderEnv


class OnyxMARLEnv(AECEnv if HAS_PETTINGZOO else object):
    """
    PettingZoo AECEnv implementing the Red vs Blue multi-agent game.

    Agents: ["attacker_0", "defender_0"]
    Turn order: attacker → defender → attacker → ...

    Parameters
    ----------
    topology_path : str
    cve_path : str
    max_steps : int  (per-agent steps; episode = 2 * max_steps total turns)
    seed : int or None
    """

    metadata = {"render_modes": ["ansi"], "name": "onyx_marl_v0"}

    def __init__(
        self,
        topology_path: str,
        cve_path: str,
        max_steps: int = 50,
        seed: Optional[int] = None,
    ):
        if not HAS_PETTINGZOO:
            raise ImportError("pettingzoo not installed.")

        self.topology_path = topology_path
        self.cve_path = cve_path
        self.max_steps = max_steps
        self._rng = random.Random(seed)

        self._base_graph = load_topology(topology_path)
        self._cve_db = load_cve_database(cve_path)
        tag_graph(self._base_graph, self._cve_db)

        self._node_order = sorted(self._base_graph.node_ids)
        self._n_real = len(self._node_order)

        # PettingZoo required attributes
        self.possible_agents = ["attacker_0", "defender_0"]
        self.agents = self.possible_agents[:]
        self._agent_selector = agent_selector(self.possible_agents)

        obs_dim = MAX_NODES * NODE_FEAT_DIM

        self.observation_spaces = {
            "attacker_0": spaces.Box(0.0, 1.0, shape=(obs_dim,), dtype=np.float32),
            "defender_0": spaces.Box(0.0, 1.0, shape=(obs_dim,), dtype=np.float32),
        }
        self.action_spaces = {
            "attacker_0": spaces.Discrete(MAX_NODES),
            "defender_0": spaces.Discrete(2 * MAX_NODES),
        }

        # Episode state (initialised in reset())
        self._graph = None
        self._sim = None
        self._compromised = set()
        self._step_count = 0

    # ------------------------------------------------------------------
    # PettingZoo interface
    # ------------------------------------------------------------------

    def observation_space(self, agent: str):
        return self.observation_spaces[agent]

    def action_space(self, agent: str):
        return self.action_spaces[agent]

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None,
    ):
        if seed is not None:
            self._rng = random.Random(seed)

        self._graph = self._base_graph.deep_copy()
        tag_graph(self._graph, self._cve_db)
        self._sim = AttackSimulator(self._graph, max_steps=self.max_steps, seed=self._rng.randint(0, 10**6))
        self._sim.reset()
        self._compromised = set(self._sim.compromised)
        self._step_count = 0

        self.agents = self.possible_agents[:]
        self.agent_selection = self._agent_selector.reset()

        obs = _build_obs(self._graph, self._node_order)
        self.observations = {agent: obs for agent in self.agents}

        self.rewards = {agent: 0.0 for agent in self.agents}
        self.terminations = {agent: False for agent in self.agents}
        self.truncations = {agent: False for agent in self.agents}
        self.infos = {
            "attacker_0": {"action_mask": self._attacker_mask()},
            "defender_0": {"action_mask": self._defender_mask()},
        }

    def step(self, action: int):
        agent = self.agent_selection
        self._step_count += 1

        if agent == "attacker_0":
            self._attacker_step(action)
        else:
            self._defender_step(action)

        # Check termination
        critical_taken = any(
            ca in self._compromised for ca in self._graph.critical_assets
        )
        episode_over = self._step_count >= self.max_steps * 2

        if critical_taken or episode_over:
            for a in self.agents:
                self.terminations[a] = critical_taken
                self.truncations[a] = episode_over and not critical_taken

            # Terminal rewards
            if critical_taken:
                self.rewards["attacker_0"] += 0.0  # already rewarded step-by-step
                self.rewards["defender_0"] += -10.0
            else:
                self.rewards["defender_0"] += 10.0  # protected all critical assets

            self.agents = []
        else:
            # Update observations and masks
            obs = _build_obs(self._graph, self._node_order)
            self.observations = {a: obs for a in self.agents}
            self.infos = {
                "attacker_0": {"action_mask": self._attacker_mask()},
                "defender_0": {"action_mask": self._defender_mask()},
            }
            self.agent_selection = self._agent_selector.next()

    def observe(self, agent: str) -> np.ndarray:
        return self.observations.get(agent, np.zeros(MAX_NODES * NODE_FEAT_DIM, dtype=np.float32))

    def render(self) -> str:
        lines = [f"=== MARL Step {self._step_count} ==="]
        for nid in self._node_order:
            n = self._graph.get_node(nid)
            tags = []
            if n.is_compromised:  tags.append("ATK")
            if n.is_patched:      tags.append("PATCHED")
            if n.is_isolated:     tags.append("ISOLATED")
            lines.append(f"  {nid:25s}  {','.join(tags) or 'ok'}")
        return "\n".join(lines)

    def close(self):
        pass

    # ------------------------------------------------------------------
    # Internal action handlers
    # ------------------------------------------------------------------

    def _attacker_step(self, action: int):
        reward = -0.1
        if action < self._n_real:
            action_nid = self._node_order[action]
            before = set(self._sim.compromised)
            step_reward, _ = self._sim.step(action_nid)
            self._compromised = set(self._sim.compromised)
            newly = self._compromised - before
            reward = step_reward
            if any(self._graph.get_node(n).is_critical_asset for n in newly):
                reward += 10.0
        self.rewards["attacker_0"] = reward
        self.rewards["defender_0"] = 0.0

    def _defender_step(self, action: int):
        reward = -0.05
        n = self._n_real
        if action < n:
            # Patch
            nid = self._node_order[action]
            node = self._graph.get_node(nid)
            if not node.is_patched:
                node.vulnerabilities = []
                node.is_patched = True
        elif action < 2 * n:
            # Isolate
            idx = action - n
            if idx < n:
                nid = self._node_order[idx]
                node = self._graph.get_node(nid)
                if not node.is_isolated:
                    node.is_isolated = True

        # Penalise if attacker just compromised nodes
        reward += -1.0 * len([
            nid for nid in self._node_order
            if self._graph.get_node(nid).is_compromised
        ]) * 0.05

        self.rewards["defender_0"] = reward
        self.rewards["attacker_0"] = 0.0

    def _attacker_mask(self) -> np.ndarray:
        return _build_action_mask(self._graph, self._node_order, self._compromised)

    def _defender_mask(self) -> np.ndarray:
        mask = np.zeros(2 * MAX_NODES, dtype=bool)
        for i, nid in enumerate(self._node_order):
            node = self._graph.get_node(nid)
            if node.num_vulns > 0 and not node.is_patched:
                mask[i] = True
            if not node.is_isolated:
                mask[MAX_NODES + i] = True
        return mask
