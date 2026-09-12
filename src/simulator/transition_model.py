"""
transition_model.py — Abstract base class for world model transition functions.
Provides two implementations: RuleBasedTransition and GNNTransition.
The RL environments program against this interface so the backend is swappable.
"""

from __future__ import annotations
import random
from abc import ABC, abstractmethod
from typing import Dict, Optional


class TransitionModel(ABC):
    """
    Abstract transition model: given the current graph state and an action
    (node to attack), predict whether each node gets compromised.
    """

    @abstractmethod
    def predict_next_state(
        self,
        graph,
        action_node_id: str,
        rng: Optional[random.Random] = None,
    ) -> Dict[str, float]:
        """
        Parameters
        ----------
        graph : NetworkGraph
            Current graph state.
        action_node_id : str
            The node the attacker is targeting.
        rng : random.Random or None
            For stochastic rule-based models.

        Returns
        -------
        dict {node_id: P(compromised)}
        """


class RuleBasedTransition(TransitionModel):
    """
    Transition using rule-based probability: P = max_cvss / 10.
    This is deterministic in probability but stochastic in outcome.
    """

    def predict_next_state(
        self,
        graph,
        action_node_id: str,
        rng: Optional[random.Random] = None,
    ) -> Dict[str, float]:
        rng = rng or random.Random()
        result = {}
        for node in graph.nodes:
            if node.is_compromised:
                result[node.node_id] = 1.0
            elif node.node_id == action_node_id:
                # Check reachability
                reachable = graph.reachable_from(
                    [n.node_id for n in graph.nodes if n.is_compromised]
                )
                if action_node_id in reachable:
                    p = node.compromise_probability
                    result[node.node_id] = p
                else:
                    result[node.node_id] = 0.0
            else:
                result[node.node_id] = 0.0
        return result


class GNNTransition(TransitionModel):
    """
    Transition using the trained GNN world model.
    Loaded lazily from a checkpoint path.
    """

    def __init__(self, model_path: str, device: str = "cuda"):
        self._model_path = model_path
        self._device = device
        self._model = None

    def _load_model(self):
        import torch
        from src.models.gnn_world_model import GNNWorldModel
        self._model = GNNWorldModel()
        state_dict = torch.load(self._model_path, map_location=self._device)
        self._model.load_state_dict(state_dict)
        self._model.to(self._device)
        self._model.eval()

    def predict_next_state(
        self,
        graph,
        action_node_id: str,
        rng: Optional[random.Random] = None,
    ) -> Dict[str, float]:
        import torch
        from src.graph.pyg_converter import to_pyg

        if self._model is None:
            self._load_model()

        data = to_pyg(graph, attacked_node_id=action_node_id)
        x = data.x.to(self._device)
        edge_index = data.edge_index.to(self._device)

        with torch.no_grad():
            probs = self._model(x, edge_index).squeeze(-1).cpu()

        return {nid: float(p) for nid, p in zip(data.node_ids, probs)}
