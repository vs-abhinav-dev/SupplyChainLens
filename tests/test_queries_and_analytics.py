import pytest
from supplychainlens.graph import (
    Node,
    Edge,
    NetworkXBackend,
    IGraphBackend,
    GraphRepository,
    GraphQueryService,
    create_graph,
)
from supplychainlens.analytics import (
    GraphAnalyzer,
    AnalyticsRegistry,
    DegreeAnalyzer,
    PageRankAnalyzer,
    BetweennessAnalyzer,
    ComponentsAnalyzer,
    CyclesAnalyzer,
    DependencyDepthAnalyzer,
    default_registry,
)


@pytest.fixture
def sample_graph():
    """Build a sample dependency graph for query and analytics tests."""
    g = create_graph("networkx")
    # Topology:
    # A -> B -> C -> D
    # A -> C
    # E -> F -> E (cycle)
    # Isolated
    nodes = [
        Node("npm:A@1.0.0", "npm:A", "A", "1.0.0"),
        Node("npm:B@1.0.0", "npm:B", "B", "1.0.0"),
        Node("npm:C@1.0.0", "npm:C", "C", "1.0.0"),
        Node("npm:D@1.0.0", "npm:D", "D", "1.0.0"),
        Node("npm:E@1.0.0", "npm:E", "E", "1.0.0"),
        Node("npm:F@1.0.0", "npm:F", "F", "1.0.0"),
        Node("npm:Isolated@1.0.0", "npm:Isolated", "Isolated", "1.0.0"),
    ]
    for n in nodes:
        g.add_node(n)

    g.add_edge(Edge("npm:A@1.0.0", "npm:B@1.0.0", "^1.0.0"))
    g.add_edge(Edge("npm:B@1.0.0", "npm:C@1.0.0", "^1.0.0"))
    g.add_edge(Edge("npm:C@1.0.0", "npm:D@1.0.0", "^1.0.0"))
    g.add_edge(Edge("npm:A@1.0.0", "npm:C@1.0.0", "^1.0.0"))
    g.add_edge(Edge("npm:E@1.0.0", "npm:F@1.0.0", "^1.0.0"))
    g.add_edge(Edge("npm:F@1.0.0", "npm:E@1.0.0", "^1.0.0"))

    return g


# ==========================================
# GraphQueryService Tests
# ==========================================

def test_query_neighborhood(sample_graph):
    queries = GraphQueryService(graph=sample_graph)

    # Depth 1 dependencies from A -> should include B and C
    sub1 = queries.get_dependencies("npm:A@1.0.0", depth=1)
    assert sub1 is not None
    assert sub1.root_id == "npm:A@1.0.0"
    node_ids = {n["id"] for n in sub1.nodes}
    assert node_ids == {"npm:A@1.0.0", "npm:B@1.0.0", "npm:C@1.0.0"}

    # Depth 2 dependencies from A -> should include B, C, D
    sub2 = queries.get_dependencies("npm:A@1.0.0", depth=2)
    assert sub2 is not None
    node_ids2 = {n["id"] for n in sub2.nodes}
    assert node_ids2 == {"npm:A@1.0.0", "npm:B@1.0.0", "npm:C@1.0.0", "npm:D@1.0.0"}

    # Dependents of C -> should include A and B
    sub_dep = queries.get_dependents("npm:C@1.0.0", depth=1)
    assert sub_dep is not None
    dep_node_ids = {n["id"] for n in sub_dep.nodes}
    assert dep_node_ids == {"npm:A@1.0.0", "npm:B@1.0.0", "npm:C@1.0.0"}


def test_query_pathfinding(sample_graph):
    queries = GraphQueryService(graph=sample_graph)

    # Path from A to D: A -> C -> D (length 2) or A -> B -> C -> D
    path_res = queries.find_path("npm:A@1.0.0", "npm:D@1.0.0")
    assert path_res is not None
    assert path_res.source_node_id == "npm:A@1.0.0"
    assert path_res.target_node_id == "npm:D@1.0.0"
    assert path_res.path[0] == "npm:A@1.0.0"
    assert path_res.path[-1] == "npm:D@1.0.0"
    assert len(path_res.nodes) == len(path_res.path)
    assert len(path_res.edges) == len(path_res.path) - 1

    # Unreachable path: D to A
    assert queries.find_path("npm:D@1.0.0", "npm:A@1.0.0") is None

    # Unreachable path to isolated
    assert queries.find_path("npm:A@1.0.0", "npm:Isolated@1.0.0") is None


