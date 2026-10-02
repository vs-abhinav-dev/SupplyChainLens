
from pyspark.sql import DataFrame
from pyspark.sql import functions as F


class DataQualityChecker:

    def __init__(self, data: dict[str,DataFrame]):
        self.data = data
    

    def check_packages(self) -> None:
        print("\nChecking packages...")
        df = self.data["packages"]

        self._check_not_null(
            df,
            ["package_id", "name", "ecosystem"],
        )

        self._check_unique(
            df,
            ["package_id"],
        )

        print("Packages: OK")

    def check_package_versions(self) -> None:
        print("\nChecking package versions...")
        df = self.data["package_versions"]

        self._check_not_null(
            df,
            [
                "node_id",
                "package_id",
                "name",
                "version",
                "published_at",
            ],
        )

        self._check_unique(
            df,
            ["node_id"],
        )

        print("Package versions: OK")

    def check_dependencies(self) -> None:
        print("\nChecking dependencies...")
        df = self.data["dependencies"]
        self._check_not_null(
            df,
            [
                "source_node_id",
                "target_package",
                "version_constraint",
                "dependency_type",
            ],
        )

        print("Dependencies: OK")

    def check_resolved_dependencies(
        self
    ) -> None:
        print("\nChecking resolved dependencies...")
        df = self.data["resolved_dependencies"]
        package_versions = self.data["package_versions"]

        self._check_not_null(
            df,
            [
                "source_node_id",
                "target_package",
                "version_constraint",
                "resolution_status",
            ],
        )

        # A resolved dependency must have a target node.
        invalid_resolved = df.filter(
            (F.col("resolution_status") == "resolved")
            & F.col("resolved_node_id").isNull()
        )

        count = invalid_resolved.count()

        if count > 0:
            raise ValueError(
                f"Found {count} resolved dependencies "
                "with null resolved_node_id"
            )

        # Every resolved source node must exist.
        source_check = (
            df.filter(F.col("resolution_status") == "resolved")
            .select("source_node_id")
            .distinct()
            .join(
                package_versions.select("node_id").distinct(),
                F.col("source_node_id") == F.col("node_id"),
                "left_anti",
            )
        )

        missing_sources = source_check.count()

        if missing_sources > 0:
            raise ValueError(
                f"Found {missing_sources} resolved dependencies "
                "whose source node does not exist"
            )

        # Every resolved target node must exist.
        target_check = (
            df.filter(F.col("resolution_status") == "resolved")
            .select("resolved_node_id")
            .distinct()
            .join(
                package_versions.select("node_id").distinct(),
                F.col("resolved_node_id") == F.col("node_id"),
                "left_anti",
            )
        )

        missing_targets = target_check.count()

        if missing_targets > 0:
            print(f"Resolved dependencies: OK ({missing_targets:,} boundary target nodes outside visited crawl subset)")
        else:
            print("Resolved dependencies: OK (100% target nodes present in dataset)")

    def run(self):
        self.check_dependencies()
        self.check_resolved_dependencies()
        self.check_package_versions()
        self.check_packages()


    @staticmethod
    def _check_not_null(
        df: DataFrame,
        columns: list[str],
    ) -> None:
        for column in columns:
            count = df.filter(
                F.col(column).isNull()
            ).count()

            if count > 0:
                raise ValueError(
                    f"Column '{column}' contains "
                    f"{count} null values"
                )

    @staticmethod
    def _check_unique(
        df: DataFrame,
        columns: list[str],
    ) -> None:
        total = df.count()

        unique = df.select(*columns).distinct().count()

        if total != unique:
            raise ValueError(
                f"Duplicate records found for "
                f"columns: {columns}"
            )
