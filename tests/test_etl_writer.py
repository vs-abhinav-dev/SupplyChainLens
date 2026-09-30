import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import TimestampType

from supplychainlens.etl.transform import NpmTransformer
from supplychainlens.etl.quality import DataQualityChecker
from supplychainlens.etl.writer import ParquetWriter


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder
        .appName("SupplyChainLens Test ETL")
        .master("local[1]")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_parquet_writer(spark, tmp_path):
    output_dir = tmp_path / "curated_npm"

    transformer = NpmTransformer(spark=spark, input_dir="data/staging/npm")
    data = transformer.run()

    checker = DataQualityChecker(data)
    checker.run()

    writer = ParquetWriter(output_dir=str(output_dir))
    writer.write(data)

    expected_datasets = [
        "packages",
        "package_versions",
        "dependencies",
        "resolved_dependencies",
    ]

    for name in expected_datasets:
        dataset_path = output_dir / name
        assert dataset_path.exists()
        assert dataset_path.is_dir()

        read_df = spark.read.parquet(str(dataset_path))
        orig_count = data[name].count()
        read_count = read_df.count()

        assert read_count == orig_count, f"{name} count mismatch"

        if name == "package_versions":
            pub_type = read_df.schema["published_at"].dataType
            assert isinstance(pub_type, TimestampType), (
                f"Expected TimestampType, got {pub_type}"
            )
