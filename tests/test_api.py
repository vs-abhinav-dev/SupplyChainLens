import pytest
from fastapi.testclient import TestClient
from supplychainlens.api.app import app

client = TestClient(app)


def test_health_and_root():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "supplychainlens"}

    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "docs" in res_root.json()


def test_packages_endpoints():
    # List packages
    res = client.get("/api/packages?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 50
    assert len(data["packages"]) == 10
    assert "express" in client.get("/api/packages?q=express").json()["packages"]

    # Package metadata
    res_pkg = client.get("/api/packages/express")
    assert res_pkg.status_code == 200
    pkg_data = res_pkg.json()
    assert pkg_data["name"] == "express"
    assert pkg_data["total_versions"] > 0
    assert len(pkg_data["versions"]) > 0

    # Non-existent package
    assert client.get("/api/packages/non-existent-package-xyz").status_code == 404

    # Package dependencies
    res_deps = client.get("/api/packages/express/dependencies?depth=1")
    assert res_deps.status_code == 200
    deps_data = res_deps.json()
    assert deps_data["total_nodes"] > 1
    assert len(deps_data["edges"]) > 0

    # Package dependents
    res_dependents = client.get("/api/packages/lodash/dependents?depth=1")
    assert res_dependents.status_code == 200
    assert res_dependents.json()["total_nodes"] > 0

    # Package reachability
    res_reach = client.get("/api/packages/express/reachability?direction=dependencies")
    assert res_reach.status_code == 200
    assert res_reach.json()["total_reachable"] > 0


def test_graph_endpoints():
    # Graph overall stats
    res_stats = client.get("/api/graph")
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["node_count"] == 5912
    assert stats["edge_count"] == 10072
    assert stats["boundary_edge_count"] == 59628
    assert stats["backend"] in ("igraph", "networkx")

    # Local subgraph around express
    res_sub = client.get("/api/graph/express?depth=2&direction=dependencies")
    assert res_sub.status_code == 200
    sub_data = res_sub.json()
    assert sub_data["root_id"].startswith("npm:express@")
    assert sub_data["total_nodes"] > 1
    assert sub_data["total_edges"] > 0

    # Path finding
    res_path = client.get("/api/graph/path?source=npm:express@4.18.0&target=npm:debug@2.6.9")
    assert res_path.status_code == 200
    path_data = res_path.json()
    assert path_data["found"] is True
    assert path_data["length"] == 1
    assert path_data["path"] == ["npm:express@4.18.0", "npm:debug@2.6.9"]


def test_analytics_endpoints():
    # List available analyzers
    res_list = client.get("/api/analytics")
    assert res_list.status_code == 200
    analyzers = res_list.json()
    names = [a["name"] for a in analyzers]
    assert "degree" in names
    assert "pagerank" in names
    assert "betweenness" in names
    assert "components" in names
    assert "cycles" in names
    assert "dependency_depth" in names

    # Run degree
    res_deg = client.get("/api/analytics/degree?top_n=10")
    assert res_deg.status_code == 200
    deg_data = res_deg.json()
    assert deg_data["total_nodes"] == 5912
    assert len(deg_data["top_fan_in"]) == 10

    # Run PageRank
    res_pr = client.get("/api/analytics/pagerank?top_n=5")
    assert res_pr.status_code == 200
    pr_data = res_pr.json()
    assert pr_data["metric"] == "pagerank"
    assert len(pr_data["rankings"]) == 5

    # Run Betweenness
    res_bet = client.get("/api/analytics/betweenness?top_n=5")
    assert res_bet.status_code == 200
    assert len(res_bet.json()["rankings"]) == 5

    # Run Components
    res_comp = client.get("/api/analytics/components?mode=weak")
    assert res_comp.status_code == 200
    assert res_comp.json()["total_components"] > 0

    # Run Cycles
    res_cyc = client.get("/api/analytics/cycles")
    assert res_cyc.status_code == 200
    assert "has_cycles" in res_cyc.json()

    # Run Dependency Depth
    res_depth = client.get("/api/analytics/dependency_depth?top_n=5")
    assert res_depth.status_code == 200
    assert res_depth.json()["max_depth"] > 0

    # 404 on unknown algorithm
    assert client.get("/api/analytics/unknown_algorithm_xyz").status_code == 404
