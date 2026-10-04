from collections import Counter
from typing import List, Optional
from ..graph.backend import GraphBackend
from .base import GraphAnalyzer
from .models import DegreeAnalysisResult, RankingItem


class DegreeAnalyzer(GraphAnalyzer):
    """
    Analyzes in-degree, out-degree, degree distributions, graph density,
    and identifies high fan-in and high fan-out packages.
    """

    @property
    def name(self) -> str:
        return "degree"

    @property
    def description(self) -> str:
        return "Calculates graph density, in/out degree distributions, and top fan-in/fan-out packages."

    @property
    def category(self) -> str:
        return "structural"

    def analyze(self, graph: GraphBackend, top_n: int = 25, **kwargs) -> DegreeAnalysisResult:
        n_count = graph.node_count()
        e_count = graph.edge_count()

        density = (e_count / (n_count * (n_count - 1))) if n_count > 1 else 0.0
        avg_degree = (2.0 * e_count / n_count) if n_count > 0 else 0.0

        in_degrees = {}
        out_degrees = {}

        for node in graph.nodes():
            nid = node.node_id
            in_degrees[nid] = graph.in_degree(nid)
            out_degrees[nid] = graph.out_degree(nid)

        in_dist = Counter(in_degrees.values())
        out_dist = Counter(out_degrees.values())

        # Top fan-in (highest in-degree, most depended upon)
        sorted_in = sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)[:top_n]
        top_fan_in: List[RankingItem] = []
        for rank, (nid, deg) in enumerate(sorted_in, start=1):
            node = graph.get_node(nid)
            top_fan_in.append(RankingItem(
                node_id=nid,
                name=node.name if node else nid,
                version=node.version if node else "",
                score=float(deg),
                rank=rank,
            ))

        # Top fan-out (highest out-degree, most dependencies)
        sorted_out = sorted(out_degrees.items(), key=lambda x: x[1], reverse=True)[:top_n]
        top_fan_out: List[RankingItem] = []
        for rank, (nid, deg) in enumerate(sorted_out, start=1):
            node = graph.get_node(nid)
            top_fan_out.append(RankingItem(
                node_id=nid,
                name=node.name if node else nid,
                version=node.version if node else "",
                score=float(deg),
                rank=rank,
            ))

        return DegreeAnalysisResult(
            total_nodes=n_count,
            total_edges=e_count,
            density=round(density, 6),
            avg_degree=round(avg_degree, 3),
            in_degree_distribution={k: v for k, v in sorted(in_dist.items())},
            out_degree_distribution={k: v for k, v in sorted(out_dist.items())},
            top_fan_in=top_fan_in,
            top_fan_out=top_fan_out,
        )
