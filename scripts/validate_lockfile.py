import json
import sys
from pathlib import Path

# Add src to python path if needed
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from supplychainlens.validator import LockfileValidator


def main():
    if len(sys.argv) >= 3:
        pkg_json = sys.argv[1]
        pkg_lock = sys.argv[2]
        source_date = sys.argv[3] if len(sys.argv) >= 4 else None
    else:
        pkg_json = "sample_project/package.json"
        pkg_lock = "sample_project/package-lock.json"
        source_date = None

    validator = LockfileValidator()
    report = validator.validate_project(pkg_json, pkg_lock, source_date=source_date)

    print("=" * 60)
    print(" SupplyChainLens vs NPM Lockfile Validation Report (Step 9)")
    print("=" * 60)
    print(f"Source Node:          {report['source_node_id']}")
    print(f"Total Dependencies:   {report['total_dependencies']}")
    print(f"Exact Matches:        {report['matches']}")
    print(f"Version Differences:  {report['version_diffs']}")
    print(f"Non-Registry:         {report['non_registry']}")
    print(f"Failures:             {report['failures']}")
    print("-" * 60)
    print(f"{'Package':<20} {'Constraint':<12} {'NPM Lockfile':<15} {'SupplyChainLens':<15} {'Status':<15}")
    print("-" * 60)

    for item in report["details"]:
        pkg = item["package"][:19]
        c = item["constraint"][:11]
        npm_v = (item["npm_locked_version"] or "N/A")[:14]
        scl_v = (item["scl_resolved_version"] or "N/A")[:14]
        status = item["match_status"][:15]
        print(f"{pkg:<20} {c:<12} {npm_v:<15} {scl_v:<15} {status:<15}")

    print("=" * 60)


if __name__ == "__main__":
    main()
