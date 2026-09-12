"""
rule_based.py — Rule-based attack simulator for Onyx.

Transition probability: P(compromise node X) = max_cvss(X) / 10.0
This provides a fast, interpretable baseline and generates training data
for the GNN world model.
"""

from __future__ import annotations
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import networkx as nx

from src.graph.network_graph import NetworkGraph


# ---------------------------------------------------------------------------
# Episode data structures
# ---------------------------------------------------------------------------

@dataclass
class Transition:
    """A single (state, action, next_state, reward, done) transition."""
    step: int
    action_node_id: str
    attacker_reachable: List[str]           # candidate targets before action
    success: bool
    reward: float
    newly_compromised: List[str]            # nodes compromised THIS step
    compromised_set_before: List[str]
    compromised_set_after: List[str]
    done: bool


@dataclass
class Episode:
    """Complete attack episode record."""
    entry_point: str
    target_node: str
    transitions: List[Transition] = field(default_factory=list)
    reached_target: bool = False
    total_steps: int = 0
    total_reward: float = 0.0

    @property
    def attack_path(self) -> List[str]:
        """Ordered list of nodes compromised across the episode."""
        path = [self.entry_point]
        for t in self.transitions:
            if t.success and t.action_node_id not in path:
                path.append(t.action_node_id)
        return path

    @property
    def success(self) -> bool:
        return self.reached_target


