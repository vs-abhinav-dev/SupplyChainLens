from typing import Dict, List
from ..graph.backend import GraphBackend
from .base import GraphAnalyzer
from .models import RankingItem, RankingResult


class BetweennessAnalyzer(GraphAnalyzer):
    """
    Computes betweenness centrality across nodes.
    Identifies dependency bridges and structural chokepoints between ecosystem components.
    """

    @property
    def name(self) -> str:
        return "betweenness"

    @property
    def description(self) -> str:
        return "Calculates betweenness centrality to identify chokepoint and bridge packages."

    @property
    def category(self) -> str:
        return "centrality"

    def analyze(
        self,
        graph: GraphBackend,
        top_n: int = 50,
        **kwargs,
    ) -> RankingResult:
        node_scores: Dict[str, float] = {}

        if graph.backend_name == "igraph":
            ig = graph.to_igraph()
            if ig.vcount() > 0:
                # igraph betweenness in C (Brandes algorithm)
                raw_scores = ig.betweenness(directed=True)
                # Normalize by (n-1)*(n-2) for directed graph if n > 2
                n = ig.vcount()
                scale = 1.0 / ((n - 1) * (n - 2)) if n > 2 else 1.0
                for idx, score in enumerate(raw_scores):
                    nid = ig.vs[idx]["name"]
                    node_scores[nid] = float(score * scale)
        else:
            import networkx as nx
            nx_g = graph.to_networkx()
            if nx_g.number_of_nodes() > 0:
                node_scores = nx.betweenness_centrality(nx_g, normalized=True)

        sorted_items = sorted(node_scores.items(), key=lambda x: x[1], reverse=True)
        rankings: List[RankingItem] = []

        for rank, (nid, score) in enumerate(sorted_items[:top_n], start=1):
            node = graph.get_node(nid)
            rankings.append(RankingItem(
                node_id=nid,
                name=node.name if node else nid,
                version=node.version if node else "",
                score=round(score, 8),
                rank=rank,
            ))

        scores_list = list(node_scores.values())
        summary = {
            "min": round(min(scores_list), 8) if scores_list else 0.0,
            "max": round(max(scores_list), 8) if scores_list else 0.0,
            "mean": round(sum(scores_list) / len(scores_list), 8) if scores_list else 0.0,
        }

        return RankingResult(
            metric="betweenness",
            total_nodes=graph.node_count(),
            rankings=rankings,
            summary=summary,
        )
