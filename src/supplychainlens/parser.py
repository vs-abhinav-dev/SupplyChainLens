from typing import Any, Dict, List, Tuple
from .models import Package, PackageVersion, Dependency


class NPMParser:
    """Parses raw NPM packuments into normalized models."""

    @staticmethod
    def parse_packument(
        raw_packument: Dict[str, Any]
    ) -> Tuple[Package, List[PackageVersion], List[Dependency]]:
        """
        Parses a raw npm packument JSON object.
        Returns:
            (Package, List[PackageVersion], List[Dependency])
        """
        name = raw_packument.get("name", "")
        package_id = f"npm:{name}"
        package_obj = Package(package_id=package_id, name=name, ecosystem="npm")

        time_dict = raw_packument.get("time", {})
        versions_dict = raw_packument.get("versions", {})

        package_versions: List[PackageVersion] = []
        dependencies: List[Dependency] = []

        for ver_str, ver_data in versions_dict.items():
            if not isinstance(ver_data, dict):
                continue

            ver_name = ver_data.get("name", name)
            node_id = f"npm:{ver_name}@{ver_str}"
            published_at = time_dict.get(ver_str)

            pkg_version = PackageVersion(
                node_id=node_id,
                package_id=package_id,
                name=ver_name,
                version=ver_str,
                published_at=published_at,
            )
            package_versions.append(pkg_version)

            # Extract dependencies for this version
            dep_types = [
                ("dependencies", ver_data.get("dependencies")),
                ("devDependencies", ver_data.get("devDependencies")),
                ("peerDependencies", ver_data.get("peerDependencies")),
                ("optionalDependencies", ver_data.get("optionalDependencies")),
            ]

            for dep_type_name, dep_map in dep_types:
                if isinstance(dep_map, dict):
                    for target_pkg, constraint in dep_map.items():
                        if isinstance(constraint, str):
                            dependencies.append(
                                Dependency(
                                    source_node_id=node_id,
                                    target_package=target_pkg,
                                    version_constraint=constraint.strip(),
                                    dependency_type=dep_type_name,
                                )
                            )

        return package_obj, package_versions, dependencies
