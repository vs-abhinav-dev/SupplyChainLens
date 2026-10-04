import pytest
from supplychainlens.graph import (
    Node,
    Edge,
    NetworkXBackend,
    IGraphBackend,
    GraphRepository,
    create_graph,
)


@pytest.fixture(params=["networkx", "igraph"])
def backend_instance(request):
    """Parameterized fixture to run identical graph tests against both backends."""
    return create_graph(request.param)


def test_node_addition_and_retrieval(backend_instance):
    g = backend_instance
    n1 = Node(node_id="npm:A@1.0.0", package_id="npm:A", name="A", version="1.0.0", published_at="2024-01-01T00:00:00Z")
    n2 = Node(node_id="npm:B@2.0.0", package_id="npm:B", name="B", version="2.0.0", published_at="2024-01-02T00:00:00Z")

    g.add_node(n1)
    g.add_node(n2)

    assert g.node_count() == 2
    assert g.has_node("npm:A@1.0.0")
    assert g.has_node("npm:B@2.0.0")
    assert not g.has_node("npm:C@3.0.0")

    retrieved = g.get_node("npm:A@1.0.0")
    assert retrieved is not None
    assert retrieved.name == "A"
    assert retrieved.version == "1.0.0"


def test_edge_addition_and_boundary_handling(backend_instance):
    g = backend_instance
    n1 = Node(node_id="npm:A@1.0.0", package_id="npm:A", name="A", version="1.0.0")
    n2 = Node(node_id="npm:B@2.0.0", package_id="npm:B", name="B", version="2.0.0")
    g.add_node(n1)
    g.add_node(n2)

    # Valid internal edge
    e1 = Edge(source_node_id="npm:A@1.0.0", target_node_id="npm:B@2.0.0", version_constraint="^2.0.0", dependency_type="dependencies")
    assert g.add_edge(e1) is True
    assert g.edge_count() == 1
    assert g.has_edge("npm:A@1.0.0", "npm:B@2.0.0")
    assert not g.has_edge("npm:B@2.0.0", "npm:A@1.0.0")

    # Boundary edge (target node does not exist in graph)
    e_boundary = Edge(source_node_id="npm:A@1.0.0", target_node_id="npm:outside@1.0.0", version_constraint="^1.0.0")
    assert g.add_edge(e_boundary) is False
    assert g.edge_count() == 1
    assert g.boundary_edge_count() == 1

    b_records = g.boundary_edges()
    assert len(b_records) == 1
    assert b_records[0]["source_node_id"] == "npm:A@1.0.0"
    assert b_records[0]["target_node_id"] == "npm:outside@1.0.0"


def test_neighborhood_traversal_and_degree(backend_instance):
    g = backend_instance
    # Tree: root -> child1 -> grandchild, root -> child2
    root = Node(node_id="npm:root@1.0.0", package_id="npm:root", name="root", version="1.0.0")
    c1 = Node(node_id="npm:c1@1.0.0", package_id="npm:c1", name="c1", version="1.0.0")
    c2 = Node(node_id="npm:c2@1.0.0", package_id="npm:c2", name="c2", version="1.0.0")
    gc = Node(node_id="npm:gc@1.0.0", package_id="npm:gc", name="gc", version="1.0.0")

    for n in [root, c1, c2, gc]:
        g.add_node(n)

    g.add_edge(Edge(source_node_id="npm:root@1.0.0", target_node_id="npm:c1@1.0.0", version_constraint="^1.0.0"))
    g.add_edge(Edge(source_node_id="npm:root@1.0.0", target_node_id="npm:c2@1.0.0", version_constraint="^1.0.0"))
    g.add_edge(Edge(source_node_id="npm:c1@1.0.0", target_node_id="npm:gc@1.0.0", version_constraint="^1.0.0"))

    # Outgoing dependencies from root
    succs = {n.node_id for n in g.successors("npm:root@1.0.0")}
    assert succs == {"npm:c1@1.0.0", "npm:c2@1.0.0"}

    # Incoming dependents to c1
    preds = {n.node_id for n in g.predecessors("npm:c1@1.0.0")}
    assert preds == {"npm:root@1.0.0"}

    # Degrees
    assert g.out_degree("npm:root@1.0.0") == 2
    assert g.in_degree("npm:root@1.0.0") == 0
    assert g.degree("npm:root@1.0.0") == 2

    assert g.out_degree("npm:c1@1.0.0") == 1
    assert g.in_degree("npm:c1@1.0.0") == 1
    assert g.degree("npm:c1@1.0.0") == 2

    assert g.out_degree("npm:gc@1.0.0") == 0
    assert g.in_degree("npm:gc@1.0.0") == 1
    assert g.degree("npm:gc@1.0.0") == 1


def test_shortest_path_and_connectivity(backend_instance):
    g = backend_instance
    # Path: A -> B -> C -> D
    nodes = [
        Node(node_id=f"npm:{char}@1.0.0", package_id=f"npm:{char}", name=char, version="1.0.0")
        for char in ["A", "B", "C", "D", "Isolated"]
    ]
    for n in nodes:
        g.add_node(n)

    g.add_edge(Edge("npm:A@1.0.0", "npm:B@1.0.0", "^1.0.0"))
    g.add_edge(Edge("npm:B@1.0.0", "npm:C@1.0.0", "^1.0.0"))
    g.add_edge(Edge("npm:C@1.0.0", "npm:D@1.0.0", "^1.0.0"))

    # Direct path
    path = g.shortest_path("npm:A@1.0.0", "npm:D@1.0.0")
    assert path == ["npm:A@1.0.0", "npm:B@1.0.0", "npm:C@1.0.0", "npm:D@1.0.0"]

    # Reverse direction path should not exist in directed graph
    assert g.shortest_path("npm:D@1.0.0", "npm:A@1.0.0") is None

    # Path to isolated node
    assert g.shortest_path("npm:A@1.0.0", "npm:Isolated@1.0.0") is None

    # Connected components
    wcc = g.connected_components()
    assert len(wcc) == 2
    assert {"npm:A@1.0.0", "npm:B@1.0.0", "npm:C@1.0.0", "npm:D@1.0.0"} in wcc
    assert {"npm:Isolated@1.0.0"} in wcc


