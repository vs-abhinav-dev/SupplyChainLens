import re
from typing import List, Optional, Tuple
import semver


def is_non_registry_constraint(constraint: str) -> bool:
    """Detects if a dependency constraint is a non-registry dependency (git, HTTP, file path, workspace)."""
    c = constraint.strip().lower()
    if not c:
        return False

    prefixes = (
        "git+",
        "git://",
        "http://",
        "https://",
        "file:",
        "workspace:",
        "github:",
        "bitbucket:",
        "gitlab:",
    )
    if any(c.startswith(p) for p in prefixes):
        return True

    # Tarball URL (.tgz / .tar.gz)
    if c.endswith(".tgz") or c.endswith(".tar.gz"):
        return True

    # User/repo pattern e.g. "expressjs/express" or "lodash/lodash#v4.17.21"
    if "/" in c and not any(op in c for op in (">", "<", "=", "~", "^", " ")):
        return True

    return False


def normalize_version(ver_str: str) -> Optional[semver.Version]:
    """Coerces a version string into a valid semver.Version object."""
    clean = ver_str.strip().lstrip("v")
    # Handle version like "1.2" or "1"
    parts = clean.split(".")
    if len(parts) == 1 and parts[0].isdigit():
        clean = f"{parts[0]}.0.0"
    elif len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        clean = f"{parts[0]}.{parts[1]}.0"

    try:
        return semver.Version.parse(clean)
    except ValueError:
        return None


def _parse_single_comparator(comp: str):
    """
    Parses a single comparator like '^1.2.3', '~1.2.0', '>=2', '<3', '1.x', '*', '1.2.3'.
    Returns a function (semver.Version) -> bool or raises ValueError.
    """
    comp = comp.strip().lstrip("v")
    if not comp or comp in ("*", "x", "X"):
        return lambda v: True

    # Caret range: ^1.2.3, ^0.2.3, ^0.0.3, ^2
    if comp.startswith("^"):
        v_str = comp[1:].strip()
        v_parsed = normalize_version(v_str)
        if v_parsed is None:
            raise ValueError(f"Invalid caret version: {comp}")

        # Determine upper bound for caret
        if v_parsed.major > 0:
            upper = semver.Version(v_parsed.major + 1, 0, 0, prerelease="0")
        elif v_parsed.minor > 0:
            upper = semver.Version(0, v_parsed.minor + 1, 0, prerelease="0")
        else:
            upper = semver.Version(0, 0, v_parsed.patch + 1, prerelease="0")

        return lambda v: v >= v_parsed and v < upper

    # Tilde range: ~1.2.3, ~1.2, ~1
    if comp.startswith("~"):
        v_str = comp[1:].strip()
        parts = v_str.split(".")
        v_parsed = normalize_version(v_str)
        if v_parsed is None:
            raise ValueError(f"Invalid tilde version: {comp}")

        if len(parts) == 1:
            upper = semver.Version(v_parsed.major + 1, 0, 0, prerelease="0")
        else:
            upper = semver.Version(v_parsed.major, v_parsed.minor + 1, 0, prerelease="0")

        return lambda v: v >= v_parsed and v < upper

    # Wildcards e.g. 1.x, 1.*, 1.2.x, 1.2.*
    if ".x" in comp.lower() or ".*" in comp:
        clean_comp = re.sub(r"\.[xX\*]", "", comp)
        parts = clean_comp.split(".")
        if len(parts) == 1 and parts[0].isdigit():
            major = int(parts[0])
            lower = semver.Version(major, 0, 0)
            upper = semver.Version(major + 1, 0, 0, prerelease="0")
            return lambda v: v >= lower and v < upper
        elif len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            major, minor = int(parts[0]), int(parts[1])
            lower = semver.Version(major, minor, 0)
            upper = semver.Version(major, minor + 1, 0, prerelease="0")
            return lambda v: v >= lower and v < upper
        else:
            raise ValueError(f"Invalid wildcard range: {comp}")

    # Comparative operators: >=, <=, >, <, =, ==
    ops = [(">=", lambda v, target: v >= target),
           ("<=", lambda v, target: v <= target),
           (">", lambda v, target: v > target),
           ("<", lambda v, target: v < target),
           ("==", lambda v, target: v == target),
           ("=", lambda v, target: v == target)]

    for op_str, op_fn in ops:
        if comp.startswith(op_str):
            v_str = comp[len(op_str):].strip()
            v_parsed = normalize_version(v_str)
            if v_parsed is None:
                raise ValueError(f"Invalid comparison target: {comp}")
            return lambda v, op_fn=op_fn, target=v_parsed: op_fn(v, target)

    # Simple version number e.g. "1.2.3" or "1.2" or "1"
    v_parsed = normalize_version(comp)
    if v_parsed is not None:
        return lambda v, target=v_parsed: v == target

    raise ValueError(f"Unrecognized constraint syntax: {comp}")


def parse_range_expression(constraint: str):
    """
    Parses an npm semver range string (supporting space-separated AND conditions and || OR clauses).
    Returns a matcher function (semver.Version) -> bool or raises ValueError.
    """
    c = constraint.strip()
    if not c or c in ("*", "x", "X", "latest"):
        return lambda v: True

    # Split by || (OR clauses)
    or_clauses = c.split("||")
    clause_matchers = []

    for clause in or_clauses:
        clause = clause.strip()
        if not clause:
            continue

        # Split space/comma separated AND components e.g. ">=2.0.0 <3.0.0" or ">=2, <3"
        raw_comps = re.split(r"[\s,]+", clause)
        comp_matchers = []

        for comp in raw_comps:
            comp = comp.strip()
            if comp:
                comp_matchers.append(_parse_single_comparator(comp))

        if comp_matchers:
            clause_matchers.append(lambda v, matchers=comp_matchers: all(m(v) for m in matchers))

    if not clause_matchers:
        raise ValueError(f"Empty constraint expression: {constraint}")

    return lambda v: any(cm(v) for cm in clause_matchers)


def is_valid_constraint(constraint: str) -> bool:
    """Returns True if the constraint is a syntactically valid NPM SemVer range."""
    if is_non_registry_constraint(constraint):
        return False
    try:
        parse_range_expression(constraint)
        return True
    except ValueError:
        return False


def satisfies(version_str: str, constraint: str) -> bool:
    """Evaluates whether a version string satisfies an npm semver constraint."""
    v_parsed = normalize_version(version_str)
    if v_parsed is None:
        return False

    try:
        matcher = parse_range_expression(constraint)
        return matcher(v_parsed)
    except ValueError:
        return False
