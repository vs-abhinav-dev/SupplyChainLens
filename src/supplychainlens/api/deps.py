import os
from typing import Dict, Optional
from ..analytics import AnalyticsRegistry, default_registry
from ..graph import GraphQueryService, GraphRepository

_repositories: Dict[str, GraphRepository] = {}
_query_services: Dict[str, GraphQueryService] = {}


def get_repository(
    backend: Optional[str] = None,
    curated_dir: str = "data/curated/npm",
) -> GraphRepository:
    """
    Returns a cached GraphRepository instance for the given backend.
    Loads data on initial request.
    """
    b_key = (backend or os.environ.get("GRAPH_BACKEND", "igraph")).lower().strip()
    if b_key not in ("networkx", "igraph"):
        b_key = "igraph"

    if b_key not in _repositories:
        repo = GraphRepository(curated_dir=curated_dir, backend=b_key)
        repo.load()
        _repositories[b_key] = repo

    return _repositories[b_key]


def get_query_service(backend: Optional[str] = None) -> GraphQueryService:
    """
    Returns a GraphQueryService wrapping the requested backend repository.
    """
    b_key = (backend or os.environ.get("GRAPH_BACKEND", "igraph")).lower().strip()
    if b_key not in ("networkx", "igraph"):
        b_key = "igraph"

    if b_key not in _query_services:
        repo = get_repository(backend=b_key)
        _query_services[b_key] = GraphQueryService(repository=repo)

    return _query_services[b_key]


def get_analytics_registry() -> AnalyticsRegistry:
    """
    Returns the central analytics registry with pre-registered algorithms.
    """
    return default_registry
