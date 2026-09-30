import argparse
import sys
from pathlib import Path

# Add src to python path if needed
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from supplychainlens.generator import NPMDatasetGenerator


def main():
    parser = argparse.ArgumentParser(
        description="SupplyChainLens Phase 2 Dataset Generator - Large-Scale NPM Dependency Ingestion"
    )
    parser.add_argument(
        "--seeds",
        nargs="+",
        default=["express", "react", "lodash", "axios"],
        help="Seed package names for graph discovery (default: express react lodash axios)",
    )
    parser.add_argument(
        "--target-nodes",
        type=int,
        default=50,
        help="Maximum target package count for discovery limit (default: 50)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic discovery queue ordering (default: 42)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/staging/npm",
        help="Target directory for staging JSONL files (default: data/staging/npm)",
    )
    parser.add_argument(
        "--source-date",
        type=str,
        default=None,
        help="Optional ISO publication date cutoff for resolution",
    )

    args = parser.parse_args()

    generator = NPMDatasetGenerator()
    stats = generator.generate_dataset(
        seeds=args.seeds,
        target_nodes=args.target_nodes,
        seed=args.seed,
        output_dir=args.output_dir,
        source_date=args.source_date,
    )

    print("=" * 60)
    print(" SupplyChainLens Dataset Generator (Phase 2)")
    print("=" * 60)
    print(f"Discovered packages:       {stats['discovered_packages']:,}")
    print(f"Package versions:         {stats['package_versions']:,}")
    print(f"Dependency records:       {stats['dependency_records']:,}")
    print(f"Resolved edges:           {stats['resolved_edges']:,}")
    print(f"Unresolved:                {stats['unresolved_edges']:,}")
    print("\nResolution Breakdown:")
    for status_key, count in stats["resolution_breakdown"].items():
        print(f"  {status_key:<22} {count:,}")
    print("=" * 60)
    print(f"Staging dataset written to: {Path(args.output_dir).resolve()}")


if __name__ == "__main__":
    main()
