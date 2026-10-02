import sys
from pathlib import Path

# Add project root directory to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from scripts.run_pipeline import run_pipeline


def test_end_to_end_pipeline(tmp_path):
    staging_dir = tmp_path / "staging_npm"
    curated_dir = tmp_path / "curated_npm"

    results = run_pipeline(
        seeds=["express", "react"],
        target_nodes=10,
        seed=42,
        staging_dir=str(staging_dir),
        curated_dir=str(curated_dir),
    )

    # 1. Verify staging JSONL files exist
    assert (staging_dir / "packages.jsonl").exists()
    assert (staging_dir / "package_versions.jsonl").exists()
    assert (staging_dir / "dependencies.jsonl").exists()
    assert (staging_dir / "resolved_dependencies.jsonl").exists()

    # 2. Verify curated Parquet directories exist
    assert (curated_dir / "packages").exists()
    assert (curated_dir / "package_versions").exists()
    assert (curated_dir / "dependencies").exists()
    assert (curated_dir / "resolved_dependencies").exists()

    # 3. Verify VersionGraph properties
    graph = results["graph"]
    assert graph.node_count() > 0
    assert graph.edge_count() > 0
    assert len(graph.validate()) == 0
