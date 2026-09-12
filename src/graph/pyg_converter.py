"""
pyg_converter.py — Converts NetworkGraph → torch_geometric.data.Data.

Node feature vector (11 dims):
  [0]   is_compromised
  [1]   cvss_score_norm        (max_cvss / 10)
  [2]   num_vulns_norm         (num_vulns / MAX_VULNS_CLIP)
  [3-6] node_type_onehot       [server, workstation, router, firewall]
          database and cloud → server bucket (index 0)
  [7]   is_critical_asset
  [8]   is_patched
  [9]   is_isolated
  [10]  degree_centrality_norm

When encoding an attack action, a 12th feature is added:
  [11]  is_being_attacked  (set to 1 on the target node only)

Edge feature vector (5 dims):
  [0-2] connection_type_onehot  [ssh+rdp+vpn, http+ftp, sql]
  [3]   has_firewall
  [4]   permission_level_norm   (read=0.33, write=0.66, admin=1.0)
"""

from __future__ import annotations
from typing import Optional, List
import torch
import numpy as np

try:
    from torch_geometric.data import Data
    HAS_PYG = True
except ImportError:
    HAS_PYG = False

from src.graph.network_graph import NetworkGraph, NODE_TYPES, CONNECTION_TYPES

# -------------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------------
MAX_VULNS_CLIP = 5.0   # normalise num_vulns; values above 5 are clipped to 1

# 4 one-hot categories (database/cloud treated as server)
_NODE_TYPE_ORDER = ["server", "workstation", "router", "firewall"]

# 3 connection categories
_CONN_SSH_GROUP = {"ssh", "rdp", "vpn"}
_CONN_HTTP_GROUP = {"http", "ftp"}
_CONN_SQL_GROUP = {"sql"}


def _node_type_onehot(node_type: str) -> List[float]:
    type_map = {t: i for i, t in enumerate(_NODE_TYPE_ORDER)}
    idx = type_map.get(node_type, 0)  # unknown / database / cloud → server bucket
    oh = [0.0, 0.0, 0.0, 0.0]
    oh[idx] = 1.0
    return oh


def _edge_type_onehot(connection_type: str) -> List[float]:
    ct = connection_type.lower()
    if ct in _CONN_SSH_GROUP:
        return [1.0, 0.0, 0.0]
    elif ct in _CONN_HTTP_GROUP:
        return [0.0, 1.0, 0.0]
    elif ct in _CONN_SQL_GROUP:
        return [0.0, 0.0, 1.0]
    else:
        return [0.0, 0.0, 0.0]


# -------------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------------

def to_pyg(
    graph: NetworkGraph,
    attacked_node_id: Optional[str] = None,
) -> "Data":
    """
    Convert a NetworkGraph to a PyG Data object.

    Parameters
    ----------
    graph : NetworkGraph
        Tagged and (optionally) partially compromised graph.
    attacked_node_id : str or None
        If provided, the 12th feature on that node is set to 1.0.
        Used during GNN world-model forward pass.

    Returns
    -------
    torch_geometric.data.Data
        x         : [N, 11] or [N, 12] float tensor
        edge_index: [2, E] long tensor (COO format)
        edge_attr : [E, 5] float tensor
        node_ids  : list[str] — ordered node id list (for decoding predictions)
    """
    if not HAS_PYG:
        raise ImportError("torch_geometric is not installed. Run: pip install torch-geometric")

    node_ids = graph.node_ids
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    degree_centrality = graph.degree_centrality()

    # ---- Node features ----------------------------------------
    node_feats = []
    for nid in node_ids:
        node = graph.get_node(nid)
        feat = [
            float(node.is_compromised),                   # [0]
            node.max_cvss / 10.0,                          # [1]
            min(node.num_vulns / MAX_VULNS_CLIP, 1.0),    # [2]
        ]
        feat.extend(_node_type_onehot(node.node_type))    # [3-6]
        feat.append(float(node.is_critical_asset))         # [7]
        feat.append(float(node.is_patched))                # [8]
        feat.append(float(node.is_isolated))               # [9]
        feat.append(degree_centrality.get(nid, 0.0))       # [10]

        if attacked_node_id is not None:
            feat.append(1.0 if nid == attacked_node_id else 0.0)  # [11]

        node_feats.append(feat)

    x = torch.tensor(node_feats, dtype=torch.float)

    # ---- Edge index + attributes ------------------------------
    src_list, dst_list, edge_feat_list = [], [], []
    for src_id, dst_id, edata in graph.G.edges(data=True):
        edge = edata["data"]
        src_idx = id_to_idx[src_id]
        dst_idx = id_to_idx[dst_id]

        # Skip isolated nodes
        if graph.get_node(src_id).is_isolated or graph.get_node(dst_id).is_isolated:
            continue

        src_list.append(src_idx)
        dst_list.append(dst_idx)

        efeat = _edge_type_onehot(edge.connection_type)       # [0-2]
        efeat.append(float(edge.has_firewall))                  # [3]
        efeat.append(edge.permission_value)                     # [4]
        edge_feat_list.append(efeat)

    if src_list:
        edge_index = torch.tensor([src_list, dst_list], dtype=torch.long)
        edge_attr = torch.tensor(edge_feat_list, dtype=torch.float)
    else:
        edge_index = torch.zeros((2, 0), dtype=torch.long)
        edge_attr = torch.zeros((0, 5), dtype=torch.float)

    data = Data(x=x, edge_index=edge_index, edge_attr=edge_attr)
    data.node_ids = node_ids          # keep for decoding
    data.num_nodes = len(node_ids)
    return data


def get_compromise_vector(graph: NetworkGraph) -> torch.Tensor:
    """
    Return a [N] float tensor of is_compromised flags in node_id order.
    Used as the training target for the GNN world model.
    """
    return torch.tensor(
        [float(graph.get_node(nid).is_compromised) for nid in graph.node_ids],
        dtype=torch.float,
    )
