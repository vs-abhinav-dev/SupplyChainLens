import json
from typing import Any, Dict, List, Optional
from ..graph.backend import GraphBackend
from .base import GraphAnalyzer
from .betweenness import BetweennessAnalyzer
from .cache import AnalyticsCache
from .components import ComponentsAnalyzer
from .cycles import CyclesAnalyzer
from .degree import DegreeAnalyzer
from .dependency_depth import DependencyDepthAnalyzer
from .pagerank import PageRankAnalyzer


class AnalyticsRegistry:
    """
    Central registry and execution manager for SupplyChainLens graph analytics.
    Allows modular registration of graph algorithms without altering API or crawler internals.
    """

    def __init__(self, cache: Optional[AnalyticsCache] = None) -> None:
        self._analyzers: Dict[str, GraphAnalyzer] = {}
        self.cache: AnalyticsCache = cache if cache is not None else AnalyticsCache()

    def register(self, analyzer: GraphAnalyzer) -> None:
        """Register a new GraphAnalyzer instance."""
        self._analyzers[analyzer.name.lower()] = analyzer

    def get(self, name: str) -> Optional[GraphAnalyzer]:
        """Retrieve an analyzer by algorithm name."""
        return self._analyzers.get(name.lower().strip())

    def list_analyzers(self) -> List[Dict[str, str]]:
        """List metadata for all registered analyzers."""
        return [
            {
                "name": analyzer.name,
                "description": analyzer.description,
                "category": analyzer.category,
            }
            for analyzer in self._analyzers.values()
        ]

    def run(
        self,
        name: str,
        graph: GraphBackend,
        use_cache: bool = True,
        **kwargs,
    ) -> Any:
        """
        Executes a registered graph analyzer with caching support.
        """
        analyzer = self.get(name)
        if not analyzer:
            raise KeyError(
                f"Analyzer '{name}' is not registered. Available analyzers: {list(self._analyzers.keys())}"
            )

        kwargs_str = json.dumps(kwargs, sort_keys=True)
        cache_key = f"{analyzer.name}:{graph.backend_name}:{kwargs_str}"

        if use_cache:
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                return cached_result

        result = analyzer.analyze(graph, **kwargs)

        if use_cache:
            self.cache.set(cache_key, result)

        return result


def create_default_registry() -> AnalyticsRegistry:
    """Instantiate and populate the default AnalyticsRegistry with core algorithms."""
    registry = AnalyticsRegistry()
    registry.register(DegreeAnalyzer())
    registry.register(PageRankAnalyzer())
    registry.register(BetweennessAnalyzer())
    registry.register(ComponentsAnalyzer())
    registry.register(CyclesAnalyzer())
    registry.register(DependencyDepthAnalyzer())
    return registry


# Global default registry instance
default_registry = create_default_registry()
