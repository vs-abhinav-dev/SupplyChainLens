from collections import Counter, deque
from typing import Dict, List, Optional
from ..graph.backend import GraphBackend
from .base import GraphAnalyzer
from .models import DependencyDepthResult, RankingItem


class DependencyDepthAnalyzer(GraphAnalyzer):
    """
    Analyzes transitive dependency tree depth across package versions.
    Deeper trees indicate higher fragile supply chain risk and transitive vulnerability exposure.
    """

    @property
    def name(self) -> str:
        return "dependency_depth"

    @property
    def description(self) -> str:
        return "Calculates transitive dependency tree depth, identifying packages with the deepest dependency trees."

    @property
    def category(self) -> str:
        return "dependency"

    def analyze(
        self,
        graph: GraphBackend,
        max_hops: int = 25,
        top_n: int = 25,
        **kwargs,
    ) -> DependencyDepthResult:
        memo: Dict[str, int] = {}

        def compute_depth(node_id: str, visited_path: set[str], current_hop: int) -> int:
            if current_hop >= max_hops:
                return 0
            if node_id in memo:
                return memo[node_id]
            if node_id in visited_path:
                return 0  # Cycle detected, break

            succs = graph.successors(node_id)
            if not succs:
                memo[node_id] = 0
                return 0

            new_visited = visited_path | {node_id}
            max_succ_depth = 0
            for s in succs:
                d = compute_depth(s.node_id, new_visited, current_hop + 1)
                if d > max_succ_depth:
                    max_succ_depth = d

            result_depth = 1 + max_succ_depth
            memo[node_id] = result_depth
            return result_depth

        node_depths: Dict[str, int] = {}
        for node in graph.nodes():
            node_depths[node.node_id] = compute_depth(node.node_id, set(), 0)

        depth_dist = Counter(node_depths.values())
        max_depth = max(node_depths.values(), default=0)
        avg_depth = (
            sum(node_depths.values()) / len(node_depths) if node_depths else 0.0
        )

        sorted_depths = sorted(node_depths.items(), key=lambda x: x[1], reverse=True)[:top_n]
        deepest_nodes: List[RankingItem] = []

        for rank, (nid, d) in enumerate(sorted_depths, start=1):
            n = graph.get_node(nid)
            deepest_nodes.append(RankingItem(
                node_id=nid,
                name=n.name if n else nid,
                version=n.version if n else "",
                score=float(d),
                rank=rank,
            ))

        return DependencyDepthResult(
            max_depth=max_depth,
            avg_depth=round(avg_depth, 2),
            depth_distribution={k: v for k, v in sorted(depth_dist.items())},
            deepest_nodes=deepest_nodes,
        )
