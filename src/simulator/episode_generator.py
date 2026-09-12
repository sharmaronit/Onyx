"""
episode_generator.py — Batch episode generation for GNN world model training.

Generates (state_t, action, state_{t+1}) transition tuples from rule-based
simulator runs across multiple topology variants, storing them in HDF5.
"""

from __future__ import annotations
import json
import random
import copy
import numpy as np
import h5py
from pathlib import Path
from typing import List, Optional, Tuple
from tqdm import tqdm

from src.graph.network_graph import NetworkGraph
from src.graph.topology_loader import load_topology
from src.graph.cve_tagger import load_cve_database, tag_graph
from src.simulator.rule_based import AttackSimulator


# ---------------------------------------------------------------------------
# State snapshot helpers
# ---------------------------------------------------------------------------

def _node_ids_sorted(graph: NetworkGraph) -> List[str]:
    return sorted(graph.node_ids)


def _state_snapshot(graph: NetworkGraph, node_order: List[str]) -> np.ndarray:
    """
    Extract a (N,) float32 vector of is_compromised flags, in node_order.
    Used as GNN training target: predict which nodes are compromised after action.
    """
    return np.array(
        [float(graph.get_node(nid).is_compromised) for nid in node_order],
        dtype=np.float32,
    )


def _node_features(graph: NetworkGraph, node_order: List[str]) -> np.ndarray:
    """
    Extract (N, 11) float32 feature matrix.
    Keep in sync with pyg_converter._to_pyg node feature ordering.
    """
    from src.graph.network_graph import NODE_TYPES
    dc = graph.degree_centrality()
    _TYPE_ORDER = ["server", "workstation", "router", "firewall"]
    _MAX_VULNS = 5.0

    rows = []
    for nid in node_order:
        n = graph.get_node(nid)
        # one-hot type
        type_idx = _TYPE_ORDER.index(n.node_type) if n.node_type in _TYPE_ORDER else 0
        oh = [0.0] * 4
        oh[type_idx] = 1.0

        row = [
            float(n.is_compromised),
            n.max_cvss / 10.0,
            min(n.num_vulns / _MAX_VULNS, 1.0),
        ] + oh + [
            float(n.is_critical_asset),
            float(n.is_patched),
            float(n.is_isolated),
            dc.get(nid, 0.0),
        ]
        rows.append(row)
    return np.array(rows, dtype=np.float32)   # (N, 11)


def _action_vector(graph: NetworkGraph, node_order: List[str], action_nid: str) -> np.ndarray:
    """(N,) float32 — 1.0 at action node, 0 elsewhere."""
    return np.array(
        [1.0 if nid == action_nid else 0.0 for nid in node_order],
        dtype=np.float32,
    )


# ---------------------------------------------------------------------------
# Single-topology generator
# ---------------------------------------------------------------------------

def _edge_index(graph: NetworkGraph, node_order: List[str]) -> np.ndarray:
    """
    Build edge_index (2, E) from the graph's edges in the given node_order.
    Returns np.int32 array.
    """
    nid_to_idx = {nid: i for i, nid in enumerate(node_order)}
    sources = []
    targets = []
    for edge in graph.edges:
        if edge.source in nid_to_idx and edge.target in nid_to_idx:
            sources.append(nid_to_idx[edge.source])
            targets.append(nid_to_idx[edge.target])
    if not sources:
        return np.zeros((2, 0), dtype=np.int32)
    return np.array([sources, targets], dtype=np.int32)


