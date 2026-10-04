from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from ..deps import get_query_service, get_repository
from ..schemas import GraphNodeSchema, GraphStatsResponse, PathResponse, SubgraphResponse

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("", response_model=GraphStatsResponse)
def get_graph_stats(backend: Optional[str] = Query(None)):
    repo = get_repository(backend=backend)
    g = repo.get_graph()
    return GraphStatsResponse(
        backend=g.backend_name,
        node_count=g.node_count(),
        edge_count=g.edge_count(),
        boundary_edge_count=g.boundary_edge_count(),
        package_count=len(repo.list_packages()),
    )


@router.get("/path", response_model=PathResponse)
def find_graph_path(
    source: str = Query(..., description="Source package or version identifier"),
    target: str = Query(..., description="Target package or version identifier"),
    backend: Optional[str] = Query(None),
):
    service = get_query_service(backend=backend)
    res = service.find_path(source, target)
    if not res:
        return PathResponse(
            source=source,
            target=target,
            found=False,
            length=0,
            path=[],
            nodes=[],
            edges=[],
        )

    formatted_nodes = [
        GraphNodeSchema(
            id=n.node_id,
            label=f"{n.name}@{n.version}",
            name=n.name,
            version=n.version,
            package_id=n.package_id,
            published_at=n.published_at,
            is_root=(n.node_id == res.source_node_id),
            degree=service.graph.degree(n.node_id),
            in_degree=service.graph.in_degree(n.node_id),
            out_degree=service.graph.out_degree(n.node_id),
        )
        for n in res.nodes
    ]

    formatted_edges = [
        {
            "source": e.source_node_id,
            "target": e.target_node_id,
            "version_constraint": e.version_constraint,
            "dependency_type": e.dependency_type,
        }
        for e in res.edges
    ]

    return PathResponse(
        source=res.source_node_id,
        target=res.target_node_id,
        found=True,
        length=res.length,
        path=res.path,
        nodes=formatted_nodes,
        edges=formatted_edges,
    )


@router.get("/{package}", response_model=SubgraphResponse)
def get_package_neighborhood(
    package: str,
    depth: int = Query(1, ge=1, le=5),
    direction: str = Query("both", description="'both', 'dependencies', or 'dependents'"),
    max_nodes: int = Query(150, ge=1, le=500),
    backend: Optional[str] = Query(None),
):
    service = get_query_service(backend=backend)
    sub = service.get_neighborhood(package, depth=depth, direction=direction, max_nodes=max_nodes)
    if not sub:
        raise HTTPException(status_code=404, detail=f"Package or node '{package}' not found in graph.")

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
