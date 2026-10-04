from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RankingItem(BaseModel):
    """Represents a ranked node score item in an analytics ranking."""
    node_id: str
    name: str
    version: str
    score: float
    rank: int


class RankingResult(BaseModel):
    """Represents the results of a centrality or ranking analysis across nodes."""
    metric: str
    total_nodes: int
    rankings: List[RankingItem]
    summary: Dict[str, float] = Field(default_factory=dict)


class NodeMetric(BaseModel):
    """Individual metric calculated for a single node."""
    node_id: str
    metric: str
    value: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphMetric(BaseModel):
    """Aggregate metric calculated for the entire graph."""
    metric: str
    value: float | int | str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ComponentItem(BaseModel):
    """Details of a single connected component."""
    component_id: int
    size: int
    sample_nodes: List[str]


class ComponentsResult(BaseModel):
    """Results of connected components analysis."""
    component_type: str  # 'weak' or 'strong'
    total_components: int
    max_component_size: int
    components: List[ComponentItem]
    size_distribution: Dict[int, int] = Field(default_factory=dict)


class CycleItem(BaseModel):
    """Details of a single detected dependency cycle."""
    cycle_id: int
    length: int
    cycle: List[str]


class CyclesResult(BaseModel):
    """Results of dependency cycle detection."""
    total_cycles: int
    has_cycles: bool
    cycles: List[CycleItem]


class DependencyDepthResult(BaseModel):
    """Results of transitive dependency depth and blast radius analysis."""
    max_depth: int
    avg_depth: float
    depth_distribution: Dict[int, int]
    deepest_nodes: List[RankingItem]


class DegreeAnalysisResult(BaseModel):
    """Results of degree centrality and connectivity analysis."""
    total_nodes: int
    total_edges: int
    density: float
    avg_degree: float
    in_degree_distribution: Dict[int, int]
    out_degree_distribution: Dict[int, int]
    top_fan_in: List[RankingItem]   # Most depended-upon nodes
    top_fan_out: List[RankingItem]  # Nodes with highest direct dependency count
