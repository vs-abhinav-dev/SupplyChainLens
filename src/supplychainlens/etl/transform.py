from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import to_timestamp

from .schemas import (
    packages_schema,
    package_versions_schema,
    dependencies_schema,
    resolved_dependencies_schema,
)


class NpmTransformer:

    def __init__(self, spark: SparkSession, input_dir: str):
        self.spark = spark
        self.input_dir = Path(input_dir)

    def read_packages(self) -> DataFrame:
        return self.spark.read.schema(
            packages_schema
        ).json(str(self.input_dir / "packages.jsonl"))

    def read_package_versions(self) -> DataFrame:
        return self.spark.read.schema(
            package_versions_schema
        ).json(str(self.input_dir / "package_versions.jsonl"))

    def read_dependencies(self) -> DataFrame:
        return self.spark.read.schema(
            dependencies_schema
        ).json(str(self.input_dir / "dependencies.jsonl"))

    def read_resolved_dependencies(self) -> DataFrame:
        return self.spark.read.schema(
            resolved_dependencies_schema
        ).json(str(self.input_dir / "resolved_dependencies.jsonl"))

    def transform_package_versions(
        self,
        df: DataFrame
    ) -> DataFrame:
        return df.withColumn(
            "published_at",
            to_timestamp("published_at")
        )

    def run(self) -> dict[str, DataFrame]:
        packages = self.read_packages()

        package_versions = self.read_package_versions()
        package_versions = self.transform_package_versions(
            package_versions
        )

        dependencies = self.read_dependencies()

        resolved_dependencies = (
            self.read_resolved_dependencies()
        )

        return {
            "packages": packages,
            "package_versions": package_versions,
            "dependencies": dependencies,
            "resolved_dependencies": resolved_dependencies,
        }
