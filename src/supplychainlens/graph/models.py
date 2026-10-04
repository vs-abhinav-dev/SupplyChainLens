from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Node:
    """Represents an npm package version vertex in the dependency graph."""
    node_id: str
    package_id: str
    name: str
    version: str
    published_at: Optional[str] = None


@dataclass(frozen=True)
class Edge:
    """Represents a resolved dependency edge between two package version vertices."""
    source_node_id: str
    target_node_id: str
    version_constraint: str
    dependency_type: str = "dependencies"


@dataclass
class SubgraphView:
    """
    Frontend-friendly projection of a localized subgraph for expand-on-demand visualization.
    """
    root_id: str
    depth: int
    direction: str
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0
    truncated: bool = False


@dataclass
class PathResult:
    """
    Result of a path search between two vertices.
    """
    source_node_id: str
    target_node_id: str
    path: List[str]
    length: int
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)


@dataclass
class PackageSummary:
    """
    Summary metadata for a package across all its published versions.
    """
    package_id: str
    name: str
    total_versions: int
    latest_version: Optional[str]
    latest_node_id: Optional[str]
    versions: List[str] = field(default_factory=list)
    node_ids: List[str] = field(default_factory=list)

