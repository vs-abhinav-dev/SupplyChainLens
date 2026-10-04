from abc import ABC, abstractmethod
from typing import Any
from ..graph.backend import GraphBackend


class GraphAnalyzer(ABC):
    """
    Abstract base protocol for any graph analytics algorithm in SupplyChainLens.
    Allows independent implementation and registration of metrics.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier name for this analyzer (e.g., 'pagerank', 'betweenness')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable explanation of what this analyzer calculates."""
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        """Category: 'centrality', 'structural', 'dependency', or 'cycles'."""
        pass

    @abstractmethod
    def analyze(self, graph: GraphBackend, **kwargs) -> Any:
        """
        Executes the analysis algorithm on the given GraphBackend and returns a typed result.
        """
        pass
