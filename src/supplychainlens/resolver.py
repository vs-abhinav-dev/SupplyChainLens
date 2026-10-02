from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from .fetcher import NPMFetcher
from .models import Dependency, PackageVersion, ResolutionStatus, ResolvedDependency
from .parser import NPMParser
from .semver_utils import (
    is_non_registry_constraint,
    is_valid_constraint,
    normalize_version,
    satisfies,
)


def _parse_iso_date(date_input: str | datetime | None) -> Optional[datetime]:
    """Helper to convert date strings or datetimes into timezone-aware/naive comparable datetimes."""
    if date_input is None:
        return None
    if isinstance(date_input, datetime):
        return date_input

    d_str = str(date_input).strip()
    if d_str.endswith("Z"):
        d_str = d_str[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(d_str)
    except ValueError:
        return None


class DependencyResolver:
    """Time-aware npm dependency resolver."""

    def __init__(self, fetcher: Optional[NPMFetcher] = None):
        self.fetcher = fetcher or NPMFetcher()
        self._parsed_versions_cache: Dict[str, List[PackageVersion]] = {}
        self._resolution_cache: Dict[Tuple[str, str, Optional[str]], ResolvedDependency] = {}

    def resolve_dependency(
        self,
        source_node_id: str,
        target_package: str,
        version_constraint: str,
        source_date: Optional[str | datetime] = None,
        cached_packument: Optional[Dict[str, Any]] = None,
    ) -> ResolvedDependency:
        """
        Resolves a single dependency requirement taking publication date restrictions into account.
        Uses in-memory memoization cache for identical resolution queries.
        """
        source_date_str = str(source_date) if source_date is not None else None
        cache_key = (target_package, version_constraint, source_date_str)

        if cache_key in self._resolution_cache:
            cached_res = self._resolution_cache[cache_key]
            return ResolvedDependency(
                source_node_id=source_node_id,
                target_package=cached_res.target_package,
                version_constraint=cached_res.version_constraint,
                resolved_node_id=cached_res.resolved_node_id,
                resolution_status=cached_res.resolution_status,
            )

        # Step 1: Non-registry check
        if is_non_registry_constraint(version_constraint):
            res = ResolvedDependency(
                source_node_id=source_node_id,
                target_package=target_package,
                version_constraint=version_constraint,
                resolved_node_id=None,
                resolution_status=ResolutionStatus.NON_REGISTRY,
            )
            self._resolution_cache[cache_key] = res
            return res

        # Step 2: Invalid constraint check
        if not is_valid_constraint(version_constraint):
            res = ResolvedDependency(
                source_node_id=source_node_id,
                target_package=target_package,
                version_constraint=version_constraint,
                resolved_node_id=None,
                resolution_status=ResolutionStatus.INVALID_CONSTRAINT,
            )
            self._resolution_cache[cache_key] = res
            return res

        # Step 3: Fetch target packument
        if cached_packument is not None:
            raw_packument = cached_packument
        else:
            raw_packument = self.fetcher.fetch_packument(target_package)

        if raw_packument is None:
            res = ResolvedDependency(
                source_node_id=source_node_id,
                target_package=target_package,
                version_constraint=version_constraint,
                resolved_node_id=None,
                resolution_status=ResolutionStatus.PACKAGE_MISSING,
            )
            self._resolution_cache[cache_key] = res
            return res

        # Step 4: Parse packument (use cache if available)
        if target_package in self._parsed_versions_cache:
            versions = self._parsed_versions_cache[target_package]
        else:
            _, versions, _ = NPMParser.parse_packument(raw_packument)
            self._parsed_versions_cache[target_package] = versions

        # Step 5: Filter out versions published AFTER source_date
        parsed_source_date = _parse_iso_date(source_date)
        eligible_versions: List[PackageVersion] = []

        for ver in versions:
            if parsed_source_date is not None and ver.published_at is not None:
                ver_pub_date = _parse_iso_date(ver.published_at)
                if ver_pub_date is not None and ver_pub_date > parsed_source_date:
                    continue  # Published after source date cut-off
            eligible_versions.append(ver)

        # Step 6: Filter by semver constraint
        satisfying_versions: List[Tuple[Any, PackageVersion]] = []
        for ver in eligible_versions:
            if satisfies(ver.version, version_constraint):
                norm_v = normalize_version(ver.version)
                if norm_v is not None:
                    satisfying_versions.append((norm_v, ver))

        # Step 7: Sort descending and select latest
        if not satisfying_versions:
            res = ResolvedDependency(
                source_node_id=source_node_id,
                target_package=target_package,
                version_constraint=version_constraint,
                resolved_node_id=None,
                resolution_status=ResolutionStatus.NO_SATISFYING_VERSION,
            )
            self._resolution_cache[cache_key] = res
            return res

        satisfying_versions.sort(key=lambda item: item[0], reverse=True)
        best_version = satisfying_versions[0][1]

        res = ResolvedDependency(
            source_node_id=source_node_id,
            target_package=target_package,
            version_constraint=version_constraint,
            resolved_node_id=f"npm:{target_package}@{best_version.version}",
            resolution_status=ResolutionStatus.RESOLVED,
        )
        self._resolution_cache[cache_key] = res
        return res