def recommended_episode_limit(
    graph: NetworkGraph,
    floor: int = 10,
    ceiling: int = 40,
) -> int:
    """Estimate a topology-aware max step budget for one episode.

    The limit is based on graph size and shortest entry-to-critical depth.
    This keeps small topologies tighter and gives larger topologies enough
    room without encouraging excessive retry behavior.
    """
    num_nodes = max(1, int(graph.num_nodes))
    entry_points = graph.entry_points or graph.node_ids[:1]
    critical_assets = graph.critical_assets or graph.node_ids[-1:]

    depths: List[int] = []
    for src in entry_points:
        for dst in critical_assets:
            if src == dst:
                continue
            try:
                depths.append(int(nx.shortest_path_length(graph.G, source=src, target=dst)))
            except nx.NetworkXNoPath:
                continue

    shortest_depth = min(depths) if depths else max(2, num_nodes // 4)
    proposed = int(round(shortest_depth * 2.2 + num_nodes * 0.35))
    return max(floor, min(ceiling, proposed))


# ---------------------------------------------------------------------------
# AttackSimulator
# ---------------------------------------------------------------------------

class AttackSimulator:
    """
    Rule-based attacker that traverses the network graph.

    Parameters
    ----------
    graph : NetworkGraph
        A tagged network graph (must have CVEs attached via cve_tagger).
    max_steps : int
        Maximum steps per episode before truncation.
    seed : int or None
        Random seed for reproducibility.
    """

    def __init__(
        self,
        graph: NetworkGraph,
        max_steps: int = 50,
        max_attempts_per_target: int = 2,
        seed: Optional[int] = None,
    ):
        self.graph = graph
        self.max_steps = max_steps
        self.max_attempts_per_target = max_attempts_per_target
        self._rng = random.Random(seed)
        self._step_count = 0
        self._compromised: set = set()
        self._done = False
        self._attempts_by_target: Dict[str, int] = {}

    @staticmethod
    def _connection_multiplier(connection_type: str) -> float:
        return {
            "http": 0.83,
            "ssh": 0.79,
            "rdp": 0.74,
            "sql": 0.71,
            "ftp": 0.66,
            "vpn": 0.70,
        }.get(connection_type, 0.76)

    @staticmethod
    def _permission_multiplier(permission_level: str) -> float:
        return {
            "read": 0.68,
            "write": 0.82,
            "admin": 1.0,
        }.get(permission_level, 0.68)

    @classmethod
    def _attack_vector_multiplier(cls, connection_type: str, permission_level: str, attack_vector: str) -> float:
        vector = (attack_vector or "local").lower()
        if vector == "network":
            return 1.0
        if vector == "adjacent":
            return 0.72 if connection_type in {"rdp", "ssh", "vpn"} else 0.42
        if permission_level == "admin":
            return 0.28
        if permission_level == "write":
            return 0.12
        return 0.06

    def _best_compromise_probability(self, target_node_id: str, attempts: int) -> float:
        target = self.graph.get_node(target_node_id)
        if not target.vulnerabilities:
            return 0.0

        best_path_probability = 0.0
        for source_id in self._compromised:
            edge = self.graph.get_edge(source_id, target_node_id)
            if not edge:
                continue

            connection_multiplier = self._connection_multiplier(edge.connection_type)
            permission_multiplier = self._permission_multiplier(edge.permission_level)
            firewall_multiplier = 0.6 if edge.has_firewall else 1.0
            edge_multiplier = connection_multiplier * permission_multiplier * firewall_multiplier

            for vuln in target.vulnerabilities:
                base_probability = min(0.92, max(0.05, float(vuln.cvss_score) / 10.0))
                vector_multiplier = self._attack_vector_multiplier(
                    edge.connection_type,
                    edge.permission_level,
                    vuln.attack_vector,
                )
                candidate = base_probability * edge_multiplier * vector_multiplier
                best_path_probability = max(best_path_probability, candidate)

        if best_path_probability <= 0.0:
            return 0.0

        critical_hardening = 0.78 if target.is_critical_asset else 1.0
        attempt_decay = 0.62 ** attempts
        detection_drag = max(0.45, 1.0 - 0.035 * len(self._compromised))

        p_success = best_path_probability * critical_hardening * attempt_decay * detection_drag
        return max(0.0, min(0.88, p_success))

    # ------------------------------------------------------------------
    # Episode control
    # ------------------------------------------------------------------

    def reset(self, entry_point: Optional[str] = None) -> str:
        """
        Reset simulator for a new episode.

        Parameters
        ----------
        entry_point : str or None
            Node to start from. If None, a random entry_point is chosen.

        Returns
        -------
        str
            The entry point node id used.
        """
        self.graph.reset_runtime_state()
        self._step_count = 0
        self._done = False
        self._attempts_by_target = {}

        # Choose entry point
        entry_points = self.graph.entry_points
        if not entry_points:
            # Fallback: pick a random node
            entry_points = self.graph.node_ids

        if entry_point is None:
            entry_point = self._rng.choice(entry_points)

        # Mark entry node as compromised
        self.graph.get_node(entry_point).is_compromised = True
        self._compromised = {entry_point}
        return entry_point

    def step(self, action_node_id: str) -> Tuple[float, bool]:
        """
        Attempt to compromise action_node_id.

        Returns
        -------
        (reward, done)
        """
        if self._done:
            return 0.0, True

        self._step_count += 1
        reward = -0.1  # step penalty

        target = self.graph.get_node(action_node_id)
        attempts = self._attempts_by_target.get(action_node_id, 0)

        if attempts >= self.max_attempts_per_target:
            reward += -0.45
            done = self._step_count >= self.max_steps
            self._done = done
            return reward, done

        # Check validity: node must be reachable and not already compromised
        reachable = self.graph.reachable_from(list(self._compromised))
        if (
            action_node_id not in reachable
            or action_node_id in self._compromised
            or target.is_isolated
            or target.is_patched
        ):
            reward += -0.5  # invalid action penalty
            done = self._step_count >= self.max_steps
            self._done = done
            return reward, done

        # Stochastic compromise attempt with edge + vector constraints and retry decay.
        self._attempts_by_target[action_node_id] = attempts + 1

        p_success = self._best_compromise_probability(action_node_id, attempts)
        if self._rng.random() < p_success:
            target.is_compromised = True
            self._compromised.add(action_node_id)
            reward += 10.0 if target.is_critical_asset else 1.0

        done = (
            self._step_count >= self.max_steps
            or (target.is_critical_asset and target.is_compromised)
        )
        self._done = done
        return reward, done

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    @property
    def compromised(self) -> List[str]:
        return list(self._compromised)

    @property
    def reachable_targets(self) -> List[str]:
        """Nodes reachable from current compromised set, not yet compromised."""
        reachable = set(self.graph.reachable_from(list(self._compromised)))
        return [n for n in reachable if n not in self._compromised]

    # ------------------------------------------------------------------
    # Batch simulation (for data generation + patch optimizer)
    # ------------------------------------------------------------------

    def run_episode(
        self,
        entry_point: Optional[str] = None,
        target_node: Optional[str] = None,
    ) -> Episode:
        """
        Run a single complete episode with random action selection.
        Returns a detailed Episode record.
        """
        ep_entry = self.reset(entry_point)

        # Default target: first critical asset
        if target_node is None:
            critical = self.graph.critical_assets
            target_node = critical[0] if critical else self.graph.node_ids[-1]

        episode = Episode(entry_point=ep_entry, target_node=target_node)
        step_idx = 0

        while not self._done:
            candidates = self.reachable_targets
            if not candidates:
                break

            # Random action from reachable set
            action = self._rng.choice(candidates)
            before = list(self._compromised)
            reward, done = self.step(action)
            after = list(self._compromised)

            newly = [n for n in after if n not in before]
            success = len(newly) > 0

            transition = Transition(
                step=step_idx,
                action_node_id=action,
                attacker_reachable=candidates,
                success=success,
                reward=reward,
                newly_compromised=newly,
                compromised_set_before=before,
                compromised_set_after=after,
                done=done,
            )
            episode.transitions.append(transition)
            episode.total_reward += reward
            step_idx += 1

        episode.total_steps = step_idx
        episode.reached_target = (
            target_node in self._compromised
            and self.graph.get_node(target_node).is_critical_asset
        )
        return episode

    def run_batch(
        self,
        n_episodes: int,
        entry_point: Optional[str] = None,
        target_node: Optional[str] = None,
    ) -> Dict:
        """
        Run n_episodes simulations and return aggregate statistics.

        Returns
        -------
        dict with keys:
            n_episodes, success_count, success_rate,
            mean_steps, mean_reward, episodes (list of Episode)
        """
        episodes = []
        for _ in range(n_episodes):
            ep = self.run_episode(entry_point, target_node)
            episodes.append(ep)

        success_count = sum(1 for e in episodes if e.success)
        return {
            "n_episodes": n_episodes,
            "success_count": success_count,
            "success_rate": success_count / n_episodes,
            "mean_steps": sum(e.total_steps for e in episodes) / n_episodes,
            "mean_reward": sum(e.total_reward for e in episodes) / n_episodes,
            "episodes": episodes,
        }
