from typing import Dict, List
from ..graph.backend import GraphBackend
from .base import GraphAnalyzer
from .models import RankingItem, RankingResult


class PageRankAnalyzer(GraphAnalyzer):
    """
    Computes directed PageRank centrality across vertices.
    Measures the structural authority and foundational importance of package versions.
    """

    @property
    def name(self) -> str:
        return "pagerank"

    @property
    def description(self) -> str:
        return "Calculates directed PageRank centrality identifying the most foundational packages in the ecosystem."

    @property
    def category(self) -> str:
        return "centrality"

    def analyze(
        self,
        graph: GraphBackend,
        damping: float = 0.85,
        top_n: int = 50,
        **kwargs,
    ) -> RankingResult:
        node_scores: Dict[str, float] = {}

        if graph.backend_name == "igraph":
            ig = graph.to_igraph()
            if ig.vcount() > 0:
                raw_scores = ig.pagerank(directed=True, damping=damping)
                for idx, score in enumerate(raw_scores):
                    nid = ig.vs[idx]["name"]
                    node_scores[nid] = float(score)
        else:
            import networkx as nx
            nx_g = graph.to_networkx()
            if nx_g.number_of_nodes() > 0:
                node_scores = nx.pagerank(nx_g, alpha=damping)

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
            metric="pagerank",
            total_nodes=graph.node_count(),
            rankings=rankings,
            summary=summary,
        )
