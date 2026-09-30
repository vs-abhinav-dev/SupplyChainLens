from dataclasses import dataclass
from typing import Optional


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