def test_query_reachability(sample_graph):
    queries = GraphQueryService(graph=sample_graph)

    # Reachability from A (dependencies)
    reach = queries.get_reachability("npm:A@1.0.0", direction="dependencies")
    assert reach == {"npm:B@1.0.0", "npm:C@1.0.0", "npm:D@1.0.0"}

    # Upstream blast radius of D (dependents)
    blast_radius = queries.get_reachability("npm:D@1.0.0", direction="dependents")
    assert blast_radius == {"npm:A@1.0.0", "npm:B@1.0.0", "npm:C@1.0.0"}


# ==========================================
# Analytics Analyzers Tests
# ==========================================

def test_degree_analyzer(sample_graph):
    analyzer = DegreeAnalyzer()
    res = analyzer.analyze(sample_graph)

    assert res.total_nodes == 7
    assert res.total_edges == 6
    assert res.density > 0.0
    assert len(res.top_fan_in) > 0
    assert len(res.top_fan_out) > 0
    # C is depended on by A and B, so its fan-in should be 2
    top_in_ids = [item.node_id for item in res.top_fan_in]
    assert "npm:C@1.0.0" in top_in_ids


def test_pagerank_analyzer(sample_graph):
    analyzer = PageRankAnalyzer()
    res = analyzer.analyze(sample_graph)

    assert res.metric == "pagerank"
    assert res.total_nodes == 7
    assert len(res.rankings) == 7
    assert res.summary["max"] >= res.summary["min"]


def test_betweenness_analyzer(sample_graph):
    analyzer = BetweennessAnalyzer()
    res = analyzer.analyze(sample_graph)

    assert res.metric == "betweenness"
    assert res.total_nodes == 7
    assert len(res.rankings) > 0


def test_components_analyzer(sample_graph):
    analyzer = ComponentsAnalyzer()
    # Weak components
    res_weak = analyzer.analyze(sample_graph, mode="weak")
    assert res_weak.component_type == "weak"
    assert res_weak.total_components == 3  # (A-B-C-D), (E-F), (Isolated)

    # Strong components
    res_strong = analyzer.analyze(sample_graph, mode="strong")
    assert res_strong.component_type == "strong"
    # E and F form a strong component of size 2
    assert res_strong.max_component_size == 2


def test_cycles_analyzer(sample_graph):
    analyzer = CyclesAnalyzer()
    res = analyzer.analyze(sample_graph)

    assert res.has_cycles is True
    assert res.total_cycles == 1
    cycle_nodes = set(res.cycles[0].cycle)
    assert "npm:E@1.0.0" in cycle_nodes
    assert "npm:F@1.0.0" in cycle_nodes


def test_dependency_depth_analyzer(sample_graph):
    analyzer = DependencyDepthAnalyzer()
    res = analyzer.analyze(sample_graph)

    assert res.max_depth == 3  # A -> B -> C -> D is 3 hops
    assert len(res.deepest_nodes) > 0
    assert res.deepest_nodes[0].node_id == "npm:A@1.0.0"
    assert res.deepest_nodes[0].score == 3.0


# ==========================================
# AnalyticsRegistry & Extensibility Tests
# ==========================================

def test_analytics_registry(sample_graph):
    reg = AnalyticsRegistry()
    reg.register(DegreeAnalyzer())
    reg.register(PageRankAnalyzer())

    available = reg.list_analyzers()
    names = [a["name"] for a in available]
    assert "degree" in names
    assert "pagerank" in names

    # Execute via registry
    res_degree = reg.run("degree", sample_graph)
    assert res_degree.total_nodes == 7

    # Cached execution
    res_cached = reg.run("degree", sample_graph, use_cache=True)
    assert res_cached is res_degree

    # Non-cached execution
    res_fresh = reg.run("degree", sample_graph, use_cache=False)
    assert res_fresh.total_nodes == 7


def test_custom_analyzer_extensibility(sample_graph):
    """Verify that a future developer can easily add a custom algorithm without modifying core."""
    class CustomClusteringCoefficient(GraphAnalyzer):
        @property
        def name(self) -> str:
            return "my_custom_metric"

        @property
        def description(self) -> str:
            return "Custom test algorithm"

        @property
        def category(self) -> str:
            return "experimental"

        def analyze(self, graph, **kwargs):
            return {"custom_score": 42, "node_count": graph.node_count()}

    reg = AnalyticsRegistry()
    reg.register(CustomClusteringCoefficient())

    assert reg.get("my_custom_metric") is not None
    out = reg.run("my_custom_metric", sample_graph)
    assert out["custom_score"] == 42
    assert out["node_count"] == 7
