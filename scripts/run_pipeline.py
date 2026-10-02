import sys
from pathlib import Path

# Add src directory to Python path if needed
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pyspark.sql import SparkSession

from supplychainlens.generator import NPMDatasetGenerator
from supplychainlens.etl.transform import NpmTransformer
from supplychainlens.etl.quality import DataQualityChecker
from supplychainlens.etl.writer import ParquetWriter
from supplychainlens.graph.loader import GraphLoader


def run_pipeline(
    seeds: list[str] = None,
    target_nodes: int = 50,
    seed: int = 42,
    staging_dir: str = "data/staging/npm",
    curated_dir: str = "data/curated/npm",
) -> dict:
    if seeds is None:
        seeds = ["express", "react", "lodash", "axios"]

    print("=" * 60)
    print(" SupplyChainLens End-to-End Pipeline Execution")
    print(f" Parameters: seeds={seeds}, target_nodes={target_nodes}, seed={seed}")
    print(f" Paths: staging_dir='{staging_dir}', curated_dir='{curated_dir}'")
    print("=" * 60)

    # 1. Run Crawler (Phase 2)
    print("\n[Step 1/5] Running bounded npm dependency crawler...")
    generator = NPMDatasetGenerator()
    crawler_stats = generator.generate_dataset(
        seeds=seeds,
        target_nodes=target_nodes,
        seed=seed,
        output_dir=staging_dir,
    )

    # 2. Run Spark ETL (Phase 3A)
    print("\n[Step 2/5] Running Spark ETL pipeline...")
    spark = (
        SparkSession.builder
        .appName("SupplyChainLens End-To-End Pipeline")
        .master("local[*]")
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )

    transformer = NpmTransformer(spark=spark, input_dir=staging_dir)
    etl_data = transformer.run()

    # 3. Data Quality Checks
    print("\n[Step 3/5] Running Data Quality checks...")
    checker = DataQualityChecker(etl_data)
    checker.run()
    quality_status = "PASSED"

    # 4. Write Curated Parquet
    print("\n[Step 4/5] Writing curated Parquet datasets...")
    writer = ParquetWriter(output_dir=curated_dir)
    writer.write(etl_data)
    parquet_status = "OK"

    # 5. Load VersionGraph
    print("\n[Step 5/5] Loading VersionGraph from curated Parquet...")
    loader = GraphLoader(spark=spark, curated_dir=curated_dir)
    graph = loader.load()

    # Basic Graph Sanity & Invariant Checks
    validation_errors = graph.validate()
    if validation_errors:
        raise ValueError(f"Graph validation failed: {validation_errors}")

    if graph.node_count() == 0:
        raise ValueError("Graph node count is zero!")

    if graph.edge_count() == 0:
        raise ValueError("Graph edge count is zero!")

    # Summary Output
    print("\n" + "=" * 30)
    print("SupplyChainLens Pipeline")
    print("=" * 30)
    print("\nCrawler")
    print(f"  Packages discovered: {crawler_stats['discovered_packages']:,}")
    print(f"  Package versions:   {crawler_stats['package_versions']:,}")

    print("\nSpark ETL")
    print(f"  Packages:           {etl_data['packages'].count():,}")
    print(f"  Package versions:   {etl_data['package_versions'].count():,}")
    print(f"  Dependencies:       {etl_data['dependencies'].count():,}")
    print(f"  Resolved deps:      {etl_data['resolved_dependencies'].count():,}")

    print("\nQuality")
    print(f"  Status:             {quality_status}")

    print("\nParquet")
    print(f"  Status:             {parquet_status}")

    print("\nGraph")
    print(f"  Vertices:           {graph.node_count():,}")
    print(f"  Edges:              {graph.edge_count():,}")
    print(f"  Boundary/excluded:  {graph.boundary_edge_count():,}")

    print("\nPipeline completed successfully.\n")

    spark.stop()

    return {
        "crawler_stats": crawler_stats,
        "etl_data": etl_data,
        "graph": graph,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="SupplyChainLens End-to-End Pipeline Execution (Crawler -> ETL -> Parquet -> VersionGraph)"
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
        help="Target package count limit for discovery (0 for unlimited crawl)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic discovery queue ordering (default: 42)",
    )
    parser.add_argument(
        "--staging-dir",
        type=str,
        default="data/staging/npm",
        help="Directory for staging JSONL files (default: data/staging/npm)",
    )
    parser.add_argument(
        "--curated-dir",
        type=str,
        default="data/curated/npm",
        help="Directory for curated Parquet files (default: data/curated/npm)",
    )

    args = parser.parse_args()

    # Treat target_nodes=0 as unlimited (float('inf'))
    target_limit = float("inf") if args.target_nodes <= 0 else args.target_nodes

    run_pipeline(
        seeds=args.seeds,
        target_nodes=target_limit,
        seed=args.seed,
        staging_dir=args.staging_dir,
        curated_dir=args.curated_dir,
    )