def test_strongly_connected_components_cycles(backend_instance):
    g = backend_instance
    # Cycle: X -> Y -> Z -> X
    for char in ["X", "Y", "Z"]:
        g.add_node(Node(node_id=f"npm:{char}@1.0.0", package_id=f"npm:{char}", name=char, version="1.0.0"))

    g.add_edge(Edge("npm:X@1.0.0", "npm:Y@1.0.0", "^1.0.0"))
    g.add_edge(Edge("npm:Y@1.0.0", "npm:Z@1.0.0", "^1.0.0"))
    g.add_edge(Edge("npm:Z@1.0.0", "npm:X@1.0.0", "^1.0.0"))

    scc = g.strongly_connected_components()
    assert len(scc) == 1
    assert scc[0] == {"npm:X@1.0.0", "npm:Y@1.0.0", "npm:Z@1.0.0"}


def test_subgraph_extraction(backend_instance):
    g = backend_instance
    for char in ["A", "B", "C", "D"]:
        g.add_node(Node(node_id=f"npm:{char}@1.0.0", package_id=f"npm:{char}", name=char, version="1.0.0"))

    g.add_edge(Edge("npm:A@1.0.0", "npm:B@1.0.0", "^1.0.0"))
    g.add_edge(Edge("npm:B@1.0.0", "npm:C@1.0.0", "^1.0.0"))
    g.add_edge(Edge("npm:C@1.0.0", "npm:D@1.0.0", "^1.0.0"))

    sub = g.get_subgraph(["npm:A@1.0.0", "npm:B@1.0.0"])
    assert sub.node_count() == 2
    assert sub.edge_count() == 1
    assert sub.has_edge("npm:A@1.0.0", "npm:B@1.0.0")
    assert not sub.has_node("npm:C@1.0.0")


def test_exact_parity_between_networkx_and_igraph():
    """Verify that NetworkXBackend and IGraphBackend produce identical results on the same graph."""
    nx_b = NetworkXBackend()
    ig_b = IGraphBackend()

    # Build complex test topology
    nodes = [
        Node(node_id=f"npm:pkg{i}@1.0.0", package_id=f"npm:pkg{i}", name=f"pkg{i}", version="1.0.0")
        for i in range(10)
    ]
    for n in nodes:
        nx_b.add_node(n)
        ig_b.add_node(n)

    edges = [
        Edge("npm:pkg0@1.0.0", "npm:pkg1@1.0.0", "^1.0.0"),
        Edge("npm:pkg1@1.0.0", "npm:pkg2@1.0.0", "^1.0.0"),
        Edge("npm:pkg2@1.0.0", "npm:pkg0@1.0.0", "^1.0.0"), # cycle 0-1-2
        Edge("npm:pkg2@1.0.0", "npm:pkg3@1.0.0", "^1.0.0"),
        Edge("npm:pkg3@1.0.0", "npm:pkg4@1.0.0", "^1.0.0"),
        Edge("npm:pkg5@1.0.0", "npm:pkg6@1.0.0", "^1.0.0"),
        Edge("npm:pkg0@1.0.0", "npm:outside@1.0.0", "^1.0.0"), # boundary
    ]
    for e in edges:
        nx_b.add_edge(e)
        ig_b.add_edge(e)

    assert nx_b.node_count() == ig_b.node_count()
    assert nx_b.edge_count() == ig_b.edge_count()
    assert nx_b.boundary_edge_count() == ig_b.boundary_edge_count()

    for n in nodes:
        nid = n.node_id
        assert nx_b.in_degree(nid) == ig_b.in_degree(nid)
        assert nx_b.out_degree(nid) == ig_b.out_degree(nid)
        assert nx_b.degree(nid) == ig_b.degree(nid)
        assert {s.node_id for s in nx_b.successors(nid)} == {s.node_id for s in ig_b.successors(nid)}
        assert {p.node_id for p in nx_b.predecessors(nid)} == {p.node_id for p in ig_b.predecessors(nid)}

    assert nx_b.shortest_path("npm:pkg0@1.0.0", "npm:pkg4@1.0.0") == ig_b.shortest_path("npm:pkg0@1.0.0", "npm:pkg4@1.0.0")
    assert nx_b.connected_components() == ig_b.connected_components()
    assert nx_b.strongly_connected_components() == ig_b.strongly_connected_components()


def test_graph_repository_pyarrow_loading():
    """Verify GraphRepository loads the curated dataset using fast PyArrow ingestion."""
    repo = GraphRepository(curated_dir="data/curated/npm", backend="igraph")
    graph = repo.load()

    assert graph.node_count() == 5912
    assert graph.edge_count() == 10072
    assert graph.boundary_edge_count() == 59628

    # Test package indexing methods
    packages = repo.list_packages()
    assert len(packages) >= 50
    assert "express" in packages
    assert "react" in packages

    express_pkg = repo.get_package("express")
    assert express_pkg is not None
    assert express_pkg["name"] == "express"
    assert express_pkg["total_versions"] > 0
    assert express_pkg["latest_version"] is not None

    versions = repo.get_package_versions("express")
    assert len(versions) == express_pkg["total_versions"]
    assert all(v.name == "express" for v in versions)

    latest = repo.get_latest_version("express")
    assert latest is not None
    assert latest.version == express_pkg["latest_version"]
