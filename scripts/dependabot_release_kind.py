"""Decide whether a merged Dependabot PR changed what users install.

Invoked by `.github/workflows/auto-release.yml` with `pyproject.toml` from before
and after the merge. Prints one of:

- `none`  -- the published package is unchanged, so no release
- `patch` -- a runtime dependency's range moved, admitting the same major versions
- `minor` -- a runtime dependency was added or removed, or its range now admits
  different major versions

Dependabot's `uv` PRs usually touch `uv.lock` alone. The lock is not part of the
wheel -- its `Requires-Dist` metadata comes from `[project]` in `pyproject.toml` --
so a lock-only bump would publish an identical package under a new version. Dev
dependency groups are not published either, and are ignored. See
docs/tech/RELEASING.md.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

NONE, PATCH, MINOR = "none", "patch", "minor"

_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?")
_CLAUSE = re.compile(r"^(===|==|!=|~=|<=|>=|<|>)\s*v?([0-9][0-9.]*)(\.\*)?")

Version = tuple[int, ...]
# A requirement's identity: (extra, normalised name, environment marker). The
# marker is part of it because `foo>=2; os_name == 'nt'` and `foo>=1` are
# separate `Requires-Dist` entries that apply in different environments.
Key = tuple[str, str, str]


def _version(text: str) -> Version:
    return tuple(int(part) for part in text.strip(".").split(".") if part)


def _bump(version: Version, index: int) -> Version:
    """The first version past every release sharing `version[: index + 1]`."""
    padded = version + (0,) * (index + 1 - len(version))
    return padded[:index] + (padded[index] + 1,)


def _compare(a: Version, b: Version) -> int:
    width = max(len(a), len(b))
    a, b = a + (0,) * (width - len(a)), b + (0,) * (width - len(b))
    return (a > b) - (a < b)


def admitted_majors(clauses: list[str]) -> tuple[int, int | None] | None:
    """The major versions a specifier admits, as (first, last or None if open).

    The clauses intersect into one interval, so the admitted majors are always
    contiguous. `!=` cannot narrow that interval and is ignored. Returns None
    when the range admits nothing.
    """
    low: Version = (0,)
    low_inclusive = True
    high: Version | None = None
    high_inclusive = False

    for clause in clauses:
        match = _CLAUSE.match(clause)
        if match is None:
            continue
        op, raw, wildcard = match.groups()
        version = _version(raw)
        bounds: list[tuple[str, Version, bool]] = []
        if op in ("==", "===") and wildcard:
            bounds = [
                ("low", version, True),
                ("high", _bump(version, len(version) - 1), False),
            ]
        elif op in ("==", "==="):
            bounds = [("low", version, True), ("high", version, True)]
        elif op == "~=":
            bounds = [
                ("low", version, True),
                ("high", _bump(version, max(len(version) - 2, 0)), False),
            ]
        elif op in (">=", ">"):
            bounds = [("low", version, op == ">=")]
        elif op in ("<=", "<"):
            bounds = [("high", version, op == "<=")]
        for side, bound, inclusive in bounds:
            if side == "low":
                order = _compare(bound, low)
                if order > 0 or (order == 0 and not inclusive):
                    low, low_inclusive = bound, inclusive
            else:
                order = 1 if high is None else _compare(bound, high)
                if high is None or order < 0 or (order == 0 and not inclusive):
                    high, high_inclusive = bound, inclusive

    # `>3` still admits 3.0.1, so the lowest admitted major is low's either way.
    first = low[0]
    if high is None:
        return (first, None)
    order = _compare(high, low)
    if order < 0 or (order == 0 and not (low_inclusive and high_inclusive)):
        return None
    # An exclusive bound at exactly X (or X.0.0) admits nothing from major X.
    excludes_major = not high_inclusive and not any(high[1:])
    last = high[0] - 1 if excludes_major else high[0]
    return (first, last) if last >= first else None


def runtime_requirements(pyproject: str) -> dict[Key, list[str]]:
    """Every requirement a wheel declares, as Key -> sorted specifier clauses."""
    project = tomllib.loads(pyproject).get("project", {})
    groups = {"": project.get("dependencies", [])}
    groups.update(project.get("optional-dependencies", {}))
    requirements: dict[Key, list[str]] = {}
    for extra, entries in groups.items():
        for entry in entries:
            spec, _, marker = entry.partition(";")
            match = _NAME.match(spec)
            if match is None:
                continue
            name = re.sub(r"[-_.]+", "-", match.group(1)).lower()
            key = (extra, name, " ".join(marker.split()))
            clauses = [c.strip() for c in spec[match.end() :].split(",") if c.strip()]
            requirements.setdefault(key, []).extend("".join(c.split()) for c in clauses)
    return {key: sorted(clauses) for key, clauses in requirements.items()}


def release_kind(before: str, after: str) -> str:
    """Classify the change between two `pyproject.toml` texts."""
    old, new = runtime_requirements(before), runtime_requirements(after)
    if old == new:
        return NONE
    if old.keys() != new.keys():
        return MINOR
    for key, clauses in new.items():
        if admitted_majors(old[key]) != admitted_majors(clauses):
            return MINOR
    return PATCH


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path, help="pyproject.toml before the merge")
    parser.add_argument("after", type=Path, help="pyproject.toml after the merge")
    args = parser.parse_args(argv)
    print(release_kind(args.before.read_text(), args.after.read_text()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
