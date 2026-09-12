"""
cve_tagger.py — Attaches CVE records to network nodes based on software/version matching.
Computes per-node risk scores after tagging.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Union, List

from src.graph.network_graph import NetworkGraph, CVE


def load_cve_database(path: Union[str, Path]) -> List[CVE]:
    """Load the CVE JSON dataset into a list of CVE dataclass instances."""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    cves = []
    for entry in raw["cves"]:
        cves.append(CVE(
            cve_id=entry["cve_id"],
            software=entry["software"],
            version=entry["version"],
            cvss_score=float(entry["cvss_score"]),
            attack_vector=entry["attack_vector"],
            description=entry.get("description", ""),
        ))
    return cves


def tag_graph(
    graph: NetworkGraph,
    cve_database: List[CVE],
    include_local_vulns: bool = True,
) -> NetworkGraph:
    """
    Match CVEs to each node by (software, version) and attach them in-place.

    Parameters
    ----------
    graph : NetworkGraph
        The graph to tag (modified in-place).
    cve_database : list of CVE
        All known CVEs loaded from cve_dataset.json.
    include_local_vulns : bool
        If False, skip CVEs with attack_vector == "local" (network-only sim).

    Returns
    -------
    NetworkGraph
        Same graph reference, now with CVEs attached to nodes.
    """
    # Build lookup: (software.lower(), version) -> [CVE]
    lookup: dict = {}
    for cve in cve_database:
        key = (cve.software.lower(), cve.version)
        lookup.setdefault(key, []).append(cve)

    for node in graph.nodes:
        key = (node.software.lower(), node.version)
        matches = lookup.get(key, [])

        if not include_local_vulns:
            matches = [c for c in matches if c.attack_vector != "local"]

        node.vulnerabilities = list(matches)

    return graph


def tag_graph_from_file(
    graph: NetworkGraph,
    cve_path: Union[str, Path],
    include_local_vulns: bool = True,
) -> NetworkGraph:
    """Convenience wrapper: load CVE file then tag graph."""
    cve_db = load_cve_database(cve_path)
    return tag_graph(graph, cve_db, include_local_vulns=include_local_vulns)


def get_vulnerability_summary(graph: NetworkGraph) -> dict:
    """Return a per-node vulnerability summary dict."""
    summary = {}
    for node in graph.nodes:
        summary[node.node_id] = {
            "num_cves": node.num_vulns,
            "max_cvss": node.max_cvss,
            "severity": node.vulnerabilities[0].severity_label if node.vulnerabilities else "NONE",
            "cve_ids": [v.cve_id for v in node.vulnerabilities],
        }
    return summary
