from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx
from ..backend import GraphBackend
from ..models import Edge, Node


class NetworkXBackend(GraphBackend):
    """
    NetworkX-based directed graph backend implementation.
    """

    def __init__(self, nx_graph: Optional[nx.DiGraph] = None) -> None:
        self._g: nx.DiGraph = nx_graph if nx_graph is not None else nx.DiGraph()
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[Tuple[str, str], Edge] = {}
        self._boundary_edges: List[dict] = []

        # If wrapping an existing DiGraph, reconstruct node/edge domain models
        if nx_graph is not None:
            for nid, data in nx_graph.nodes(data=True):
                if "node" in data:
                    self._nodes[nid] = data["node"]
                else:
                    self._nodes[nid] = Node(
                        node_id=nid,
                        package_id=data.get("package_id", nid.split("@")[0]),
                        name=data.get("name", nid.split("@")[0].replace("npm:", "")),
                        version=data.get("version", nid.split("@")[-1] if "@" in nid else "0.0.0"),
                        published_at=data.get("published_at"),
                    )

            for u, v, data in nx_graph.edges(data=True):
                if "edge" in data:
                    self._edges[(u, v)] = data["edge"]
                else:
                    self._edges[(u, v)] = Edge(
                        source_node_id=u,
                        target_node_id=v,
                        version_constraint=data.get("version_constraint", ""),
                        dependency_type=data.get("dependency_type", "dependencies"),
                    )

    @property
    def backend_name(self) -> str:
        return "networkx"

    def add_node(self, node: Node) -> None:
        self._nodes[node.node_id] = node
        self._g.add_node(
            node.node_id,
            node=node,
            package_id=node.package_id,
            name=node.name,
            version=node.version,
            published_at=str(node.published_at or ""),
        )

    def add_edge(self, edge: Edge) -> bool:
        src = edge.source_node_id
        tgt = edge.target_node_id

        if not self.has_node(src) or not self.has_node(tgt):
            reason = []
            if not self.has_node(src):
                reason.append("missing_source")
            if not self.has_node(tgt):
                reason.append("missing_target")
            self.record_boundary_edge(
                source_node_id=src,
                target_node_id=tgt,
                target_package=(
                    tgt.split("@")[0].replace("npm:", "") if "@" in tgt else tgt
                ),
                version_constraint=edge.version_constraint,
                reason=",".join(reason),
            )
            return False

        key = (src, tgt)
        self._edges[key] = edge
        self._g.add_edge(
            src,
            tgt,
            edge=edge,
            version_constraint=edge.version_constraint,
            dependency_type=edge.dependency_type,
        )
        return True

    def get_node(self, node_id: str) -> Optional[Node]:
        return self._nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def get_edge(self, source_node_id: str, target_node_id: str) -> Optional[Edge]:
        return self._edges.get((source_node_id, target_node_id))

    def has_edge(self, source_node_id: str, target_node_id: str) -> bool:
        return (source_node_id, target_node_id) in self._edges

    def nodes(self) -> List[Node]:
        return list(self._nodes.values())

    def edges(self) -> List[Edge]:
        return list(self._edges.values())

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)

    def neighbors(self, node_id: str) -> List[Node]:
        return self.successors(node_id)

    def successors(self, node_id: str) -> List[Node]:
        if not self.has_node(node_id):
            return []
        return [self._nodes[s] for s in self._g.successors(node_id) if s in self._nodes]

    def predecessors(self, node_id: str) -> List[Node]:
        if not self.has_node(node_id):
            return []
        return [self._nodes[p] for p in self._g.predecessors(node_id) if p in self._nodes]

    def get_outgoing_edges(self, node_id: str) -> List[Edge]:
        if not self.has_node(node_id):
            return []
        return [
            self._edges[(node_id, s)]
            for s in self._g.successors(node_id)
            if (node_id, s) in self._edges
        ]

    def get_incoming_edges(self, node_id: str) -> List[Edge]:
        if not self.has_node(node_id):
            return []
        return [
            self._edges[(p, node_id)]
            for p in self._g.predecessors(node_id)
            if (p, node_id) in self._edges
        ]

    def degree(self, node_id: str) -> int:
        if not self.has_node(node_id):
            return 0
        return int(self._g.degree(node_id))

    def in_degree(self, node_id: str) -> int:
        if not self.has_node(node_id):
            return 0
        return int(self._g.in_degree(node_id))

    def out_degree(self, node_id: str) -> int:
        if not self.has_node(node_id):
            return 0
        return int(self._g.out_degree(node_id))

    def get_subgraph(self, node_ids: Set[str] | List[str]) -> "NetworkXBackend":
        valid_ids = {nid for nid in node_ids if self.has_node(nid)}
        sub_nx = self._g.subgraph(valid_ids).copy()
        sub = NetworkXBackend(sub_nx)
        return sub

    def shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        if not self.has_node(source) or not self.has_node(target):
            return None
        try:
            return list(nx.shortest_path(self._g, source=source, target=target))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def connected_components(self) -> List[Set[str]]:
        comps = [set(c) for c in nx.weakly_connected_components(self._g)]
        comps.sort(key=lambda c: (-len(c), sorted(list(c))))
        return comps

    def strongly_connected_components(self) -> List[Set[str]]:
        comps = [set(c) for c in nx.strongly_connected_components(self._g)]
        comps.sort(key=lambda c: (-len(c), sorted(list(c))))
        return comps

    def record_boundary_edge(
        self,
        source_node_id: str,
        target_node_id: Optional[str],
        target_package: str,
        version_constraint: str,
        reason: str = "target_outside_dataset",
    ) -> None:
        self._boundary_edges.append({
            "source_node_id": source_node_id,
            "target_node_id": target_node_id,
            "target_package": target_package,
            "version_constraint": version_constraint,
            "reason": reason,
        })

    def boundary_edges(self) -> List[dict]:
        return list(self._boundary_edges)

    def boundary_edge_count(self) -> int:
        return len(self._boundary_edges)

    def validate(self) -> List[str]:
        errors = []
        for (src, tgt), edge in self._edges.items():
            if src not in self._nodes:
                errors.append(f"Edge ({src} -> {tgt}) has unknown source node '{src}'")
            if tgt not in self._nodes:
                errors.append(f"Edge ({src} -> {tgt}) has unknown target node '{tgt}'")
            if edge.source_node_id != src or edge.target_node_id != tgt:
                errors.append(f"Edge metadata key mismatch: ({src}, {tgt}) vs {edge}")
        return errors

    def to_networkx(self) -> nx.DiGraph:
        return self._g.copy()

    def to_igraph(self) -> Any:
        import igraph

        ig = igraph.Graph(directed=True)
        node_ids = list(self._nodes.keys())
        node_id_to_idx = {nid: i for i, nid in enumerate(node_ids)}

        ig.add_vertices(len(node_ids))
        ig.vs["name"] = node_ids
        ig.vs["package_id"] = [self._nodes[nid].package_id for nid in node_ids]
        ig.vs["package_name"] = [self._nodes[nid].name for nid in node_ids]
        ig.vs["version"] = [self._nodes[nid].version for nid in node_ids]
        ig.vs["published_at"] = [str(self._nodes[nid].published_at or "") for nid in node_ids]

        edge_tuples = []
        constraints = []
        dep_types = []

        for (src, tgt), edge in self._edges.items():
            if src in node_id_to_idx and tgt in node_id_to_idx:
                edge_tuples.append((node_id_to_idx[src], node_id_to_idx[tgt]))
                constraints.append(edge.version_constraint)
                dep_types.append(edge.dependency_type)

        ig.add_edges(edge_tuples)
        ig.es["version_constraint"] = constraints
        ig.es["dependency_type"] = dep_types
        return ig
