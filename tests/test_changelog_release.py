"""Tests for scripts/changelog_release.py.

Git access is injected, so no repository fixture is needed: each test passes the
dependabot commit subjects it wants the script to see.
"""

from __future__ import annotations

import re

import pytest
from changelog_release import (
    ChangelogError,
    read_dependabot_subjects,
    release_changelog,
)

BASE = """# Changelog

Add entries under `## Unreleased` as you go. This preamble mentions the heading
inline on purpose: the real changelogs do, and a naive substring match rewrites
the prose instead of the heading.

## Unreleased

- Fixed: something a human wrote.

## 0.1.0 - 2026-07-01

- Initial release
"""


def test_renames_unreleased_to_version_keeping_human_entries() -> None:
    result = release_changelog(
        BASE, version="v0.2.0", date="2026-07-29", dependabot_subjects=[]
    )

    assert "## 0.2.0 - 2026-07-29" in result
    assert "- Fixed: something a human wrote." in result
    # The human entry moved under the new version, not left under Unreleased.
    unreleased_body = result.split("## Unreleased")[1].split("## ")[0]
    assert "human wrote" not in unreleased_body


def test_normalizes_dependabot_subject_into_build_entry() -> None:
    result = release_changelog(
        BASE,
        version="v0.2.0",
        date="2026-07-29",
        dependabot_subjects=[
            "chore(deps): Bump aiohttp in the python-dependencies group (#14)"
        ],
    )

    assert "- Build: bump aiohttp in the python-dependencies group." in result


def test_strips_build_deps_prefix_too() -> None:
    # geosphere's dependabot uses `build(deps):` where oebb's uses `chore(deps):`.
    result = release_changelog(
        BASE,
        version="v0.2.0",
        date="2026-07-29",
        dependabot_subjects=["build(deps): Bump astral-sh/setup-uv (#12)"],
    )

    assert "- Build: bump astral-sh/setup-uv." in result


def test_is_a_noop_when_the_version_section_already_exists() -> None:
    # A human may have written the section by hand in the release PR; the
    # workflow must not duplicate it.
    already = BASE.replace(
        "## Unreleased", "## Unreleased\n\n## 0.2.0 - 2026-07-29\n\n- Done."
    )

    result = release_changelog(
        already,
        version="v0.2.0",
        date="2026-07-29",
        dependabot_subjects=["chore(deps): Bump x (#1)"],
    )

    assert result == already


def test_falls_back_to_a_generic_line_when_there_is_nothing_to_say() -> None:
    empty = (
        "# Changelog\n\n## Unreleased\n\n## 0.1.0 - 2026-07-01\n\n- Initial release\n"
    )

    result = release_changelog(
        empty, version="v0.1.1", date="2026-07-29", dependabot_subjects=[]
    )

    assert "- Build: dependency updates." in result


def test_rejects_a_changelog_with_no_unreleased_heading() -> None:
    with pytest.raises(ChangelogError, match="Unreleased"):
        release_changelog(
            "# Changelog\n\n## 0.1.0 - 2026-07-01\n",
            version="v0.2.0",
            date="2026-07-29",
            dependabot_subjects=[],
        )


def test_keeps_human_entries_before_generated_build_entries() -> None:
    result = release_changelog(
        BASE,
        version="v0.2.0",
        date="2026-07-29",
        dependabot_subjects=["chore(deps): Bump aiohttp (#14)"],
    )

    assert result.index("human wrote") < result.index("- Build: bump aiohttp.")


class FakeGit:
    """Records the git argument lists it is asked to run, returns canned stdout."""

    def __init__(self, *, tags: str = "", log: str = "") -> None:
        self.calls: list[list[str]] = []
        self._tags = tags
        self._log = log

    def __call__(self, args: list[str]) -> str:
        self.calls.append(args)
        return self._log if args[0] == "log" else self._tags


def test_reads_dependabot_subjects_from_the_range_since_the_latest_tag() -> None:
    git = FakeGit(
        tags="v0.2.0\nv0.1.3\n",
        log="chore(deps): Bump aiohttp (#14)\nfix: not dependabot (#15)\n",
    )

    subjects = read_dependabot_subjects(git)

    assert "v0.2.0..HEAD" in git.calls[-1]
    assert subjects == ["chore(deps): Bump aiohttp (#14)", "fix: not dependabot (#15)"]


def test_scans_all_history_when_no_tag_exists_yet() -> None:
    git = FakeGit(tags="", log="")

    read_dependabot_subjects(git)

    # No revision range: an empty `<tag>..HEAD` would be a git error.
    assert not any(".." in arg for arg in git.calls[-1])


def test_author_filter_actually_matches_a_real_dependabot_author() -> None:
    # `git log --author=` takes a REGEX, so a literal `dependabot[bot]` is a
    # character class matching b/o/t and silently matches no commit at all.
    # Asserting the arg merely *contains* the name would not catch that.
    real_author = "dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>"
    git = FakeGit(tags="v0.1.0\n")

    read_dependabot_subjects(git)

    author_arg = next(a for a in git.calls[-1] if a.startswith("--author="))
    assert re.search(author_arg.removeprefix("--author="), real_author)


def test_rewrites_the_heading_not_a_prose_mention_of_it() -> None:
    result = release_changelog(
        BASE, version="v0.2.0", date="2026-07-29", dependabot_subjects=[]
    )

    # The preamble sentence must be untouched.
    assert "Add entries under `## Unreleased` as you go." in result
    # And exactly one new version heading, at the start of a line.
    assert len(re.findall(r"^## 0\.2\.0 - 2026-07-29$", result, re.MULTILINE)) == 1
