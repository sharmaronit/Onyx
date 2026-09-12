"""
network_graph.py — Core data structures for Onyx network representation.
Defines Node, Edge, CVE dataclasses and the NetworkGraph wrapper around NetworkX.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import copy
import networkx as nx


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CVE:
    """A single CVE vulnerability entry."""
    cve_id: str
    software: str
    version: str
    cvss_score: float           # 0.0 – 10.0
    attack_vector: str          # "network" | "adjacent" | "local"
    description: str = ""

    @property
    def severity_label(self) -> str:
        if self.cvss_score >= 9.0:
            return "CRITICAL"
        elif self.cvss_score >= 7.0:
            return "HIGH"
        elif self.cvss_score >= 4.0:
            return "MEDIUM"
        else:
            return "LOW"


@dataclass
class Node:
    """A network asset (device, server, database, cloud resource)."""
    node_id: str
    node_type: str              # "server"|"workstation"|"router"|"firewall"|"database"|"cloud"
    software: str
    version: str
    is_critical_asset: bool = False
    is_entry_point: bool = False
    description: str = ""

    # Runtime state (modified during simulation)
    vulnerabilities: List[CVE] = field(default_factory=list)
    is_compromised: bool = False
    is_patched: bool = False    # Blue agent effect: removes all vulns
    is_isolated: bool = False   # Blue agent effect: removes all edges

    @property
    def max_cvss(self) -> float:
        """Highest CVSS score among attached CVEs (0 if none)."""
        if not self.vulnerabilities:
            return 0.0
        return max(v.cvss_score for v in self.vulnerabilities)

    @property
    def num_vulns(self) -> int:
        return len(self.vulnerabilities)

    @property
    def compromise_probability(self) -> float:
        """Rule-based: probability this node yields to an attack attempt."""
        if self.is_patched or self.is_isolated:
            return 0.0

        base_probability = self.max_cvss / 10.0
        if not self.vulnerabilities:
            return 0.0

        attack_vector_multiplier = 0.35
        for vulnerability in self.vulnerabilities:
            if vulnerability.attack_vector == "network":
                attack_vector_multiplier = max(attack_vector_multiplier, 1.0)
            elif vulnerability.attack_vector == "adjacent":
                attack_vector_multiplier = max(attack_vector_multiplier, 0.7)
            else:
                attack_vector_multiplier = max(attack_vector_multiplier, 0.45)

        return min(0.95, base_probability * attack_vector_multiplier)

    def reset(self):
        """Reset runtime state for a new episode."""
        self.is_compromised = False
        self.is_patched = False
        self.is_isolated = False

    def __repr__(self) -> str:
        status = "COMPROMISED" if self.is_compromised else "clean"
        return f"Node({self.node_id}, {self.node_type}, cvss={self.max_cvss:.1f}, {status})"


@dataclass
class Edge:
    """A directional network connection between two nodes."""
    source: str
    target: str
    connection_type: str        # "ssh"|"http"|"sql"|"rdp"|"ftp"|"vpn"
    has_firewall: bool = False
    permission_level: str = "read"  # "read" | "write" | "admin"

    @property
    def permission_value(self) -> float:
        """Normalised [0,1] permission level."""
        return {"read": 0.33, "write": 0.66, "admin": 1.0}.get(self.permission_level, 0.33)

    def __repr__(self) -> str:
        fw = " [FW]" if self.has_firewall else ""
        return f"Edge({self.source} -[{self.connection_type}/{self.permission_level}]-> {self.target}{fw})"


# ---------------------------------------------------------------------------
# NetworkGraph — thin wrapper around NetworkX DiGraph
# ---------------------------------------------------------------------------

NODE_TYPES = ["server", "workstation", "router", "firewall", "database", "cloud"]
CONNECTION_TYPES = ["ssh", "http", "sql", "rdp", "ftp", "vpn"]


class NetworkGraph:
    """
    Wraps a NetworkX DiGraph.  Each node attribute holds a ``Node`` object
    under the key ``"data"``, and each edge attribute holds an ``Edge`` object
    under the key ``"data"``.
    """

    def __init__(self):
        self.G: nx.DiGraph = nx.DiGraph()

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    def add_node(self, node: Node) -> None:
        self.G.add_node(node.node_id, data=node)

    def add_edge(self, edge: Edge) -> None:
        self.G.add_edge(edge.source, edge.target, data=edge)

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    @property
    def nodes(self) -> List[Node]:
        return [d["data"] for _, d in self.G.nodes(data=True)]

    @property
    def node_ids(self) -> List[str]:
        return list(self.G.nodes())

    @property
    def edges(self) -> List[Edge]:
        return [d["data"] for _, _, d in self.G.edges(data=True)]

    def get_node(self, node_id: str) -> Node:
        return self.G.nodes[node_id]["data"]

    def get_edge(self, source: str, target: str) -> Optional[Edge]:
        if self.G.has_edge(source, target):
            return self.G[source][target]["data"]
        return None

    @property
    def entry_points(self) -> List[str]:
        return [n.node_id for n in self.nodes if n.is_entry_point]

    @property
    def critical_assets(self) -> List[str]:
        return [n.node_id for n in self.nodes if n.is_critical_asset]

    @property
    def num_nodes(self) -> int:
        return self.G.number_of_nodes()

    @property
    def num_edges(self) -> int:
        return self.G.number_of_edges()

    # ------------------------------------------------------------------
    # Reachability
    # ------------------------------------------------------------------

    def reachable_from(self, source_ids: List[str]) -> List[str]:
        """All nodes reachable (one hop) from any node in source_ids, excluding isolated nodes."""
        reachable = set()
        for src in source_ids:
            node = self.get_node(src)
            if node.is_isolated:
                continue
            for nbr in self.G.successors(src):
                nbr_node = self.get_node(nbr)
                if not nbr_node.is_isolated:
                    reachable.add(nbr)
        return list(reachable)

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def reset_runtime_state(self) -> None:
        """Reset all nodes to clean/uncompromised state."""
        for node in self.nodes:
            node.reset()

    def deep_copy(self) -> "NetworkGraph":
        """Return a fully independent copy (for patch simulations)."""
        new_g = NetworkGraph()
        new_g.G = copy.deepcopy(self.G)
        return new_g

    # ------------------------------------------------------------------
    # Degree centrality cache
    # ------------------------------------------------------------------

    def degree_centrality(self) -> dict:
        return nx.degree_centrality(self.G)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> str:
        lines = [
            f"NetworkGraph: {self.num_nodes} nodes, {self.num_edges} edges",
            f"  Entry points:    {self.entry_points}",
            f"  Critical assets: {self.critical_assets}",
        ]
        vulned = [n for n in self.nodes if n.num_vulns > 0]
        lines.append(f"  Nodes with CVEs: {len(vulned)}/{self.num_nodes}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"NetworkGraph(nodes={self.num_nodes}, edges={self.num_edges})"
