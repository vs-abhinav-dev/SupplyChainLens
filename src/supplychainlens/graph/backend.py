from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple
from .models import Edge, Node


class GraphBackend(ABC):
    """
    Abstract interface for graph storage and topology operations in SupplyChainLens.
    Hides underlying implementation details of NetworkX, igraph, or custom stores.
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Name identifier of the backend (e.g., 'networkx', 'igraph')."""
        pass

    @abstractmethod
    def add_node(self, node: Node) -> None:
        """Add a vertex node to the graph."""
        pass

    @abstractmethod
    def add_edge(self, edge: Edge) -> bool:
        """
        Add a directed dependency edge (source_node_id -> target_node_id).
        Returns True if both vertices exist and the edge was added.
        Returns False and records a boundary edge if either vertex is outside the dataset.
        """
        pass

    @abstractmethod
    def get_node(self, node_id: str) -> Optional[Node]:
        """Retrieve node by node_id, or None if not found."""
        pass

    @abstractmethod
    def has_node(self, node_id: str) -> bool:
        """Check if node_id exists in the graph."""
        pass

    @abstractmethod
    def get_edge(self, source_node_id: str, target_node_id: str) -> Optional[Edge]:
        """Retrieve edge between source and target, or None if not found."""
        pass

    @abstractmethod
    def has_edge(self, source_node_id: str, target_node_id: str) -> bool:
        """Check if a directed edge exists from source to target."""
        pass

    @abstractmethod
    def nodes(self) -> List[Node]:
        """Return list of all nodes in the graph."""
        pass

    @abstractmethod
    def edges(self) -> List[Edge]:
        """Return list of all valid in-graph edges."""
        pass

    @abstractmethod
    def node_count(self) -> int:
        """Total number of nodes."""
        pass

    @abstractmethod
    def edge_count(self) -> int:
        """Total number of in-graph edges."""
        pass

    @abstractmethod
    def neighbors(self, node_id: str) -> List[Node]:
        """
        Return outgoing adjacent nodes (dependencies) that node_id depends on.
        Equivalent to successors(node_id).
        """
        pass

    @abstractmethod
    def successors(self, node_id: str) -> List[Node]:
        """Return outgoing adjacent nodes (dependencies) of node_id."""
        pass

    @abstractmethod
    def predecessors(self, node_id: str) -> List[Node]:
        """Return incoming adjacent nodes (dependents) that depend on node_id."""
        pass

    @abstractmethod
    def get_outgoing_edges(self, node_id: str) -> List[Edge]:
        """Return list of directed edges originating from node_id."""
        pass

    @abstractmethod
    def get_incoming_edges(self, node_id: str) -> List[Edge]:
        """Return list of directed edges terminating at node_id."""
        pass

    @abstractmethod
    def degree(self, node_id: str) -> int:
        """Return total degree (in_degree + out_degree) of node_id."""
        pass

    @abstractmethod
    def in_degree(self, node_id: str) -> int:
        """Return in-degree (number of dependents) of node_id."""
        pass

    @abstractmethod
    def out_degree(self, node_id: str) -> int:
        """Return out-degree (number of dependencies) of node_id."""
        pass

    @abstractmethod
    def get_subgraph(self, node_ids: Set[str] | List[str]) -> "GraphBackend":
        """
        Return an induced subgraph containing only the specified nodes
        and the edges between them.
        """
        pass

    @abstractmethod
    def shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        """
        Compute the shortest directed path of node_ids from source to target.
        Returns list of node_ids, or None if no path exists.
        """
        pass

    @abstractmethod
    def connected_components(self) -> List[Set[str]]:
        """
        Return weakly connected components as a list of sets of node_ids.
        Sorted by size descending.
        """
        pass

    @abstractmethod
    def strongly_connected_components(self) -> List[Set[str]]:
        """
        Return strongly connected components as a list of sets of node_ids.
        Sorted by size descending.
        """
        pass

    @abstractmethod
    def record_boundary_edge(
        self,
        source_node_id: str,
        target_node_id: Optional[str],
        target_package: str,
        version_constraint: str,
        reason: str = "target_outside_dataset",
    ) -> None:
        """Record an excluded boundary edge pointing outside the sampled dataset."""
        pass

    @abstractmethod
    def boundary_edges(self) -> List[dict]:
        """Return all recorded boundary edge records."""
        pass

    @abstractmethod
    def boundary_edge_count(self) -> int:
        """Total number of recorded boundary edges."""
        pass

    @abstractmethod
    def validate(self) -> List[str]:
        """Validate internal graph consistency. Returns list of error strings (empty if valid)."""
        pass

    @abstractmethod
    def to_networkx(self) -> Any:
        """Export as NetworkX DiGraph instance."""
        pass

    @abstractmethod
    def to_igraph(self) -> Any:
        """Export as python-igraph Graph instance."""
        pass
