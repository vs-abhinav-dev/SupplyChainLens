import json
import random
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from .fetcher import NPMFetcher
from .models import Package, PackageVersion, Dependency, ResolvedDependency, ResolutionStatus
from .parser import NPMParser
from .resolver import DependencyResolver


class NPMDatasetGenerator:
    """Recursively discovers npm dependencies and builds a staging dataset formatted as JSON Lines (.jsonl)."""

    def __init__(
        self,
        fetcher: Optional[NPMFetcher] = None,
        resolver: Optional[DependencyResolver] = None,
    ):
        self.fetcher = fetcher or NPMFetcher()
        self.resolver = resolver or DependencyResolver(fetcher=self.fetcher)

    def generate_dataset(
        self,
        seeds: List[str],
        target_nodes: int = 1000,
        seed: int = 42,
        output_dir: str | Path = "data/staging/npm",
        source_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Recursively traverses package dependencies starting from seed packages until target_nodes packages are visited.
        Outputs normalized JSONL files to output_dir.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        rng = random.Random(seed)

        visited_packages: Set[str] = set()
        queued_packages: Set[str] = set()
        queue: deque = deque()

        for s in seeds:
            s_clean = s.strip()
            if s_clean and s_clean not in queued_packages:
                queued_packages.add(s_clean)
                queue.append(s_clean)

        packages_map: Dict[str, Package] = {}
        package_versions_map: Dict[str, PackageVersion] = {}
        dependencies_list: List[Dependency] = []
        resolved_dependencies_list: List[ResolvedDependency] = []
        resolution_counts: Dict[ResolutionStatus, int] = {status: 0 for status in ResolutionStatus}

        while queue and len(visited_packages) < target_nodes:
            current_pkg = queue.popleft()
            if current_pkg in visited_packages:
                continue

            visited_packages.add(current_pkg)
            raw_packument = self.fetcher.fetch_packument(current_pkg)
            if raw_packument is None:
                ## ayo why is None, handle ?
                continue

            pkg_obj, versions, deps = NPMParser.parse_packument(raw_packument)
            packages_map[pkg_obj.package_id] = pkg_obj

            for ver in versions:
                package_versions_map[ver.node_id] = ver

            new_target_candidates: Set[str] = set()

            for dep in deps:
                dependencies_list.append(dep)

                resolved = self.resolver.resolve_dependency(
                    source_node_id=dep.source_node_id,
                    target_package=dep.target_package,
                    version_constraint=dep.version_constraint,
                    source_date=source_date,
                    cached_packument=None,
                )

                resolved_dependencies_list.append(resolved)
                resolution_counts[resolved.resolution_status] += 1

                target_name = dep.target_package
                if (
                    target_name
                    and target_name not in visited_packages
                    and target_name not in queued_packages
                    and resolved.resolution_status != ResolutionStatus.NON_REGISTRY
                    and resolved.resolution_status != ResolutionStatus.INVALID_CONSTRAINT
                ):
                    new_target_candidates.add(target_name)

            # Shuffle candidates deterministically using rng
            sorted_candidates = sorted(list(new_target_candidates))
            rng.shuffle(sorted_candidates)

            for cand in sorted_candidates:
                if len(visited_packages) + len(queued_packages) < target_nodes * 2:
                    queued_packages.add(cand)
                    queue.append(cand)

        # Write JSONL outputs
        self._write_jsonl(output_path / "packages.jsonl", [p.model_dump() for p in packages_map.values()])
        self._write_jsonl(
            output_path / "package_versions.jsonl", [pv.model_dump() for pv in package_versions_map.values()]
        )
        self._write_jsonl(
            output_path / "dependencies.jsonl", [d.model_dump() for d in dependencies_list]
        )
        self._write_jsonl(
            output_path / "resolved_dependencies.jsonl", [rd.model_dump() for rd in resolved_dependencies_list]
        )

        resolved_count = resolution_counts[ResolutionStatus.RESOLVED]
        unresolved_count = len(resolved_dependencies_list) - resolved_count

        return {
            "discovered_packages": len(packages_map),
            "package_versions": len(package_versions_map),
            "dependency_records": len(dependencies_list),
            "resolved_edges": resolved_count,
            "unresolved_edges": unresolved_count,
            "resolution_breakdown": {status.value: count for status, count in resolution_counts.items()},
        }

    @staticmethod
    def _write_jsonl(file_path: Path, records: List[Dict[str, Any]]) -> None:
        """Writes a list of dictionary records to a JSON Lines (.jsonl) file."""
        with open(file_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
