"""Decide whether a merged Dependabot PR changed what users install.

Invoked by `.github/workflows/auto-release.yml` with `pyproject.toml` from before
and after the merge. Prints one of:

- `none`  -- the published package is unchanged, so no release
- `patch` -- a runtime dependency's range moved within the same major versions
- `minor` -- a runtime dependency was added, removed, or crossed a major version

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

_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
# The leading number of every version a specifier mentions: `>=2,<3` -> {2, 3}.
_MAJOR = re.compile(r"(?:===|==|!=|~=|<=|>=|<|>)\s*v?(\d+)")


def runtime_requirements(pyproject: str) -> dict[tuple[str, str], str]:
    """Map (extra, normalised name) -> specifier for everything a wheel declares.

    `extra` is "" for `[project].dependencies`, else the optional-dependency key.
    """
    project = tomllib.loads(pyproject).get("project", {})
    groups = {"": project.get("dependencies", [])}
    groups.update(project.get("optional-dependencies", {}))
    requirements: dict[tuple[str, str], str] = {}
    for extra, entries in groups.items():
        for entry in entries:
            match = _NAME.match(entry)
            if match is None:
                continue
            name = re.sub(r"[-_.]+", "-", match.group(1)).lower()
            requirements[(extra, name)] = "".join(entry[match.end() :].split())
    return requirements


def _majors(specifier: str) -> set[int]:
    # Strip extras and environment markers; neither carries a version bound.
    bounds = re.sub(r"^\[[^\]]*\]", "", specifier).split(";", 1)[0]
    return {int(major) for major in _MAJOR.findall(bounds)}


def release_kind(before: str, after: str) -> str:
    """Classify the change between two `pyproject.toml` texts."""
    old, new = runtime_requirements(before), runtime_requirements(after)
    if old == new:
        return NONE
    if old.keys() != new.keys():
        return MINOR
    for key, specifier in new.items():
        if _majors(old[key]) != _majors(specifier):
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
