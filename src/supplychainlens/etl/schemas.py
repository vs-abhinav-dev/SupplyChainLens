from pyspark.sql.types import StructField, StructType, StringType


packages_schema = StructType([
    StructField("package_id", StringType(), False),
    StructField("name", StringType(), False),
    StructField("ecosystem", StringType(), False),
])

package_versions_schema = StructType([
    StructField("node_id", StringType(), False),
    StructField("package_id", StringType(), False),
    StructField("name", StringType(), False),
    StructField("version", StringType(), False),
    StructField("published_at", StringType(), False)
])

dependencies_schema = StructType([
    StructField("source_node_id", StringType(), False),
    StructField("target_package", StringType(), False),
    StructField("version_constraint", StringType(), False),
    StructField("dependency_type", StringType(), False)
])

resolved_dependencies_schema = StructType([
    StructField("source_node_id", StringType(), False),
    StructField("target_package", StringType(), False),
    StructField("version_constraint", StringType(), False),
    StructField("resolved_node_id", StringType(), True),
    StructField("resolution_status", StringType(), False)
])
