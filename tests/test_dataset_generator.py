import json
from pathlib import Path
import pytest
from supplychainlens.generator import NPMDatasetGenerator
from supplychainlens.resolver import DependencyResolver


class MockFetcher:
    def __init__(self, packuments=None):
        self.packuments = packuments or {}

    def fetch_packument(self, package_name: str):
        return self.packuments.get(package_name)


@pytest.fixture
def mock_npm_dataset():
    pkg_a = {
        "name": "pkg-a",
        "time": {"1.0.0": "2023-01-01T00:00:00.000Z"},
        "versions": {
            "1.0.0": {
                "name": "pkg-a",
                "version": "1.0.0",
                "dependencies": {"pkg-b": "^1.0.0"},
            }
        },
    }
    pkg_b = {
        "name": "pkg-b",
        "time": {"1.0.0": "2023-01-01T00:00:00.000Z"},
        "versions": {
            "1.0.0": {
                "name": "pkg-b",
                "version": "1.0.0",
                "dependencies": {"pkg-c": "^1.0.0"},
            }
        },
    }
    pkg_c = {
        "name": "pkg-c",
        "time": {"1.0.0": "2023-01-01T00:00:00.000Z"},
        "versions": {
            "1.0.0": {
                "name": "pkg-c",
                "version": "1.0.0",
                "dependencies": {},
            }
        },
    }
    return {"pkg-a": pkg_a, "pkg-b": pkg_b, "pkg-c": pkg_c}


def test_recursive_dataset_generation(tmp_path, mock_npm_dataset):
    fetcher = MockFetcher(mock_npm_dataset)
    resolver = DependencyResolver(fetcher=fetcher)
    generator = NPMDatasetGenerator(fetcher=fetcher, resolver=resolver)

    output_dir = tmp_path / "staging"
    stats = generator.generate_dataset(
        seeds=["pkg-a"],
        target_nodes=10,
        output_dir=output_dir,
    )

    assert stats["discovered_packages"] == 3
    assert stats["package_versions"] == 3
    assert stats["dependency_records"] == 2
    assert stats["resolved_edges"] == 2

    # Check files exist and are non-empty
    for fname in ["packages.jsonl", "package_versions.jsonl", "dependencies.jsonl", "resolved_dependencies.jsonl"]:
        fpath = output_dir / fname
        assert fpath.exists()
        lines = fpath.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) > 0


def test_target_nodes_limit_enforcement(tmp_path, mock_npm_dataset):
    fetcher = MockFetcher(mock_npm_dataset)
    resolver = DependencyResolver(fetcher=fetcher)
    generator = NPMDatasetGenerator(fetcher=fetcher, resolver=resolver)

    output_dir = tmp_path / "staging_limited"
    stats = generator.generate_dataset(
        seeds=["pkg-a"],
        target_nodes=1,
        output_dir=output_dir,
    )

    # With target_nodes=1, only pkg-a should be visited
    assert stats["discovered_packages"] == 1


def test_reproducibility_with_seed(tmp_path, mock_npm_dataset):
    fetcher = MockFetcher(mock_npm_dataset)
    resolver = DependencyResolver(fetcher=fetcher)
    generator = NPMDatasetGenerator(fetcher=fetcher, resolver=resolver)

    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"

    stats1 = generator.generate_dataset(seeds=["pkg-a"], seed=42, output_dir=out1)
    stats2 = generator.generate_dataset(seeds=["pkg-a"], seed=42, output_dir=out2)

    assert stats1 == stats2
    assert (out1 / "resolved_dependencies.jsonl").read_text() == (out2 / "resolved_dependencies.jsonl").read_text()
