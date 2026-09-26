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
        """
        # Step 1: Non-registry check
        if is_non_registry_constraint(version_constraint):
            return ResolvedDependency(
                source_node_id=source_node_id,
                target_package=target_package,
                version_constraint=version_constraint,
                resolved_node_id=None,
                resolution_status=ResolutionStatus.NON_REGISTRY,
            )

        # Step 2: Invalid constraint check
        if not is_valid_constraint(version_constraint):
            return ResolvedDependency(
                source_node_id=source_node_id,
                target_package=target_package,
                version_constraint=version_constraint,
                resolved_node_id=None,
                resolution_status=ResolutionStatus.INVALID_CONSTRAINT,
            )

        # Step 3: Fetch target packument
        if cached_packument is not None:
            raw_packument = cached_packument
        else:
            raw_packument = self.fetcher.fetch_packument(target_package)

        if raw_packument is None:
            return ResolvedDependency(
                source_node_id=source_node_id,
                target_package=target_package,
                version_constraint=version_constraint,
                resolved_node_id=None,
                resolution_status=ResolutionStatus.PACKAGE_MISSING,
            )

        # Step 4: Parse packument
        _, versions, _ = NPMParser.parse_packument(raw_packument)

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
            return ResolvedDependency(
                source_node_id=source_node_id,
                target_package=target_package,
                version_constraint=version_constraint,
                resolved_node_id=None,
                resolution_status=ResolutionStatus.NO_SATISFYING_VERSION,
            )

        satisfying_versions.sort(key=lambda item: item[0], reverse=True)
        best_version = satisfying_versions[0][1]

        return ResolvedDependency(
            source_node_id=source_node_id,
            target_package=target_package,
            version_constraint=version_constraint,
            resolved_node_id=f"npm:{target_package}@{best_version.version}",
            resolution_status=ResolutionStatus.RESOLVED,
        )
