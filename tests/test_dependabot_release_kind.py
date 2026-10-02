"""Tests for scripts/dependabot_release_kind.py."""

from __future__ import annotations

import pytest
from dependabot_release_kind import admitted_majors, main, release_kind


def _pyproject(dependencies: list[str], dev: list[str] | None = None) -> str:
    deps = ", ".join(f'"{dep}"' for dep in dependencies)
    dev_deps = ", ".join(f'"{dep}"' for dep in dev or ["ruff>=0.16.0"])
    return f"""
[project]
name = "example"
dependencies = [{deps}]

[dependency-groups]
dev = [{dev_deps}]
"""


BASE = _pyproject(["mcp[cli]>=2,<3", "aiohttp>=3.0.0"])


def test_unchanged_pyproject_is_no_release() -> None:
    # The common case: Dependabot touched uv.lock only.
    assert release_kind(BASE, BASE) == "none"


def test_dev_group_bump_is_no_release() -> None:
    after = _pyproject(["mcp[cli]>=2,<3", "aiohttp>=3.0.0"], dev=["ruff>=0.17.0"])
    assert release_kind(BASE, after) == "none"


def test_whitespace_only_change_is_no_release() -> None:
    after = _pyproject(["mcp[cli] >= 2, < 3", "aiohttp>=3.0.0"])
    assert release_kind(BASE, after) == "none"


def test_floor_raised_within_the_major_is_a_patch() -> None:
    after = _pyproject(["mcp[cli]>=2,<3", "aiohttp>=3.13.0"])
    assert release_kind(BASE, after) == "patch"


@pytest.mark.parametrize(
    "mcp",
    [
        "mcp[cli]>=2,<4",  # widened to admit the next major
        "mcp[cli]>=3,<4",  # moved to the next major
    ],
)
def test_crossing_a_major_is_a_minor(mcp: str) -> None:
    assert release_kind(BASE, _pyproject([mcp, "aiohttp>=3.0.0"])) == "minor"


@pytest.mark.parametrize(
    "mcp",
    [
        "mcp[cli]>=2,<3.1",  # admits 3.0 although no bound names a new major
        "mcp[cli]>=2,<=3",  # an inclusive bound at 3 admits 3.0
    ],
)
def test_a_range_admitting_a_new_major_is_a_minor(mcp: str) -> None:
    assert release_kind(BASE, _pyproject([mcp, "aiohttp>=3.0.0"])) == "minor"


def test_narrowing_within_the_major_is_a_patch() -> None:
    # `<2.9` names a different number than `<3`, but both admit only major 2.
    after = _pyproject(["mcp[cli]>=2,<2.9", "aiohttp>=3.0.0"])
    assert release_kind(BASE, after) == "patch"


def test_entries_differing_only_by_marker_are_compared_separately() -> None:
    before = _pyproject(
        ["foo>=2; sys_platform == 'win32'", "foo>=2; sys_platform == 'linux'"]
    )
    after = _pyproject(
        ["foo>=2.1; sys_platform == 'win32'", "foo>=2; sys_platform == 'linux'"]
    )
    # A dict keyed by name alone keeps only the linux entry and reports `none`.
    assert release_kind(before, after) == "patch"


@pytest.mark.parametrize(
    ("specifier", "majors"),
    [
        (">=2,<3", (2, 2)),
        (">=3.0.0", (3, None)),
        ("==2.*", (2, 2)),
        ("~=2.1", (2, 2)),
        (">3", (3, None)),
        ("==1.4.2", (1, 1)),
        (">=3,<3", None),
    ],
)
def test_admitted_majors(specifier: str, majors) -> None:
    assert admitted_majors(specifier.split(",")) == majors


def test_added_dependency_is_a_minor() -> None:
    after = _pyproject(["mcp[cli]>=2,<3", "aiohttp>=3.0.0", "astral>=3.2"])
    assert release_kind(BASE, after) == "minor"


def test_removed_dependency_is_a_minor() -> None:
    assert release_kind(BASE, _pyproject(["mcp[cli]>=2,<3"])) == "minor"


def test_names_are_normalised() -> None:
    before = _pyproject(["Foo_Bar>=1.0"])
    assert release_kind(before, _pyproject(["foo-bar>=1.2"])) == "patch"


def test_optional_dependencies_count_as_runtime() -> None:
    before = BASE + '\n[project.optional-dependencies]\nfast = ["uvloop>=0.19"]\n'
    after = BASE + '\n[project.optional-dependencies]\nfast = ["uvloop>=0.21"]\n'
    assert release_kind(before, after) == "patch"


def test_cli_prints_the_kind(tmp_path, capsys) -> None:
    before, after = tmp_path / "before.toml", tmp_path / "after.toml"
    before.write_text(BASE)
    after.write_text(_pyproject(["mcp[cli]>=3,<4", "aiohttp>=3.0.0"]))

    assert main([str(before), str(after)]) == 0
    assert capsys.readouterr().out.strip() == "minor"
