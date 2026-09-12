"""
topology_loader.py — Loads JSON topology files into NetworkGraph instances.
Validates against the topology schema and constructs Node/Edge dataclasses.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Union

from src.graph.network_graph import NetworkGraph, Node, Edge


def load_topology(path: Union[str, Path]) -> NetworkGraph:
    """
    Load a topology JSON file and return a populated NetworkGraph.

    Parameters
    ----------
    path : str or Path
        Path to a topology JSON (matching configs/topology_schema.json).

    Returns
    -------
    NetworkGraph
        Populated graph with Node and Edge objects (no CVEs yet —
        call cve_tagger.tag_graph() next).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Topology file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    graph = NetworkGraph()

    # ----------------------------------------------------------------
    # Build nodes
    # ----------------------------------------------------------------
    for nd in data["nodes"]:
        node = Node(
            node_id=nd["node_id"],
            node_type=nd["node_type"],
            software=nd["software"],
            version=nd["version"],
            is_critical_asset=nd.get("is_critical_asset", False),
            is_entry_point=nd.get("is_entry_point", False),
            description=nd.get("description", ""),
        )
        graph.add_node(node)

    # ----------------------------------------------------------------
    # Build edges
    # ----------------------------------------------------------------
    for ed in data["edges"]:
        edge = Edge(
            source=ed["source"],
            target=ed["target"],
            connection_type=ed["connection_type"],
            has_firewall=ed.get("has_firewall", False),
            permission_level=ed.get("permission_level", "read"),
        )
        # Validate both endpoints exist
        if ed["source"] not in graph.node_ids:
            raise ValueError(f"Edge source '{ed['source']}' not in node list")
        if ed["target"] not in graph.node_ids:
            raise ValueError(f"Edge target '{ed['target']}' not in node list")
        graph.add_edge(edge)

    return graph


def load_all_topologies(topologies_dir: Union[str, Path]) -> dict:
    """
    Load all JSON topology files in a directory.

    Returns
    -------
    dict
        {topology_name: NetworkGraph}
    """
    topologies_dir = Path(topologies_dir)
    result = {}
    for json_file in sorted(topologies_dir.glob("*.json")):
        try:
            graph = load_topology(json_file)
            result[json_file.stem] = graph
        except Exception as e:
            print(f"[WARNING] Failed to load {json_file.name}: {e}")
    return result