def generate_episodes_from_graph(
    graph: NetworkGraph,
    n_episodes: int,
    max_steps: int = 50,
    seed: Optional[int] = None,
) -> List[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    """
    Run n_episodes on a single graph and extract all transitions.

    Returns
    -------
    list of (node_feats_t, action_vec, node_feats_t1, compromise_t1, edge_idx)
        node_feats_t   : (N, 11)  — state before action
        action_vec     : (N,)     — one-hot action
        node_feats_t1  : (N, 11)  — state after action
        compromise_t1  : (N,)     — is_compromised after action (GNN target)
        edge_idx       : (2, E)   — edge index for this graph
    """
    sim = AttackSimulator(graph, max_steps=max_steps, seed=seed)
    node_order = _node_ids_sorted(graph)
    edge_idx = _edge_index(graph, node_order)
    transitions = []

    for ep_idx in range(n_episodes):
        ep_seed = seed + ep_idx if seed is not None else None
        if ep_seed is not None:
            sim._rng = random.Random(ep_seed)

        sim.reset()
        done = False
        step = 0

        while not done and step < max_steps:
            candidates = sim.reachable_targets
            if not candidates:
                break

            # Snapshot before
            feats_t = _node_features(graph, node_order)

            # Random action
            action_nid = sim._rng.choice(candidates)
            action_vec = _action_vector(graph, node_order, action_nid)

            # Take step
            _, done = sim.step(action_nid)

            # Snapshot after
            feats_t1 = _node_features(graph, node_order)
            comp_t1 = _state_snapshot(graph, node_order)

            transitions.append((feats_t, action_vec, feats_t1, comp_t1, edge_idx))
            step += 1

    return transitions


# ---------------------------------------------------------------------------
# Multi-topology HDF5 generator
# ---------------------------------------------------------------------------

def generate_dataset(
    topologies_dir: str,
    cve_path: str,
    output_path: str,
    episodes_per_topology: int = 500,
    max_steps: int = 50,
    seed: int = 42,
    verbose: bool = True,
) -> dict:
    """
    Generate training data across all topologies in topologies_dir.
    Saves transitions to HDF5 at output_path.

    HDF5 structure:
        /node_feats_t   : (total_transitions, max_N, 11)
        /action_vec     : (total_transitions, max_N)
        /node_feats_t1  : (total_transitions, max_N, 11)
        /compromise_t1  : (total_transitions, max_N)
        /n_nodes        : (total_transitions,)   — actual N for each transition

    All arrays are padded with zeros to max_N = 50.

    Returns
    -------
    dict with generation statistics
    """
    from src.graph.topology_loader import load_all_topologies

    MAX_N = 50  # from config
    topologies = load_all_topologies(topologies_dir)
    cve_db = load_cve_database(cve_path)

    if verbose:
        print(f"Loaded {len(topologies)} topologies from {topologies_dir}")
        print(f"Loaded {len(cve_db)} CVEs from {cve_path}")
        print(f"Generating {episodes_per_topology} episodes per topology...")

    all_transitions = []
    rng = random.Random(seed)

    for topo_name, base_graph in (tqdm(topologies.items(), desc="Topologies") if verbose else topologies.items()):
        # Also generate synthetic topology variants for generalisation
        graphs_to_use = [base_graph]
        for variant_seed in range(min(5, max(1, 100 // len(topologies)))):
            variant_graph = _make_variant(base_graph, cve_db, rng=rng)
            graphs_to_use.append(variant_graph)

        for g in graphs_to_use:
            tag_graph(g, cve_db)
            ep_per_g = episodes_per_topology // len(graphs_to_use)
            transitions = generate_episodes_from_graph(
                g,
                n_episodes=max(1, ep_per_g),
                max_steps=max_steps,
                seed=rng.randint(0, 10**6),
            )
            all_transitions.extend(transitions)

    if verbose:
        print(f"Total transitions collected: {len(all_transitions)}")

    # ----------------------------------------------------------------
    # Write to HDF5
    # ----------------------------------------------------------------
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    n_total = len(all_transitions)
    # Determine max edges across all transitions for padding
    MAX_EDGES = max(t[4].shape[1] for t in all_transitions) if all_transitions else 0
    with h5py.File(output_path, "w") as f:
        f.create_dataset("node_feats_t",  shape=(n_total, MAX_N, 11), dtype=np.float32)
        f.create_dataset("action_vec",    shape=(n_total, MAX_N),     dtype=np.float32)
        f.create_dataset("node_feats_t1", shape=(n_total, MAX_N, 11), dtype=np.float32)
        f.create_dataset("compromise_t1", shape=(n_total, MAX_N),     dtype=np.float32)
        f.create_dataset("n_nodes",       shape=(n_total,),            dtype=np.int32)
        f.create_dataset("edge_index",    shape=(n_total, 2, MAX_EDGES), dtype=np.int32)
        f.create_dataset("n_edges",       shape=(n_total,),            dtype=np.int32)

        for i, (ft, av, ft1, ct1, ei) in enumerate(
            tqdm(all_transitions, desc="Writing HDF5") if verbose else all_transitions
        ):
            n = ft.shape[0]
            n_e = ei.shape[1]
            assert n <= MAX_N, f"Graph has {n} nodes > MAX_N={MAX_N}"

            f["node_feats_t"][i, :n, :]  = ft
            f["action_vec"][i, :n]        = av
            f["node_feats_t1"][i, :n, :]  = ft1
            f["compromise_t1"][i, :n]     = ct1
            f["n_nodes"][i]               = n
            f["edge_index"][i, :, :n_e]   = ei
            f["n_edges"][i]               = n_e

    stats = {
        "total_transitions": n_total,
        "num_topologies": len(topologies),
        "output_path": str(output_path),
    }
    if verbose:
        print(f"Dataset saved to {output_path} ({n_total:,} transitions)")
    return stats


# ---------------------------------------------------------------------------
# Topology variant generator
# ---------------------------------------------------------------------------

def _make_variant(base_graph: NetworkGraph, cve_db, rng: random.Random) -> NetworkGraph:
    """
    Create a shallow structural variant of base_graph for training diversity.
    Randomly adds/removes one edge and flips one firewall flag.
    """
    variant = base_graph.deep_copy()
    edges = variant.edges
    if edges and rng.random() < 0.5:
        # Flip a firewall flag on a random edge
        edge = rng.choice(edges)
        edge.has_firewall = not edge.has_firewall
    return variant


# ---------------------------------------------------------------------------
# HDF5 Dataset class (for PyTorch DataLoader)
# ---------------------------------------------------------------------------

class EpisodeDataset:
    """
    PyTorch-compatible dataset that reads from the HDF5 generated above.
    Yields (node_feats_t_with_action, compress_t1_masked) pairs.
    """

    def __init__(self, hdf5_path: str):
        import torch
        from torch.utils.data import Dataset

        class _HDF5Dataset(Dataset):
            def __init__(self_, path):
                self_.f = h5py.File(path, "r")
                self_.n = self_.f["n_nodes"].shape[0]
                self_.has_edges = "edge_index" in self_.f

            def __len__(self_):
                return self_.n

            def __getitem__(self_, idx):
                n = int(self_.f["n_nodes"][idx])
                ft  = torch.tensor(self_.f["node_feats_t"][idx, :n, :],  dtype=torch.float)
                av  = torch.tensor(self_.f["action_vec"][idx, :n],        dtype=torch.float)
                ct1 = torch.tensor(self_.f["compromise_t1"][idx, :n],     dtype=torch.float)
                # Concat action as 12th feature
                x = torch.cat([ft, av.unsqueeze(-1)], dim=-1)  # (n, 12)
                # Edge index
                if self_.has_edges:
                    n_e = int(self_.f["n_edges"][idx])
                    ei = torch.tensor(self_.f["edge_index"][idx, :, :n_e], dtype=torch.long)
                else:
                    ei = torch.zeros((2, 0), dtype=torch.long)
                return x, ct1, n, ei

            def __del__(self_):
                try:
                    self_.f.close()
                except Exception:
                    pass

        self.dataset = _HDF5Dataset(hdf5_path)

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, idx):
        return self.dataset[idx]

    def __call__(self):
        return self.dataset
