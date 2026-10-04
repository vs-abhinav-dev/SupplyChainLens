from collections import Counter
from typing import List
from ..graph.backend import GraphBackend
from .base import GraphAnalyzer
from .models import ComponentItem, ComponentsResult


class ComponentsAnalyzer(GraphAnalyzer):
    """
    Analyzes connected components (both weakly and strongly connected).
    Measures ecosystem fragmentation and cluster cohesion.
    """

    @property
    def name(self) -> str:
        return "components"

    @property
    def description(self) -> str:
        return "Analyzes weakly and strongly connected components and ecosystem cluster sizes."

    @property
    def category(self) -> str:
        return "structural"

    def analyze(
        self,
        graph: GraphBackend,
        mode: str = "weak",
        top_n: int = 25,
        **kwargs,
    ) -> ComponentsResult:
        if mode.lower() in ("strong", "scc"):
            raw_comps = graph.strongly_connected_components()
            comp_type = "strong"
        else:
            raw_comps = graph.connected_components()
            comp_type = "weak"

        total_comps = len(raw_comps)
        max_size = max((len(c) for c in raw_comps), default=0)
        sizes = [len(c) for c in raw_comps]
        size_dist = Counter(sizes)

        component_items: List[ComponentItem] = []
        for idx, comp in enumerate(raw_comps[:top_n], start=1):
            nodes_list = sorted(list(comp))
            component_items.append(ComponentItem(
                component_id=idx,
                size=len(comp),
                sample_nodes=nodes_list[:10],
            ))

        return ComponentsResult(
            component_type=comp_type,
            total_components=total_comps,
            max_component_size=max_size,
            components=component_items,
            size_distribution={k: v for k, v in sorted(size_dist.items(), reverse=True)},
        )
