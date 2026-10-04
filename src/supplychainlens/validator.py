import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from .models import ResolutionStatus, ResolvedDependency
from .resolver import DependencyResolver


class LockfileValidator:
    """Validates SupplyChainLens resolution output against actual npm package-lock.json."""

    def __init__(self, resolver: Optional[DependencyResolver] = None):
        self.resolver = resolver or DependencyResolver()

    def load_lockfile_actual_versions(self, lockfile_path: Path | str) -> Dict[str, str]:
        """
        Parses package-lock.json (supporting v1, v2, v3 formats)
        to map direct package names to installed versions.
        """
        with open(lockfile_path, "r", encoding="utf-8") as f:
            lock_data = json.load(f)

        actual_versions: Dict[str, str] = {}

        # Lockfile v2 / v3 format
        if "packages" in lock_data and isinstance(lock_data["packages"], dict):
            for pkg_path, details in lock_data["packages"].items():
                if not pkg_path or not isinstance(details, dict):
                    continue
                if "version" in details:
                    # pkg_path is usually "node_modules/lodash" or "node_modules/@types/node"
                    if pkg_path.startswith("node_modules/"):
                        pkg_name = pkg_path[len("node_modules/") :]
                        # Top-level direct node_modules entry only
                        # (no nested node_modules/foo/node_modules/bar)
                        if "node_modules/" not in pkg_name:
                            actual_versions[pkg_name] = details["version"]

        # Lockfile v1 format fallback
        if "dependencies" in lock_data and isinstance(lock_data["dependencies"], dict):
            for pkg_name, details in lock_data["dependencies"].items():
                if isinstance(details, dict) and "version" in details:
                    if pkg_name not in actual_versions:
                        # Strip git/tarball specifiers if present
                        actual_versions[pkg_name] = details["version"].split("#")[-1]

        return actual_versions

    def validate_project(
        self,
        package_json_path: Path | str,
        package_lock_path: Path | str,
        source_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compares package.json declared dependencies against package-lock.json actual locked versions
        and SupplyChainLens resolution results.
        """
        package_json_path = Path(package_json_path)
        package_lock_path = Path(package_lock_path)

        with open(package_json_path, "r", encoding="utf-8") as f:
            pkg_data = json.load(f)

        actual_versions = self.load_lockfile_actual_versions(package_lock_path)

        pkg_name = pkg_data.get("name", "app")
        pkg_ver = pkg_data.get("version", "1.0.0")
        source_node_id = f"npm:{pkg_name}@{pkg_ver}"

        # Collect dependencies from package.json
        declared_deps: Dict[str, str] = {}
        for dep_field in ("dependencies", "devDependencies"):
            if dep_field in pkg_data and isinstance(pkg_data[dep_field], dict):
                declared_deps.update(pkg_data[dep_field])

        comparison_results = []
        matches = 0
        diffs = 0
        non_registry = 0
        failures = 0

        for target_pkg, constraint in declared_deps.items():
            resolved: ResolvedDependency = self.resolver.resolve_dependency(
                source_node_id=source_node_id,
                target_package=target_pkg,
                version_constraint=constraint,
                source_date=source_date,
            )

            actual_ver = actual_versions.get(target_pkg)
            scl_ver = None
            if resolved.resolved_node_id and "@" in resolved.resolved_node_id:
                scl_ver = resolved.resolved_node_id.rsplit("@", 1)[-1]

            match_status = "UNKNOWN"
            if resolved.resolution_status == ResolutionStatus.NON_REGISTRY:
                match_status = "NON_REGISTRY"
                non_registry += 1
            elif resolved.resolution_status != ResolutionStatus.RESOLVED:
                match_status = f"FAILED ({resolved.resolution_status.value})"
                failures += 1
            elif actual_ver and scl_ver:
                if actual_ver == scl_ver:
                    match_status = "MATCH"
                    matches += 1
                else:
                    match_status = "VERSION_DIFF"
                    diffs += 1
            else:
                match_status = "MISSING_IN_LOCKFILE"
                diffs += 1

            comparison_results.append({
                "package": target_pkg,
                "constraint": constraint,
                "npm_locked_version": actual_ver,
                "scl_resolved_version": scl_ver,
                "resolution_status": resolved.resolution_status.value,
                "match_status": match_status,
            })

        return {
            "source_node_id": source_node_id,
            "total_dependencies": len(declared_deps),
            "matches": matches,
            "version_diffs": diffs,
            "non_registry": non_registry,
            "failures": failures,
            "details": comparison_results,
        }
