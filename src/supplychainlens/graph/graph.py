from typing import Dict, List, Optional, Set, Tuple
from .models import Edge, Node


class VersionGraph:
    """
    Directed graph abstraction for npm package version dependencies.

    Vertices represent npm package versions (Node).
    Edges represent resolved dependencies (Edge), directed from source to target (A -> B means A depends on B).

    Edges are only included if both source and target vertices are present in the graph.
    Boundary edges (where target vertex lies outside the dataset) are tracked separately.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[Tuple[str, str], Edge] = {}
        self._outgoing: Dict[str, Dict[str, Edge]] = {}
        self._incoming: Dict[str, Dict[str, Edge]] = {}
        self._boundary_edges: List[dict] = []

    def add_node(self, node: Node) -> None:
        """Add a vertex node to the graph."""
        self._nodes[node.node_id] = node
        if node.node_id not in self._outgoing:
            self._outgoing[node.node_id] = {}
        if node.node_id not in self._incoming:
            self._incoming[node.node_id] = {}

    def get_node(self, node_id: str) -> Optional[Node]:
        """Retrieve node by node_id, or None if not present."""
        return self._nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        """Check if node_id exists in the graph."""
        return node_id in self._nodes

    def add_edge(self, edge: Edge) -> bool:
        """
        Add a dependency edge (source_node_id -> target_node_id).

        Returns True if the edge was added (both vertices exist).
        Returns False if excluded due to dataset boundary (either vertex missing).
        """
        if not self.has_node(edge.source_node_id) or not self.has_node(edge.target_node_id):
            reason = []
            if not self.has_node(edge.source_node_id):
                reason.append("missing_source")
            if not self.has_node(edge.target_node_id):
                reason.append("missing_target")
            self.record_boundary_edge(
                source_node_id=edge.source_node_id,
                target_node_id=edge.target_node_id,
                target_package=edge.target_node_id.split("@")[0].replace("npm:", "") if "@" in edge.target_node_id else edge.target_node_id,
                version_constraint=edge.version_constraint,
                reason=",".join(reason),
            )
            return False

        key = (edge.source_node_id, edge.target_node_id)
        self._edges[key] = edge
        self._outgoing[edge.source_node_id][edge.target_node_id] = edge
        self._incoming[edge.target_node_id][edge.source_node_id] = edge
        return True

    def record_boundary_edge(
        self,
        source_node_id: str,
        target_node_id: Optional[str],
        target_package: str,
        version_constraint: str,
        reason: str = "target_outside_dataset",
    ) -> None:
        """Record an excluded edge pointing outside the sampled dataset boundary."""
        self._boundary_edges.append({
            "source_node_id": source_node_id,
            "target_node_id": target_node_id,
            "target_package": target_package,
            "version_constraint": version_constraint,
            "reason": reason,
        })

    def get_edge(self, source_node_id: str, target_node_id: str) -> Optional[Edge]:
        """Retrieve edge metadata between source and target nodes."""
        return self._edges.get((source_node_id, target_node_id))

    def get_neighbors(self, node_id: str) -> List[Node]:
        """Return list of target nodes that node_id depends on (outgoing adjacent nodes)."""
        if node_id not in self._outgoing:
            return []
        return [
            self._nodes[target_id]
            for target_id in self._outgoing[node_id].keys()
            if target_id in self._nodes
        ]

    def get_dependents(self, node_id: str) -> List[Node]:
        """Return list of source nodes that depend on node_id (incoming adjacent nodes)."""
        if node_id not in self._incoming:
            return []
        return [
            self._nodes[source_id]
            for source_id in self._incoming[node_id].keys()
            if source_id in self._nodes
        ]

    def get_outgoing_edges(self, node_id: str) -> List[Edge]:
        """Return list of outgoing edges from node_id."""
        if node_id not in self._outgoing:
            return []
        return list(self._outgoing[node_id].values())

    def get_incoming_edges(self, node_id: str) -> List[Edge]:
        """Return list of incoming edges to node_id."""
        if node_id not in self._incoming:
            return []
        return list(self._incoming[node_id].values())

    def nodes(self) -> List[Node]:
        """Return list of all vertex nodes in the graph."""
        return list(self._nodes.values())

    def edges(self) -> List[Edge]:
        """Return list of all in-graph edges."""
        return list(self._edges.values())

    def node_count(self) -> int:
        """Total vertex count."""
        return len(self._nodes)

    def edge_count(self) -> int:
        """Total in-graph edge count."""
        return len(self._edges)

    def boundary_edge_count(self) -> int:
        """Total count of excluded boundary edges."""
        return len(self._boundary_edges)

    def get_boundary_edges(self) -> List[dict]:
        """Return list of boundary edge records."""
        return self._boundary_edges

    def validate(self) -> List[str]:
        """
        Validate graph invariants and consistency.
        Returns list of validation error strings (empty list if valid).
        """
        errors = []

        for (src, tgt), edge in self._edges.items():
            if src not in self._nodes:
                errors.append(f"Edge ({src} -> {tgt}) has non-existent source node '{src}'")
            if tgt not in self._nodes:
                errors.append(f"Edge ({src} -> {tgt}) has non-existent target node '{tgt}'")
            if edge.source_node_id != src or edge.target_node_id != tgt:
                errors.append(f"Edge metadata key mismatch: key=({src}, {tgt}), edge=({edge.source_node_id}, {edge.target_node_id})")

        for src, targets in self._outgoing.items():
            if src not in self._nodes:
                errors.append(f"Outgoing adjacency index contains unknown source node '{src}'")
            for tgt in targets:
                if tgt not in self._nodes:
                    errors.append(f"Outgoing adjacency index from '{src}' points to unknown target node '{tgt}'")

        for tgt, sources in self._incoming.items():
            if tgt not in self._nodes:
                errors.append(f"Incoming adjacency index contains unknown target node '{tgt}'")
            for src in sources:
                if src not in self._nodes:
                    errors.append(f"Incoming adjacency index to '{tgt}' points from unknown source node '{src}'")

        return errors
