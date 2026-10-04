import os
from typing import Optional
from .backend import GraphBackend
from .backends.igraph_backend import IGraphBackend
from .backends.networkx_backend import NetworkXBackend


def create_graph(backend: Optional[str] = None) -> GraphBackend:
    """
    Factory function to instantiate a GraphBackend.
    If backend is None, inspects GRAPH_BACKEND environment variable.
    Defaults to 'igraph' for high performance, or 'networkx'.
    """
    chosen = backend or os.environ.get("GRAPH_BACKEND", "igraph")
    chosen = chosen.strip().lower()

    if chosen == "networkx":
        return NetworkXBackend()
    elif chosen == "igraph":
        return IGraphBackend()
    else:
        raise ValueError(
            f"Unsupported graph backend: '{chosen}'. Must be 'networkx' or 'igraph'."
        )
