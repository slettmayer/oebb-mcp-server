# Releasing

> How a version gets published, and where the changelog fits. Read this before cutting a release or
> changing `auto-release.yml` / `release.yml`.

## The version lives in git, not the source tree

`hatch-vcs` derives the version from the git tag. There is **no** version string to edit — no
`__version__` literal, no `version =` in `pyproject.toml`. `src/oebb_mcp_server/_version.py` is generated
at build time and gitignored.

Consequence: **creating the tag is the release.** Everything else follows from it.

## Writing changelog entries

Add entries under `## Unreleased` in `CHANGELOG.md` as work lands, in the same PR as the change. Say what
changed and why it mattered; the diff already shows the how.

You do **not** rename `## Unreleased` yourself — the release workflow does it (see below). Renaming it by
hand is harmless (the script detects an existing section and leaves it alone), but unnecessary.

A `Changelog reminder` job warns when a PR touches `src/` without touching `CHANGELOG.md`. It is advisory:
it never blocks a merge, and it skips Dependabot PRs and anything labelled `no-changelog`.

## Cutting a release

Run the **Auto Release** workflow via `workflow_dispatch`:

- leave `version` empty → bumps the patch from the highest existing tag
- set `version` (e.g. `v0.3.0`) → releases exactly that, for a deliberate minor or major

The workflow then:

1. resolves and validates the version, failing if that tag already exists
2. runs `scripts/changelog_release.py`, which moves the `## Unreleased` entries under
   `## <version> - <date>` and appends a `- Build:` line per Dependabot commit since the last tag
3. commits `CHANGELOG.md` to `main` — only if it actually changed
4. tags **that** commit and pushes

Step 4's order matters: the tag must point at the commit containing the changelog, or every release ships
without its own section.

Pushing the `v*` tag triggers **Release**, which builds, verifies the tag matches the built version,
publishes to PyPI via Trusted Publishing, creates the GitHub Release, and publishes to the MCP Registry.
`server.json`'s version is rewritten from the tag at publish time, so the `0.1.0` in the committed file is
a placeholder and does not need updating.

## What Dependabot triggers

Merging a Dependabot PR from the **`uv`** ecosystem (`dependabot/uv/*`) auto-cuts a patch release — those
change the published package. **`github-actions`** bumps do not; they merge without releasing.

This automation is why `CHANGELOG.md` once drifted: it tagged releases without touching the changelog, so
0.1.2 and 0.1.3 were published with no section. Step 2 above is what closes that.

## Changing the changelog script

`scripts/changelog_release.py` is covered by `tests/test_changelog_release.py`, which fakes git so no
repository fixture is needed. Run `pytest tests/test_changelog_release.py`.

Two non-obvious constraints are pinned by tests — don't regress them:

- the `## Unreleased` match is **line-anchored**, because this file's own preamble mentions the heading in
  prose and a plain substring match rewrites the prose instead
- the author filter is `dependabot`, **not** `dependabot[bot]`, because `git log --author=` takes a regex
  where `[bot]` is a character class that matches no commit at all

## If `main` becomes protected

The release workflow pushes a commit directly to `main`. `main` is unprotected today. If branch protection
is added, the GitHub App used by `auto-release.yml` needs bypass permission, or releases will start failing
at step 3.
