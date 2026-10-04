from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import pyarrow.parquet as pq

from .backend import GraphBackend
from .factory import create_graph
from .models import Edge, Node
from ..semver_utils import normalize_version


class GraphRepository:
    """
    Repository layer for constructing and querying SupplyChainLens graphs from Parquet.
    Uses high-speed PyArrow ingestion (no JVM overhead) and isolates callers from storage details.
    """

    def __init__(
        self,
        curated_dir: str | Path = "data/curated/npm",
        backend: Optional[str] = None,
    ) -> None:
        self.curated_dir = Path(curated_dir)
        self._backend_choice = backend
        self._graph: Optional[GraphBackend] = None
        self._packages_meta: Dict[str, Dict[str, Any]] = {}
        self._package_to_versions: Dict[str, List[Node]] = {}

    @property
    def graph(self) -> GraphBackend:
        if self._graph is None:
            self.load()
        assert self._graph is not None
        return self._graph

    def get_graph(self) -> GraphBackend:
        """Return the current GraphBackend instance, loading on demand if not loaded."""
        return self.graph

    def load(self) -> GraphBackend:
        """
        Loads curated Parquet files and constructs the graph backend.
        Returns the constructed GraphBackend instance.
        """
        graph = create_graph(self._backend_choice)
        self._packages_meta.clear()
        self._package_to_versions.clear()

        # 1. Load packages metadata if present
        packages_path = self.curated_dir / "packages"
        if packages_path.exists():
            pkg_table = pq.read_table(str(packages_path))
            for row in pkg_table.to_pylist():
                pkg_id = row.get("package_id", "")
                name = row.get("name", "")
                self._packages_meta[pkg_id] = row
                self._packages_meta[name] = row

        # 2. Load package version vertices
        versions_path = self.curated_dir / "package_versions"
        if not versions_path.exists():
            raise FileNotFoundError(f"Curated package versions not found at: {versions_path}")

        v_table = pq.read_table(str(versions_path))
        for row in v_table.to_pylist():
            pub_at = str(row["published_at"]) if row.get("published_at") is not None else None
            node = Node(
                node_id=row["node_id"],
                package_id=row["package_id"],
                name=row["name"],
                version=row["version"],
                published_at=pub_at,
            )
            graph.add_node(node)

            # Index package versions
            name = node.name
            pkg_id = node.package_id
            if name not in self._package_to_versions:
                self._package_to_versions[name] = []
            self._package_to_versions[name].append(node)

            if pkg_id not in self._package_to_versions:
                self._package_to_versions[pkg_id] = self._package_to_versions[name]

        # Sort versions in each package
        for name, nodes in self._package_to_versions.items():
            nodes.sort(
                key=lambda n: normalize_version(n.version) or n.version,
                reverse=True,
            )

        # 3. Load dependency edges
        deps_path = self.curated_dir / "dependencies"
        res_deps_path = self.curated_dir / "resolved_dependencies"

        dep_type_map: Dict[tuple, str] = {}
        if deps_path.exists():
            deps_table = pq.read_table(str(deps_path))
            for row in deps_table.to_pylist():
                key = (
                    row["source_node_id"],
                    row["target_package"],
                    row["version_constraint"],
                )
                dep_type_map[key] = row.get("dependency_type") or "dependencies"

        if res_deps_path.exists():
            res_table = pq.read_table(str(res_deps_path))
            for row in res_table.to_pylist():
                if row.get("resolution_status") != "resolved":
                    continue

                source_id = row["source_node_id"]
                target_id = row.get("resolved_node_id")
                constraint = row.get("version_constraint") or ""
                target_pkg = row.get("target_package") or ""
                dep_type = dep_type_map.get((source_id, target_pkg, constraint), "dependencies")

                if not target_id:
                    graph.record_boundary_edge(
                        source_node_id=source_id,
                        target_node_id=None,
                        target_package=target_pkg,
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

        self._graph = graph
        return self._graph

    def reload(self) -> GraphBackend:
        """Forces reloading the graph from disk."""
        return self.load()

    def list_packages(self) -> List[str]:
        """Return sorted list of distinct package names."""
        if self._graph is None:
            self.load()
        # Filter out prefixed ids so only clean package names appear
        clean_names = {
            pkg for pkg in self._package_to_versions.keys() if not pkg.startswith("npm:")
        }
        return sorted(list(clean_names))

    def get_package(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve package metadata and version list for a given package name."""
        if self._graph is None:
            self.load()

        clean_name = package_name.strip()
        if clean_name.startswith("npm:"):
            clean_name = clean_name[4:]

        versions = self._package_to_versions.get(clean_name, [])
        if not versions:
            return None

        latest_node = versions[0] if versions else None
        meta = self._packages_meta.get(clean_name) or self._packages_meta.get(f"npm:{clean_name}") or {}

        return {
            "package_id": f"npm:{clean_name}",
            "name": clean_name,
            "ecosystem": meta.get("ecosystem", "npm"),
            "versions": [v.version for v in versions],
            "node_ids": [v.node_id for v in versions],
            "latest_version": latest_node.version if latest_node else None,
            "latest_node_id": latest_node.node_id if latest_node else None,
            "total_versions": len(versions),
        }

    def get_package_versions(self, package_name: str) -> List[Node]:
        """Return list of Node objects representing all recorded versions of a package."""
        if self._graph is None:
            self.load()
        clean = package_name.strip().replace("npm:", "")
        return list(self._package_to_versions.get(clean, []))

    def get_latest_version(self, package_name: str) -> Optional[Node]:
        """Return the latest version Node for a package, or None."""
        versions = self.get_package_versions(package_name)
        return versions[0] if versions else None
