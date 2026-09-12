"""
gnn_world_model.py — GraphSAGE-based world model for Onyx.

Predicts P(each node becomes compromised) given the current graph state
and the node being attacked (encoded as 12th feature on target node).

Architecture:
    3 × SAGEConv layers with BatchNorm and dropout
    Final sigmoid output → probability per node ∈ [0, 1]

Also defines GATWorldModel (drop-in alternative using 4-head GAT).

Training target: binary vector of is_compromised flags for state t+1.
Loss: Binary Cross-Entropy per node.
"""

from __future__ import annotations
import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    from torch_geometric.nn import SAGEConv, GATConv, GCNConv
    from torch_geometric.nn import BatchNorm as PyGBatchNorm
    HAS_PYG = True
except ImportError:
    HAS_PYG = False

NODE_FEAT_DIM_WITH_ACTION = 12   # 11 node features + 1 is_being_attacked flag


# ---------------------------------------------------------------------------
# GraphSAGE World Model (primary)
# ---------------------------------------------------------------------------

class GNNWorldModel(nn.Module):
    """
    GraphSAGE-based transition function.

    Input:  graph state with is_being_attacked flag  (node feat dim = 12)
    Output: P(each node is compromised)              shape [N, 1]
    """

    def __init__(
        self,
        in_channels: int = NODE_FEAT_DIM_WITH_ACTION,
        hidden_channels: int = 64,
        num_layers: int = 3,
        dropout: float = 0.1,
    ):
        super().__init__()
        if not HAS_PYG:
            raise ImportError("torch_geometric not installed.")

        self.dropout = dropout
        self.convs = nn.ModuleList()
        self.bns = nn.ModuleList()

        # Input → hidden
        self.convs.append(SAGEConv(in_channels, hidden_channels))
        self.bns.append(PyGBatchNorm(hidden_channels))

        # Hidden → hidden (num_layers - 2 intermediate layers)
        for _ in range(num_layers - 2):
            self.convs.append(SAGEConv(hidden_channels, hidden_channels))
            self.bns.append(PyGBatchNorm(hidden_channels))

        # Hidden → 1 (output)
        self.convs.append(SAGEConv(hidden_channels, 1))

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        x : Tensor [N, 12]
        edge_index : Tensor [2, E]

        Returns
        -------
        Tensor [N, 1]  — P(compromised) per node
        """
        for i, (conv, bn) in enumerate(zip(self.convs[:-1], self.bns)):
            x = conv(x, edge_index)
            x = bn(x)
            x = F.relu(x)
            x = F.dropout(x, p=self.dropout, training=self.training)

        x = self.convs[-1](x, edge_index)
        return torch.sigmoid(x)   # [N, 1]

    def predict_proba(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
    ) -> torch.Tensor:
        """Inference wrapper — returns [N] float tensor."""
        with torch.no_grad():
            return self.forward(x, edge_index).squeeze(-1)


# ---------------------------------------------------------------------------
# GAT World Model (comparison / ablation)
# ---------------------------------------------------------------------------

class GATWorldModel(nn.Module):
    """
    GAT-based alternative. Same interface as GNNWorldModel.
    Uses 4 attention heads.
    """

    def __init__(
        self,
        in_channels: int = NODE_FEAT_DIM_WITH_ACTION,
        hidden_channels: int = 64,
        heads: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()
        if not HAS_PYG:
            raise ImportError("torch_geometric not installed.")

        self.dropout = dropout
        self.conv1 = GATConv(in_channels, hidden_channels // heads, heads=heads, concat=True, dropout=dropout)
        self.conv2 = GATConv(hidden_channels, hidden_channels // heads, heads=heads, concat=True, dropout=dropout)
        self.conv3 = GATConv(hidden_channels, 1, heads=1, concat=False, dropout=dropout)
        self.bn1 = PyGBatchNorm(hidden_channels)
        self.bn2 = PyGBatchNorm(hidden_channels)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        x = F.relu(self.bn1(self.conv1(x, edge_index)))
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = F.relu(self.bn2(self.conv2(x, edge_index)))
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = torch.sigmoid(self.conv3(x, edge_index))
        return x   # [N, 1]

    def predict_proba(self, x, edge_index):
        with torch.no_grad():
            return self.forward(x, edge_index).squeeze(-1)


# ---------------------------------------------------------------------------
# GCN World Model (comparison / ablation)
# ---------------------------------------------------------------------------

class GCNWorldModel(nn.Module):
    """Vanilla GCN baseline for ablation."""

    def __init__(
        self,
        in_channels: int = NODE_FEAT_DIM_WITH_ACTION,
        hidden_channels: int = 64,
        dropout: float = 0.1,
    ):
        super().__init__()
        if not HAS_PYG:
            raise ImportError("torch_geometric not installed.")

        self.dropout = dropout
        self.conv1 = GCNConv(in_channels, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, hidden_channels)
        self.conv3 = GCNConv(hidden_channels, 1)
        self.bn1 = PyGBatchNorm(hidden_channels)
        self.bn2 = PyGBatchNorm(hidden_channels)

    def forward(self, x, edge_index):
        x = F.relu(self.bn1(self.conv1(x, edge_index)))
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = F.relu(self.bn2(self.conv2(x, edge_index)))
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = torch.sigmoid(self.conv3(x, edge_index))
        return x

    def predict_proba(self, x, edge_index):
        with torch.no_grad():
            return self.forward(x, edge_index).squeeze(-1)
