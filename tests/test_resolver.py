import pytest
from datetime import datetime
from supplychainlens.models import ResolutionStatus
from supplychainlens.resolver import DependencyResolver


class MockFetcher:
    """Mock fetcher for offline unit testing."""

    def __init__(self, packuments=None):
        self.packuments = packuments or {}

    def fetch_packument(self, package_name: str):
        return self.packuments.get(package_name)


def test_1_caret_constraint_latest_satisfying():
    packument_lodash = {
        "name": "lodash",
        "time": {
            "4.17.19": "2020-01-01T00:00:00.000Z",
            "4.17.20": "2020-02-01T00:00:00.000Z",
            "4.17.21": "2021-01-01T00:00:00.000Z",
            "5.0.0": "2022-01-01T00:00:00.000Z",
        },
        "versions": {
            "4.17.19": {"name": "lodash", "version": "4.17.19"},
            "4.17.20": {"name": "lodash", "version": "4.17.20"},
            "4.17.21": {"name": "lodash", "version": "4.17.21"},
            "5.0.0": {"name": "lodash", "version": "5.0.0"},
        },
    }
    resolver = DependencyResolver(fetcher=MockFetcher({"lodash": packument_lodash}))

    res = resolver.resolve_dependency(
        source_node_id="npm:test-pkg@1.0.0",
        target_package="lodash",
        version_constraint="^4.17.0",
        source_date="2023-01-01T00:00:00.000Z",
    )

    assert res.resolution_status == ResolutionStatus.RESOLVED
    assert res.resolved_node_id == "npm:lodash@4.17.21"


def test_2_range_constraint_latest_2_x():
    packument_body_parser = {
        "name": "body-parser",
        "time": {
            "1.19.0": "2019-01-01T00:00:00.000Z",
            "2.0.0": "2021-01-01T00:00:00.000Z",
            "2.2.0": "2022-01-01T00:00:00.000Z",
            "3.0.0": "2023-01-01T00:00:00.000Z",
        },
        "versions": {
            "1.19.0": {"name": "body-parser", "version": "1.19.0"},
            "2.0.0": {"name": "body-parser", "version": "2.0.0"},
            "2.2.0": {"name": "body-parser", "version": "2.2.0"},
            "3.0.0": {"name": "body-parser", "version": "3.0.0"},
        },
    }
    resolver = DependencyResolver(fetcher=MockFetcher({"body-parser": packument_body_parser}))

    res = resolver.resolve_dependency(
        source_node_id="npm:express@5.0.0",
        target_package="body-parser",
        version_constraint=">=2,<3",
        source_date="2024-01-01T00:00:00.000Z",
    )

    assert res.resolution_status == ResolutionStatus.RESOLVED
    assert res.resolved_node_id == "npm:body-parser@2.2.0"


def test_3_publish_date_rule_cutoff():
    """
    Source: A@1.0 published 2024-01-01
    Target B versions:
      B@2.0 -> 2023-01-01
      B@2.1 -> 2023-06-01
      B@2.2 -> 2024-02-01 (published AFTER source)
    Constraint: ^2.0.0
    Must pick B@2.1, not B@2.2!
    """
    packument_b = {
        "name": "B",
        "time": {
            "2.0.0": "2023-01-01T00:00:00.000Z",
            "2.1.0": "2023-06-01T00:00:00.000Z",
            "2.2.0": "2024-02-01T00:00:00.000Z",
        },
        "versions": {
            "2.0.0": {"name": "B", "version": "2.0.0"},
            "2.1.0": {"name": "B", "version": "2.1.0"},
            "2.2.0": {"name": "B", "version": "2.2.0"},
        },
    }
    resolver = DependencyResolver(fetcher=MockFetcher({"B": packument_b}))

    res = resolver.resolve_dependency(
        source_node_id="npm:A@1.0.0",
        target_package="B",
        version_constraint="^2.0.0",
        source_date="2024-01-01T00:00:00.000Z",
    )

    assert res.resolution_status == ResolutionStatus.RESOLVED
    assert res.resolved_node_id == "npm:B@2.1.0"


def test_4_git_dependency_non_registry():
    resolver = DependencyResolver(fetcher=MockFetcher({}))

    git_constraints = [
        "git+https://github.com/foo/bar.git#v1.0.0",
        "https://github.com/foo/bar/tarball/v1.0.0",
        "github:foo/bar",
        "file:../local-pkg",
    ]

    for c in git_constraints:
        res = resolver.resolve_dependency(
            source_node_id="npm:my-app@1.0.0",
            target_package="bar",
            version_constraint=c,
            source_date="2024-01-01T00:00:00.000Z",
        )
        assert res.resolution_status == ResolutionStatus.NON_REGISTRY
        assert res.resolved_node_id is None


def test_5_invalid_constraint():
    resolver = DependencyResolver(fetcher=MockFetcher({}))

    invalid_constraints = [
        "invalid constraint syntax",
        "foo-bar-baz",
        ">= not_a_version",
    ]

    for c in invalid_constraints:
        res = resolver.resolve_dependency(
            source_node_id="npm:my-app@1.0.0",
            target_package="some-pkg",
            version_constraint=c,
            source_date="2024-01-01T00:00:00.000Z",
        )
        assert res.resolution_status == ResolutionStatus.INVALID_CONSTRAINT
        assert res.resolved_node_id is None


def test_6_no_satisfying_version():
    packument_c = {
        "name": "C",
        "time": {
            "1.0.0": "2020-01-01T00:00:00.000Z",
            "1.1.0": "2021-01-01T00:00:00.000Z",
        },
        "versions": {
            "1.0.0": {"name": "C", "version": "1.0.0"},
            "1.1.0": {"name": "C", "version": "1.1.0"},
        },
    }
    resolver = DependencyResolver(fetcher=MockFetcher({"C": packument_c}))

    res = resolver.resolve_dependency(
        source_node_id="npm:my-app@1.0.0",
        target_package="C",
        version_constraint="^2.0.0",
        source_date="2024-01-01T00:00:00.000Z",
    )

    assert res.resolution_status == ResolutionStatus.NO_SATISFYING_VERSION
    assert res.resolved_node_id is None


def test_7_package_missing():
    resolver = DependencyResolver(fetcher=MockFetcher({}))

    res = resolver.resolve_dependency(
        source_node_id="npm:my-app@1.0.0",
        target_package="non-existent-package-xyz-12345",
        version_constraint="^1.0.0",
        source_date="2024-01-01T00:00:00.000Z",
    )

    assert res.resolution_status == ResolutionStatus.PACKAGE_MISSING
    assert res.resolved_node_id is None
