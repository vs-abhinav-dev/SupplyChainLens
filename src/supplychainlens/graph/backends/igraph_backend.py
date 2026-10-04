from typing import Any, Dict, List, Optional, Set, Tuple
import igraph
from ..backend import GraphBackend
from ..models import Edge, Node


class IGraphBackend(GraphBackend):
    """
    python-igraph-based directed graph backend implementation.
    Offers high-performance C-speed graph algorithms and memory efficiency.
    """

    def __init__(self, ig_graph: Optional[igraph.Graph] = None) -> None:
        self._g: igraph.Graph = ig_graph if ig_graph is not None else igraph.Graph(directed=True)
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[Tuple[str, str], Edge] = {}
        self._name_to_idx: Dict[str, int] = {}
        self._idx_to_name: Dict[int, str] = {}
        self._boundary_edges: List[dict] = []

        if ig_graph is not None:
            # Reconstruct index and node models from existing igraph Graph
            for idx, v in enumerate(ig_graph.vs):
                nid = v["name"] if "name" in v.attributes() else str(idx)
                self._name_to_idx[nid] = idx
                self._idx_to_name[idx] = nid
                self._nodes[nid] = Node(
                    node_id=nid,
                    package_id=v.attributes().get("package_id", nid.split("@")[0]),
                    name=v.attributes().get("package_name", nid.split("@")[0].replace("npm:", "")),
                    version=v.attributes().get("version", nid.split("@")[-1] if "@" in nid else "0.0.0"),
                    published_at=v.attributes().get("published_at"),
                )

            for e in ig_graph.es:
                src = self._idx_to_name[e.source]
                tgt = self._idx_to_name[e.target]
                self._edges[(src, tgt)] = Edge(
                    source_node_id=src,
                    target_node_id=tgt,
                    version_constraint=e.attributes().get("version_constraint", ""),
                    dependency_type=e.attributes().get("dependency_type", "dependencies"),
                )

    @property
    def backend_name(self) -> str:
        return "igraph"

    def add_node(self, node: Node) -> None:
        if node.node_id in self._name_to_idx:
            # Update node model if re-adding
            self._nodes[node.node_id] = node
            return

        idx = self._g.vcount()
        self._g.add_vertex(
            name=node.node_id,
            package_id=node.package_id,
            package_name=node.name,
            version=node.version,
            published_at=str(node.published_at or ""),
        )
        self._name_to_idx[node.node_id] = idx
        self._idx_to_name[idx] = node.node_id
        self._nodes[node.node_id] = node

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
        if key in self._edges:
            self._edges[key] = edge
            return True

        u_idx = self._name_to_idx[src]
        v_idx = self._name_to_idx[tgt]

        self._g.add_edge(
            u_idx,
            v_idx,
            version_constraint=edge.version_constraint,
            dependency_type=edge.dependency_type,
        )
        self._edges[key] = edge
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
        return self._g.vcount()

    def edge_count(self) -> int:
        return self._g.ecount()

    def neighbors(self, node_id: str) -> List[Node]:
        return self.successors(node_id)

    def successors(self, node_id: str) -> List[Node]:
        if not self.has_node(node_id):
            return []
        u_idx = self._name_to_idx[node_id]
        succ_indices = self._g.neighbors(u_idx, mode="out")
        return [self._nodes[self._idx_to_name[idx]] for idx in succ_indices if idx in self._idx_to_name]

    def predecessors(self, node_id: str) -> List[Node]:
        if not self.has_node(node_id):
            return []
        u_idx = self._name_to_idx[node_id]
        pred_indices = self._g.neighbors(u_idx, mode="in")
        return [self._nodes[self._idx_to_name[idx]] for idx in pred_indices if idx in self._idx_to_name]

    def get_outgoing_edges(self, node_id: str) -> List[Edge]:
        if not self.has_node(node_id):
            return []
        u_idx = self._name_to_idx[node_id]
        succ_indices = self._g.neighbors(u_idx, mode="out")
        return [
            self._edges[(node_id, self._idx_to_name[idx])]
            for idx in succ_indices
            if (node_id, self._idx_to_name[idx]) in self._edges
        ]

    def get_incoming_edges(self, node_id: str) -> List[Edge]:
        if not self.has_node(node_id):
            return []
        u_idx = self._name_to_idx[node_id]
        pred_indices = self._g.neighbors(u_idx, mode="in")
        return [
            self._edges[(self._idx_to_name[idx], node_id)]
            for idx in pred_indices
            if (self._idx_to_name[idx], node_id) in self._edges
        ]

    def degree(self, node_id: str) -> int:
        if not self.has_node(node_id):
            return 0
        u_idx = self._name_to_idx[node_id]
        return int(self._g.degree(u_idx, mode="all"))

    def in_degree(self, node_id: str) -> int:
        if not self.has_node(node_id):
            return 0
        u_idx = self._name_to_idx[node_id]
        return int(self._g.degree(u_idx, mode="in"))

    def out_degree(self, node_id: str) -> int:
        if not self.has_node(node_id):
            return 0
        u_idx = self._name_to_idx[node_id]
        return int(self._g.degree(u_idx, mode="out"))

    def get_subgraph(self, node_ids: Set[str] | List[str]) -> "IGraphBackend":
        sub = IGraphBackend()
        valid_ids = {nid for nid in node_ids if self.has_node(nid)}
        for nid in valid_ids:
            sub.add_node(self._nodes[nid])

        for (src, tgt), edge in self._edges.items():
            if src in valid_ids and tgt in valid_ids:
                sub.add_edge(edge)

        return sub

    def shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        import warnings
        if not self.has_node(source) or not self.has_node(target):
            return None
        u_idx = self._name_to_idx[source]
        v_idx = self._name_to_idx[target]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            paths = self._g.get_shortest_paths(u_idx, to=v_idx, mode="out", output="vpath")
        if not paths or not paths[0]:
            return None
        return [self._idx_to_name[idx] for idx in paths[0]]

    def connected_components(self) -> List[Set[str]]:
        comps = self._g.connected_components(mode="weak")
        res = [set(self._idx_to_name[idx] for idx in c) for c in comps]
        res.sort(key=lambda c: (-len(c), sorted(list(c))))
        return res

    def strongly_connected_components(self) -> List[Set[str]]:
        comps = self._g.connected_components(mode="strong")
        res = [set(self._idx_to_name[idx] for idx in c) for c in comps]
        res.sort(key=lambda c: (-len(c), sorted(list(c))))
        return res

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

    def to_networkx(self) -> Any:
        import networkx as nx

        nx_g = nx.DiGraph()
        for nid, node in self._nodes.items():
            nx_g.add_node(
                nid,
                package_id=node.package_id,
                name=node.name,
                version=node.version,
                published_at=str(node.published_at or ""),
            )

        for (src, tgt), edge in self._edges.items():
            nx_g.add_edge(
                src,
                tgt,
                version_constraint=edge.version_constraint,
                dependency_type=edge.dependency_type,
            )
        return nx_g

    def to_igraph(self) -> igraph.Graph:
        return self._g.copy()
