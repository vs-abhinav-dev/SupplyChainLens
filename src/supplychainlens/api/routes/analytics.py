from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from ..deps import get_analytics_registry, get_repository
from ..schemas import AnalyzerMetaResponse

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("", response_model=List[AnalyzerMetaResponse])
def list_analytics():
    """List all registered and discoverable graph analytics algorithms."""
    registry = get_analytics_registry()
    return [AnalyzerMetaResponse(**m) for m in registry.list_analyzers()]


@router.get("/{algorithm}")
def run_analytic_algorithm(
    algorithm: str,
    backend: Optional[str] = Query(None, description="Graph backend: 'igraph' or 'networkx'"),
    use_cache: bool = Query(True, description="Whether to return cached calculations if available"),
    top_n: int = Query(50, ge=1, le=500, description="Top N ranked elements to return"),
    damping: float = Query(0.85, ge=0.0, le=1.0, description="Damping factor for PageRank"),
    mode: str = Query("weak", description="Component mode: 'weak' or 'strong'"),
):
    """
    Execute or retrieve cached results for a specified graph analytics algorithm.
    """
    registry = get_analytics_registry()
    analyzer = registry.get(algorithm)
    if not analyzer:
        available = [a["name"] for a in registry.list_analyzers()]
        raise HTTPException(
            status_code=404,
            detail=f"Algorithm '{algorithm}' not found. Available algorithms: {available}",
        )

    repo = get_repository(backend=backend)
    graph = repo.get_graph()

    kwargs: Dict[str, Any] = {"top_n": top_n}
    if algorithm.lower() == "pagerank":
        kwargs["damping"] = damping
    elif algorithm.lower() == "components":
        kwargs["mode"] = mode

    result = registry.run(algorithm, graph, use_cache=use_cache, **kwargs)

    # If result is a Pydantic model, dump to dict
    if hasattr(result, "model_dump"):
        return result.model_dump()

    return result
