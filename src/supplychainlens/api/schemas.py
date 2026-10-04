from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GraphNodeSchema(BaseModel):
    """Clean node format projected for visualization libraries (Cytoscape/D3)."""
    id: str
    label: str
    name: str
    version: str
    package_id: str
    published_at: Optional[str] = None
    is_root: bool = False
    degree: int = 0
    in_degree: int = 0
    out_degree: int = 0


class GraphEdgeSchema(BaseModel):
    """Clean edge format projected for visualization libraries (Cytoscape/D3)."""
    source: str
    target: str
    version_constraint: str = ""
    dependency_type: str = "dependencies"


class SubgraphResponse(BaseModel):
    """Expand-on-demand localized subgraph response."""
    root_id: str
    depth: int
    direction: str
    nodes: List[GraphNodeSchema]
    edges: List[GraphEdgeSchema]
    total_nodes: int
    total_edges: int
    truncated: bool = False


class PackageSummaryResponse(BaseModel):
    """Package metadata and version enumeration."""
    package_id: str
    name: str
    ecosystem: str = "npm"
    total_versions: int
    latest_version: Optional[str] = None
    latest_node_id: Optional[str] = None
    versions: List[str] = Field(default_factory=list)
    node_ids: List[str] = Field(default_factory=list)


class PackageListResponse(BaseModel):
    """List of all available packages in the repository."""
    total: int
    packages: List[str]


class GraphStatsResponse(BaseModel):
    """High-level topology overview and counts."""
    backend: str
    node_count: int
    edge_count: int
    boundary_edge_count: int
    package_count: int


class PathResponse(BaseModel):
    """Shortest directed dependency path between two nodes."""
    source: str
    target: str
    found: bool
    length: int
    path: List[str]
    nodes: List[GraphNodeSchema]
    edges: List[GraphEdgeSchema]


class AnalyzerMetaResponse(BaseModel):
    """Metadata describing a registered analytics algorithm."""
    name: str
    description: str
    category: str


class ReachabilityResponse(BaseModel):
    """Transitive closure / blast radius response."""
    root_id: str
    direction: str
    total_reachable: int
    reachable_nodes: List[str]
