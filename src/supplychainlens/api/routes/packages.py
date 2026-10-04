from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from ..deps import get_query_service, get_repository
from ..schemas import (
    PackageListResponse,
    PackageSummaryResponse,
    ReachabilityResponse,
    SubgraphResponse,
)

router = APIRouter(prefix="/api/packages", tags=["packages"])


@router.get("", response_model=PackageListResponse)
def list_packages(
    q: Optional[str] = Query(None, description="Optional search filter for package name"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    backend: Optional[str] = Query(None, description="Graph backend: 'igraph' or 'networkx'"),
):
    repo = get_repository(backend=backend)
    all_pkgs = repo.list_packages()

    if q:
        q_clean = q.lower().strip()
        all_pkgs = [p for p in all_pkgs if q_clean in p.lower()]

    paginated = all_pkgs[offset : offset + limit]
    return PackageListResponse(total=len(all_pkgs), packages=paginated)


@router.get("/{package}", response_model=PackageSummaryResponse)
def get_package(
    package: str,
    backend: Optional[str] = Query(None),
):
    repo = get_repository(backend=backend)
    summary = repo.get_package(package)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Package '{package}' not found in repository.")
    return PackageSummaryResponse(**summary)


@router.get("/{package}/dependencies", response_model=SubgraphResponse)
def get_package_dependencies(
    package: str,
    depth: int = Query(1, ge=1, le=5),
    max_nodes: int = Query(150, ge=1, le=500),
    backend: Optional[str] = Query(None),
):
    service = get_query_service(backend=backend)
    sub = service.get_dependencies(package, depth=depth, max_nodes=max_nodes)
    if not sub:
        raise HTTPException(status_code=404, detail=f"Package '{package}' not found in graph.")
    return SubgraphResponse(
        root_id=sub.root_id,
        depth=sub.depth,
        direction=sub.direction,
        nodes=sub.nodes,
        edges=sub.edges,
        total_nodes=sub.total_nodes,
        total_edges=sub.total_edges,
        truncated=sub.truncated,
    )


@router.get("/{package}/dependents", response_model=SubgraphResponse)
def get_package_dependents(
    package: str,
    depth: int = Query(1, ge=1, le=5),
    max_nodes: int = Query(150, ge=1, le=500),
    backend: Optional[str] = Query(None),
):
    service = get_query_service(backend=backend)
    sub = service.get_dependents(package, depth=depth, max_nodes=max_nodes)
    if not sub:
        raise HTTPException(status_code=404, detail=f"Package '{package}' not found in graph.")
    return SubgraphResponse(
        root_id=sub.root_id,
        depth=sub.depth,
        direction=sub.direction,
        nodes=sub.nodes,
        edges=sub.edges,
        total_nodes=sub.total_nodes,
        total_edges=sub.total_edges,
        truncated=sub.truncated,
    )


@router.get("/{package}/reachability", response_model=ReachabilityResponse)
def get_package_reachability(
    package: str,
    direction: str = Query("dependencies", description="'dependencies' or 'dependents'"),
    backend: Optional[str] = Query(None),
):
    service = get_query_service(backend=backend)
    root_id = service.resolve_node_id(package)
    if not root_id:
        raise HTTPException(status_code=404, detail=f"Package '{package}' not found in graph.")

    reachable = sorted(list(service.get_reachability(package, direction=direction)))
    return ReachabilityResponse(
        root_id=root_id,
        direction=direction,
        total_reachable=len(reachable),
        reachable_nodes=reachable,
    )
