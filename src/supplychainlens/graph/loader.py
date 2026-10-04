from pathlib import Path
from typing import Optional
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from .graph import VersionGraph
from .models import Edge, Node


class GraphLoader:
    """
    Loads curated Parquet datasets into an in-memory VersionGraph.
    Uses Spark to read Parquet data, then builds the framework-agnostic VersionGraph.
    """

    def __init__(
        self,
        spark: Optional[SparkSession] = None,
        curated_dir: str = "data/curated/npm",
    ) -> None:
        self.spark = spark
        self.curated_dir = Path(curated_dir)

    def load(self) -> VersionGraph:
        """
        Loads vertices and edges from curated Parquet files and returns a VersionGraph.
        """
        spark = self.spark
        if spark is None:
            spark = (
                SparkSession.builder
                .appName("SupplyChainLens GraphLoader")
                .master("local[*]")
                .getOrCreate()
            )

        graph = VersionGraph()

        # 1. Load vertices (package_versions)
        versions_path = self.curated_dir / "package_versions"
        print(f"Loading vertices from {versions_path}...")
        versions_df = spark.read.parquet(str(versions_path))

        versions_rows = versions_df.select(
            "node_id", "package_id", "name", "version", "published_at"
        ).collect()

        for row in versions_rows:
            pub_at_str = str(row["published_at"]) if row["published_at"] is not None else None
            node = Node(
                node_id=row["node_id"],
                package_id=row["package_id"],
                name=row["name"],
                version=row["version"],
                published_at=pub_at_str,
            )
            graph.add_node(node)

        # 2. Load dependencies with dependency_type
        deps_path = self.curated_dir / "dependencies"
        res_deps_path = self.curated_dir / "resolved_dependencies"

        print(f"Loading dependency edges from {res_deps_path}...")
        deps_df = spark.read.parquet(str(deps_path)).distinct()
        res_deps_df = spark.read.parquet(str(res_deps_path)).filter(
            F.col("resolution_status") == "resolved"
        )

        # Join resolved_dependencies with dependencies on
        # source_node_id, target_package, version_constraint
        # to obtain dependency_type
        joined_df = res_deps_df.join(
            deps_df,
            on=["source_node_id", "target_package", "version_constraint"],
            how="left",
        ).select(
            "source_node_id",
            "target_package",
            "version_constraint",
            "resolved_node_id",
            "dependency_type",
        )

        edge_rows = joined_df.collect()

        for row in edge_rows:
            source_id = row["source_node_id"]
            target_id = row["resolved_node_id"]
            constraint = row["version_constraint"] or ""
            dep_type = row["dependency_type"] or "dependencies"

            if not target_id:
                graph.record_boundary_edge(
                    source_node_id=source_id,
                    target_node_id=None,
                    target_package=row["target_package"] or "",
                    version_constraint=constraint,
                    reason="null_resolved_target",
                )
                continue

            edge = Edge(
                source_node_id=source_id,
                target_node_id=target_id,
                version_constraint=constraint,
                dependency_type=dep_type,
            )
            graph.add_edge(edge)

        print(f"\n--- VersionGraph Loaded ---")
        print(f"Vertices (Node count):     {graph.node_count():,}")
        print(f"In-Graph Edges:            {graph.edge_count():,}")
        print(f"Boundary/Excluded Edges:  {graph.boundary_edge_count():,}")

        return graph
