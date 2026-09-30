from pyspark.sql import SparkSession
from pyspark.sql.types import TimestampType

from supplychainlens.etl.transform import NpmTransformer
from supplychainlens.etl.quality import DataQualityChecker
from supplychainlens.etl.writer import ParquetWriter


def run_etl(
    input_dir: str = "data/staging/npm",
    output_dir: str = "data/curated/npm",
) -> dict:
    spark = (
        SparkSession.builder
        .appName("SupplyChainLens ETL")
        .master("local[*]")
        .getOrCreate()
    )

    print("1. Reading and transforming staging datasets...")
    transformer = NpmTransformer(
        spark=spark,
        input_dir=input_dir,
    )
    data = transformer.run()

    print("\n2. Running data quality checks...")
    checker = DataQualityChecker(data)
    checker.run()

    print("\n3. Writing curated Parquet datasets...")
    writer = ParquetWriter(output_dir=output_dir)
    writer.write(data)

    print("\n4. Verifying written Parquet datasets...")
    verified_data = {}
    for name, original_df in data.items():
        parquet_path = f"{output_dir}/{name}"
        read_df = spark.read.parquet(parquet_path)

        orig_count = original_df.count()
        read_count = read_df.count()

        print(f"\nVerifying '{name}':")
        print(f"  Parquet path: {parquet_path}")
        print(f"  In-memory count: {orig_count:,}")
        print(f"  Parquet count:   {read_count:,}")
        read_df.printSchema()

        if orig_count != read_count:
            raise ValueError(
                f"Row count mismatch for '{name}': "
                f"expected {orig_count}, got {read_count}"
            )

        if name == "package_versions":
            pub_type = read_df.schema["published_at"].dataType
            print(f"  package_versions.published_at dataType: {pub_type}")
            if not isinstance(pub_type, TimestampType):
                raise TypeError(
                    f"Expected published_at to be TimestampType, got {pub_type}"
                )

        verified_data[name] = read_df

    print("\nETL Pipeline completed and verified successfully!")
    spark.stop()
    return verified_data


if __name__ == "__main__":
    run_etl()
