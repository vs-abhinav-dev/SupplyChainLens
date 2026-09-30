import pytest
from pyspark.sql import SparkSession

from supplychainlens.graph import (
    Node,
    Edge,
    VersionGraph,
    GraphLoader,
    render_ascii_subgraph,
)


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder
        .appName("SupplyChainLens Test Graph")
        .master("local[1]")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_node_and_edge_creation():
    n1 = Node(node_id="npm:A@1.0.0", package_id="npm:A", name="A", version="1.0.0", published_at="2024-01-01T00:00:00Z")
    n2 = Node(node_id="npm:B@2.0.0", package_id="npm:B", name="B", version="2.0.0", published_at="2024-01-02T00:00:00Z")
    e = Edge(source_node_id="npm:A@1.0.0", target_node_id="npm:B@2.0.0", version_constraint="^2.0.0", dependency_type="dependencies")

    assert n1.node_id == "npm:A@1.0.0"
    assert n2.version == "2.0.0"
    assert e.source_node_id == "npm:A@1.0.0"
    assert e.target_node_id == "npm:B@2.0.0"
    assert e.dependency_type == "dependencies"


def test_version_graph_operations():
    g = VersionGraph()

    n_express = Node(node_id="npm:express@4.18.0", package_id="npm:express", name="express", version="4.18.0")
    n_body_parser = Node(node_id="npm:body-parser@1.20.0", package_id="npm:body-parser", name="body-parser", version="1.20.0")
    n_bytes = Node(node_id="npm:bytes@3.1.2", package_id="npm:bytes", name="bytes", version="3.1.2")

    g.add_node(n_express)
    g.add_node(n_body_parser)
    g.add_node(n_bytes)

    assert g.node_count() == 3
    assert g.has_node("npm:express@4.18.0")
    assert not g.has_node("npm:unknown@1.0.0")

    e1 = Edge(source_node_id="npm:express@4.18.0", target_node_id="npm:body-parser@1.20.0", version_constraint="^1.20.0")
    e2 = Edge(source_node_id="npm:body-parser@1.20.0", target_node_id="npm:bytes@3.1.2", version_constraint="^3.1.2")

    assert g.add_edge(e1) is True
    assert g.add_edge(e2) is True
    assert g.edge_count() == 2

    # Check outgoing neighbors (dependencies)
    express_neighbors = g.get_neighbors("npm:express@4.18.0")
    assert len(express_neighbors) == 1
    assert express_neighbors[0].node_id == "npm:body-parser@1.20.0"

    # Check incoming dependents
    bytes_dependents = g.get_dependents("npm:bytes@3.1.2")
    assert len(bytes_dependents) == 1
    assert bytes_dependents[0].node_id == "npm:body-parser@1.20.0"

    # Check edge metadata retrieval
    fetched_e1 = g.get_edge("npm:express@4.18.0", "npm:body-parser@1.20.0")
    assert fetched_e1 is not None
    assert fetched_e1.version_constraint == "^1.20.0"

    # Validation check
    errors = g.validate()
    assert len(errors) == 0, f"Graph validation errors: {errors}"


def test_boundary_edge_handling():
    g = VersionGraph()
    n_source = Node(node_id="npm:app@1.0.0", package_id="npm:app", name="app", version="1.0.0")
    g.add_node(n_source)

    # Edge pointing to missing target
    e_boundary = Edge(source_node_id="npm:app@1.0.0", target_node_id="npm:outside-pkg@1.0.0", version_constraint="^1.0.0")

    added = g.add_edge(e_boundary)
    assert added is False
    assert g.edge_count() == 0
    assert g.boundary_edge_count() == 1

    b_edges = g.get_boundary_edges()
    assert b_edges[0]["source_node_id"] == "npm:app@1.0.0"
    assert b_edges[0]["target_node_id"] == "npm:outside-pkg@1.0.0"


def test_ascii_visualization():
    g = VersionGraph()
    n1 = Node(node_id="npm:express@4.18.0", package_id="npm:express", name="express", version="4.18.0")
    n2 = Node(node_id="npm:body-parser@1.20.0", package_id="npm:body-parser", name="body-parser", version="1.20.0")
    g.add_node(n1)
    g.add_node(n2)
    g.add_edge(Edge(source_node_id="npm:express@4.18.0", target_node_id="npm:body-parser@1.20.0", version_constraint="^1.20.0"))

    rendered = render_ascii_subgraph(g, "npm:express@4.18.0", max_depth=2)
    assert "express@4.18.0" in rendered
    assert "body-parser@1.20.0" in rendered
    assert "[^1.20.0]" in rendered


def test_graph_loader_integration(spark):
    loader = GraphLoader(spark=spark, curated_dir="data/curated/npm")
    graph = loader.load()

    # Check vertices
    assert graph.node_count() == 5912
    # Check edges exist
    assert graph.edge_count() > 0
    # Check boundary edges recorded
    assert graph.boundary_edge_count() > 0

    # Ensure graph invariants hold
    errors = graph.validate()
    assert len(errors) == 0, f"Graph validation failed: {errors}"
