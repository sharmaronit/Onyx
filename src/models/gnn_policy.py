"""
gnn_policy.py — Custom SB3 feature extractor using a Graph Attention Network.

Replaces SB3's default MLP observation processing with a GNN that processes
the padded flat observation vector as a graph. Used in Day 13 to replace
the MlpPolicy backbone with a graph-aware one.

Usage with MaskablePPO:
    policy_kwargs = dict(
        features_extractor_class=GNNFeatureExtractor,
        features_extractor_kwargs=dict(features_dim=128, topology_path="...", cve_path="..."),
    )
    model = MaskablePPO("MlpPolicy", env, policy_kwargs=policy_kwargs)
"""

from __future__ import annotations
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional

try:
    from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
    HAS_SB3 = True
except ImportError:
    HAS_SB3 = False

try:
    from torch_geometric.nn import GATConv
    from torch_geometric.nn import BatchNorm as PyGBatchNorm
    from torch_geometric.utils import from_networkx
    HAS_PYG = True
except ImportError:
    HAS_PYG = False

from src.envs.attacker_env import MAX_NODES, NODE_FEAT_DIM


class GNNFeatureExtractor(BaseFeaturesExtractor if HAS_SB3 else nn.Module):
    """
    GNN-based feature extractor that replaces SB3's default MLP.
    Unpacks the padded flat observation, runs 2 GAT layers, applies
    global mean pooling, and outputs a fixed-size latent vector.

    Parameters
    ----------
    observation_space : gym.Space
    features_dim : int
        Output dimension of the latent representation.
    topology_path : str
        Used to rebuild edge_index at init time (topology is static).
    cve_path : str
    """

    def __init__(
        self,
        observation_space,
        features_dim: int = 128,
        topology_path: Optional[str] = None,
        cve_path: Optional[str] = None,
    ):
        if not HAS_SB3:
            raise ImportError("stable_baselines3 not installed.")
        if not HAS_PYG:
            raise ImportError("torch_geometric not installed.")

        super().__init__(observation_space, features_dim)

        self.features_dim = features_dim

        # GAT layers
        self.gat1 = GATConv(NODE_FEAT_DIM, 64, heads=4, concat=False)
        self.gat2 = GATConv(64, 32, heads=4, concat=False)
        self.bn1 = PyGBatchNorm(64)
        self.bn2 = PyGBatchNorm(32)
        self.fc = nn.Linear(32, features_dim)

        # Pre-build edge_index from topology (static for one env)
        self._edge_index: Optional[torch.Tensor] = None
        self._n_real: Optional[int] = None
        if topology_path and cve_path:
            self._build_edge_index(topology_path, cve_path)

    def _build_edge_index(self, topology_path: str, cve_path: str):
        """Pre-compute edge_index from topology (called once at init)."""
        from src.graph.topology_loader import load_topology
        from src.graph.cve_tagger import load_cve_database, tag_graph

        graph = load_topology(topology_path)
        cve_db = load_cve_database(cve_path)
        tag_graph(graph, cve_db)

        node_order = sorted(graph.node_ids)
        self._n_real = len(node_order)
        id_to_idx = {nid: i for i, nid in enumerate(node_order)}

        src_list, dst_list = [], []
        for src_id, dst_id in graph.G.edges():
            if src_id in id_to_idx and dst_id in id_to_idx:
                src_list.append(id_to_idx[src_id])
                dst_list.append(id_to_idx[dst_id])

        if src_list:
            self._edge_index = torch.tensor([src_list, dst_list], dtype=torch.long)
        else:
            self._edge_index = torch.zeros((2, 0), dtype=torch.long)

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        observations : Tensor [B, MAX_NODES * NODE_FEAT_DIM]

        Returns
        -------
        Tensor [B, features_dim]
        """
        B = observations.shape[0]
        n = self._n_real or MAX_NODES

        # Reshape: [B, MAX_NODES, 11] → only keep real nodes
        x_full = observations.view(B, MAX_NODES, NODE_FEAT_DIM)
        x = x_full[:, :n, :]   # [B, n, 11]

        # Process each graph in the batch via shared GNN weights
        # (simple loop; for large batches use PyG batching)
        outputs = []
        device = observations.device
        edge_index = self._edge_index.to(device) if self._edge_index is not None else \
            torch.zeros((2, 0), dtype=torch.long, device=device)

        for b in range(B):
            xi = x[b]   # [n, 11]
            xi = F.relu(self.bn1(self.gat1(xi, edge_index)))
            xi = F.relu(self.bn2(self.gat2(xi, edge_index)))
            xi = xi.mean(dim=0)   # global mean pool → [32]
            outputs.append(xi)

        out = torch.stack(outputs, dim=0)   # [B, 32]
        return self.fc(out)                  # [B, features_dim]
