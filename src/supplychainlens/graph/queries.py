from collections import deque
from typing import Any, Dict, List, Optional, Set

from .backend import GraphBackend
from .models import Edge, Node, PackageSummary, PathResult, SubgraphView
from .repository import GraphRepository


class GraphQueryService:
    """
    High-level graph query and traversal service.
    Translates package and version identifiers into localized subgraphs,
    paths, and dependency/dependent trees for the API and frontend.
    """

    def __init__(
        self,
        repository: Optional[GraphRepository] = None,
        graph: Optional[GraphBackend] = None,
    ) -> None:
        if repository is None and graph is None:
            self.repository = GraphRepository()
            self.graph = self.repository.get_graph()
        elif repository is not None:
            self.repository = repository
            self.graph = repository.get_graph() if graph is None else graph
        else:
            self.repository = None
            self.graph = graph

    def resolve_node_id(self, identifier: str) -> Optional[str]:
        """
        Resolves a package or version string into a valid node_id in the graph.
        Examples:
          - 'npm:express@4.18.0' -> 'npm:express@4.18.0'
          - 'express@4.18.0'     -> 'npm:express@4.18.0'
          - 'express'            -> latest node_id e.g. 'npm:express@5.1.0'
        """
        ident = identifier.strip()
        if not ident:
            return None

        # Direct check
        if self.graph.has_node(ident):
            return ident

        # Check with 'npm:' prefix
        if not ident.startswith("npm:"):
            with_prefix = f"npm:{ident}"
            if self.graph.has_node(with_prefix):
                return with_prefix

        # If it's a bare package name, resolve to latest version
        if self.repository is not None:
            clean_pkg = ident.replace("npm:", "").split("@")[0]
            latest = self.repository.get_latest_version(clean_pkg)
            if latest and self.graph.has_node(latest.node_id):
                return latest.node_id

        return None

    def get_neighborhood(
        self,
        identifier: str,
        depth: int = 1,
        direction: str = "both",
        max_nodes: int = 150,
    ) -> Optional[SubgraphView]:
        """
        Extracts a localized neighborhood subgraph around identifier up to depth steps.
        direction can be: 'dependencies' (outgoing), 'dependents' (incoming), or 'both'.
        Guarantees bounded traversal up to max_nodes.
        """
        root_id = self.resolve_node_id(identifier)
        if not root_id:
            return None

        depth = max(1, min(depth, 5))
        dir_norm = direction.lower().strip()
        if dir_norm in ("outgoing", "dependencies", "downstream"):
            follow_outgoing = True
            follow_incoming = False
        elif dir_norm in ("incoming", "dependents", "upstream"):
            follow_outgoing = False
            follow_incoming = True
        else:
            follow_outgoing = True
            follow_incoming = True

        visited_nodes: Set[str] = {root_id}
        queue: deque = deque([(root_id, 0)])
        truncated = False

        while queue:
            current_id, current_depth = queue.popleft()
            if current_depth >= depth:
                continue

            adjacent_ids: Set[str] = set()
            if follow_outgoing:
                for n in self.graph.successors(current_id):
                    adjacent_ids.add(n.node_id)
            if follow_incoming:
                for n in self.graph.predecessors(current_id):
                    adjacent_ids.add(n.node_id)

            for adj_id in adjacent_ids:
                if adj_id not in visited_nodes:
                    if len(visited_nodes) >= max_nodes:
                        truncated = True
                        break
                    visited_nodes.add(adj_id)
                    queue.append((adj_id, current_depth + 1))

            if truncated:
                break

        # Format node items for UI
        node_items: List[Dict[str, Any]] = []
        for nid in visited_nodes:
            n = self.graph.get_node(nid)
            if n:
                node_items.append({
                    "id": n.node_id,
                    "label": f"{n.name}@{n.version}",
                    "name": n.name,
                    "version": n.version,
                    "package_id": n.package_id,
                    "published_at": n.published_at,
                    "is_root": (n.node_id == root_id),
                    "degree": self.graph.degree(n.node_id),
                    "in_degree": self.graph.in_degree(n.node_id),
                    "out_degree": self.graph.out_degree(n.node_id),
                })

        # Format edge items for UI (induced edges among visited nodes)
        edge_items: List[Dict[str, Any]] = []
        for src in visited_nodes:
            for edge in self.graph.get_outgoing_edges(src):
                if edge.target_node_id in visited_nodes:
                    edge_items.append({
                        "source": edge.source_node_id,
                        "target": edge.target_node_id,
                        "version_constraint": edge.version_constraint,
                        "dependency_type": edge.dependency_type,
                    })

        return SubgraphView(
            root_id=root_id,
            depth=depth,
            direction=dir_norm,
            nodes=node_items,
            edges=edge_items,
            total_nodes=len(node_items),
            total_edges=len(edge_items),
            truncated=truncated,
        )

    def get_dependencies(
        self, identifier: str, depth: int = 1, max_nodes: int = 150
    ) -> Optional[SubgraphView]:
        """Retrieve dependencies (outgoing edges) subgraph."""
        return self.get_neighborhood(identifier, depth=depth, direction="dependencies", max_nodes=max_nodes)

    def get_dependents(
        self, identifier: str, depth: int = 1, max_nodes: int = 150
    ) -> Optional[SubgraphView]:
        """Retrieve dependents (incoming edges) subgraph."""
        return self.get_neighborhood(identifier, depth=depth, direction="dependents", max_nodes=max_nodes)

    def find_path(self, source_ident: str, target_ident: str) -> Optional[PathResult]:
        """Find the shortest directed dependency path between two packages or versions."""
        src_id = self.resolve_node_id(source_ident)
        tgt_id = self.resolve_node_id(target_ident)
        if not src_id or not tgt_id:
            return None

        path_ids = self.graph.shortest_path(src_id, tgt_id)
        if not path_ids:
            return None

        path_nodes: List[Node] = []
        path_edges: List[Edge] = []

        for nid in path_ids:
            n = self.graph.get_node(nid)
            if n:
                path_nodes.append(n)

        for i in range(len(path_ids) - 1):
            e = self.graph.get_edge(path_ids[i], path_ids[i + 1])
            if e:
                path_edges.append(e)

        return PathResult(
            source_node_id=src_id,
            target_node_id=tgt_id,
            path=path_ids,
            length=len(path_ids) - 1,
            nodes=path_nodes,
            edges=path_edges,
        )

    def get_reachability(self, identifier: str, direction: str = "dependencies") -> Set[str]:
        """
        Computes the complete transitive reachability set from identifier.
        If direction is 'dependencies', computes downstream dependency closure.
        If direction is 'dependents', computes upstream blast radius.
        """
        root_id = self.resolve_node_id(identifier)
        if not root_id:
            return set()

        is_dependencies = direction.lower() in ("dependencies", "outgoing")
        visited: Set[str] = set()
        queue: deque = deque([root_id])

        while queue:
            curr = queue.popleft()
            adjacent = (
                self.graph.successors(curr)
                if is_dependencies
                else self.graph.predecessors(curr)
            )
            for node in adjacent:
                if node.node_id not in visited and node.node_id != root_id:
                    visited.add(node.node_id)
                    queue.append(node.node_id)

        return visited

    def get_package_summary(self, package_name: str) -> Optional[PackageSummary]:
        """Return structured summary for a package name."""
        if not self.repository:
            return None
        info = self.repository.get_package(package_name)
        if not info:
            return None

        return PackageSummary(
            package_id=info["package_id"],
            name=info["name"],
            total_versions=info["total_versions"],
            latest_version=info["latest_version"],
            latest_node_id=info["latest_node_id"],
            versions=info["versions"],
            node_ids=info["node_ids"],
        )
