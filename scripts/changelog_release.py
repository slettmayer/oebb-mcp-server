"""Move `## Unreleased` entries into a released version section.

Invoked by `.github/workflows/auto-release.yml` immediately before it commits and
tags a release, so that every published version gets a changelog section without
anyone having to remember the rename. See docs/tech/RELEASING.md.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

# Dependabot authors its commits even through a squash merge, so the author is a
# reliable key where the subject prefix is not (the two repos differ there).
#
# Deliberately just "dependabot", not "dependabot[bot]": `git log --author=` takes
# a regex, so the brackets would form a character class and match nothing at all.
# A bare substring avoids depending on which regex flavour git is using.
DEPENDABOT_AUTHOR = "dependabot"

GitRunner = Callable[[list[str]], str]

# Dependabot's conventional-commit prefixes. The two repos differ (`chore(deps):`
# vs `build(deps):`), which is why commits are matched by author, not subject.
_DEPS_PREFIX = re.compile(r"^(?:chore|build)\(deps(?:-dev)?\):\s*")
_PR_SUFFIX = re.compile(r"\s*\(#\d+\)\s*$")

UNRELEASED = "## Unreleased"
# Anchored to a line: the changelog preamble mentions `## Unreleased` inline, and
# a plain substring match rewrites that prose instead of the heading.
_UNRELEASED_HEADING = re.compile(rf"^{re.escape(UNRELEASED)}[ \t]*$", re.MULTILINE)
_ANY_HEADING = re.compile(r"^## ", re.MULTILINE)

# Written when a release has neither human entries nor dependabot commits, so
# that a published version never ends up with an empty section.
FALLBACK_ENTRY = "- Build: dependency updates."


class ChangelogError(Exception):
    """The changelog does not match the structure this script requires."""


def _build_entry(subject: str) -> str:
    """Format a dependabot commit subject as a changelog `- Build:` entry."""
    text = _PR_SUFFIX.sub("", subject.strip())
    text = _DEPS_PREFIX.sub("", text)
    if text:
        text = text[0].lower() + text[1:]
    if not text.endswith("."):
        text += "."
    return f"- Build: {text}"


def release_changelog(
    text: str,
    *,
    version: str,
    date: str,
    dependabot_subjects: list[str],
) -> str:
    """Return `text` with `## Unreleased` renamed to a released version section."""
    number = version.removeprefix("v")

    heading = _UNRELEASED_HEADING.search(text)
    if heading is None:
        raise ChangelogError(f"no '{UNRELEASED}' heading found in CHANGELOG.md")

    # Idempotent: a human may already have written the section in the release PR.
    if re.search(rf"^## {re.escape(number)}\b", text, re.MULTILINE):
        return text

    head = text[: heading.start()]
    after = text[heading.end() :]

    # The Unreleased body runs to the next `## ` heading, or to EOF if it is last.
    following = _ANY_HEADING.search(after)
    body, tail = (
        (after[: following.start()], after[following.start() :])
        if following
        else (after, "")
    )

    lines = [
        line for line in (body.strip(), *map(_build_entry, dependabot_subjects)) if line
    ]
    entries = "\n".join(lines) or FALLBACK_ENTRY

    return f"{head}{UNRELEASED}\n\n## {number} - {date}\n\n{entries}\n\n{tail}"


def run_git(args: list[str], *, repo_root: Path | None = None) -> str:
    """Run a git command in `repo_root` and return its stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def read_dependabot_subjects(git: GitRunner) -> list[str]:
    """Return dependabot commit subjects since the latest `v*` tag."""
    tags = git(["tag", "-l", "v*", "--sort=-v:refname"]).split()
    # With no tag yet there is no baseline to diff against, and an empty
    # `..HEAD` range is a git error — scan all history instead.
    revision_range = [f"{tags[0]}..HEAD"] if tags else []

    log = git(
        [
            "log",
            *revision_range,
            f"--author={DEPENDABOT_AUTHOR}",
            "--format=%s",
        ]
    )
    return [line for line in log.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    """Rewrite CHANGELOG.md in place for a release. Returns an exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="release version, e.g. v0.4.0")
    parser.add_argument(
        "--date", help="release date (YYYY-MM-DD); defaults to today in UTC"
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path("."), help="repository root"
    )
    args = parser.parse_args(argv)

    changelog = args.repo_root / "CHANGELOG.md"
    date = args.date or datetime.now(UTC).strftime("%Y-%m-%d")

    try:
        updated = release_changelog(
            changelog.read_text(),
            version=args.version,
            date=date,
            dependabot_subjects=read_dependabot_subjects(
                lambda a: run_git(a, repo_root=args.repo_root)
            ),
        )
    except (ChangelogError, OSError, subprocess.CalledProcessError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    changelog.write_text(updated)
    print(f"CHANGELOG.md prepared for {args.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
