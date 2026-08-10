# Changelog

The version of a release is derived from its git tag by `hatch-vcs`; there is no version string in the
source tree. Add entries under `## Unreleased` as you go — the release workflow moves them under the
version being cut, so you never rename that heading by hand. See
[docs/tech/RELEASING.md](docs/tech/RELEASING.md).

## Unreleased

## 0.2.2 - 2026-08-10

- Added: `tests/test_server_json.py` validates `server.json` against the MCP Registry's publish
  constraints -- description length, package identifier, transport, OIDC namespace, and the `mcp-name:`
  ownership marker in the README. The registry only validates at publish time, after the PyPI upload has
  succeeded and the tag is immovable, so a rejection there cannot be re-run and costs a version number;
  the sibling `calc-mcp-server` burned two that way. This repo already satisfies every check -- the tests
  stop a future edit crossing the cap.
- Added: `.python-version` pinning local development to 3.12, the version CI installs. Without it `uv`
  picks the newest interpreter present, so local and CI silently diverge -- stdlib `math` error messages
  were reworded after 3.12, so a test asserting on them passes locally and fails in CI.

- Fixed: `docs/tech/RELEASING.md` claimed `main` was unprotected. It is protected by an active repository ruleset; the earlier check used the classic branch-protection API, which returns 404 here and reads as "not protected". The release App is now a ruleset bypass actor, without which the changelog push fails `GH013`.
- Changed: `auto-release.yml` now passes `client-id` to `actions/create-github-app-token` instead of the
  deprecated `app-id`, reading a new `GH_ACTION_APP_CLIENT_ID` secret. Every run warned
  `Input 'app-id' has been deprecated`; the token it mints is what pushes the changelog commit past the
  `main` ruleset, so the input will not be left to be removed on the action's schedule.
- Build: bump ruff in the python-dependencies group.

## 0.2.1 - 2026-07-29

- Added: releases now file their own changelog section. `auto-release.yml` runs `scripts/changelog_release.py` to move `## Unreleased` entries under the version being cut and append a `- Build:` line per Dependabot commit, then commits that before tagging. Previously it tagged without touching `CHANGELOG.md`, which is why 0.1.2 and 0.1.3 were published with no section at all.
- Added: the Auto Release workflow takes an optional `version` input, so a deliberate minor or major release is one click instead of a hand-made tag. It also refuses a version whose tag already exists.
- Added: `docs/tech/RELEASING.md` — the release process was previously undocumented, which is the other half of why the changelog drifted.
- Added: an advisory `Changelog reminder` CI job that warns when a PR changes `src/` without `CHANGELOG.md`. It never blocks a merge and skips Dependabot and `no-changelog`-labelled PRs.

## 0.2.0 - 2026-07-29

- Changed: migrated to the mcp Python SDK v2 (`mcp[cli]>=2,<3`). `mcp.server.fastmcp.FastMCP` became `mcp.server.MCPServer`; the `@mcp.tool()` and `mcp.run()` surface is unchanged, and `@mcp.tool()` still returns the plain undecorated function. This lifts the temporary `<2` pin added in 0.1.3, so Dependabot can track the v2 line again.
- Fixed: the server now advertises its own package version over the wire. v1's `FastMCP` had no `version` parameter and reported the *SDK* version (`1.28.1`) as the server version; v2 added the parameter but defaults it to an empty string, so passing `__version__` explicitly is what keeps the field meaningful.
- Fixed: the CI `ruff` job now installs from the committed `uv.lock` (`ruff` moved into the `dev` dependency group) instead of an unpinned `pip install ruff`. Same class of drift as the `mcp` bug in 0.1.3: a ruff release could fail the build with no change to this repo, and CI could lint with a different version than any developer.

## 0.1.3 - 2026-07-29

- Fixed: constrained `mcp[cli]` to `>=1.28.1,<2`. The mcp 2.0.0 release (2026-07-28) reworked the SDK and removed `mcp.server.fastmcp`, so any fresh install resolved a version this server cannot import. (Superseded by the v2 migration in 0.2.0.)
- Changed: the CI `test` job now installs with `uv sync --locked` instead of `pip install -e .`. The previous command ignored the committed `uv.lock` entirely, so dependency bumps were never actually exercised by CI and unpinned upstream releases could break the build without any change to this repo.
- Build: bumped `aiohttp` to 3.14.3, plus `astral-sh/setup-uv` and two other pinned GitHub Actions.

## 0.1.2 - 2026-07-05

- Added: merging a Dependabot `uv` PR now cuts a patch release automatically (`auto-release.yml`), so dependency updates reach PyPI and the MCP Registry without a manual tag.
- Added: `workflow_dispatch` trigger on the auto-release workflow, for cutting a release by hand.
- Fixed: removed a `#` from the auto-release tag message expression, which was truncating the generated tag annotation.
- Build: relaxed the `mcp[cli]` requirement and bumped `actions/checkout`.

## 0.1.1 - 2026-07-05

First published release. The initial server was developed as 0.1.0, but no `v0.1.0` tag or PyPI artifact
exists — 0.1.1 is the first version that shipped.

- MCP server with 4 tools: `search_station`, `station_board`, `trip_search`, `service_alerts`
- Station search by name with coordinates and IDs
- Live departures/arrivals at any OeBB station
- Trip search with time planning, departure/arrival mode, and direct-only filter
- Service alerts and disruption information with product type filtering
- Fixed: the product bitmask omitted Westbahn and other private operators, so their journeys were missing from results
- First public distribution: published to [PyPI](https://pypi.org/project/oebb-mcp-server/) (installable via `uvx oebb-mcp-server`) and listed in the [official MCP Registry](https://registry.modelcontextprotocol.io)
- Tag-driven release pipeline: PyPI Trusted Publishing (OIDC), GitHub Release, and MCP Registry publish on `v*` tags
- Version single-sourced from git tags via `hatch-vcs`; added PyPI metadata (authors, URLs, classifiers, keywords) and a `py.typed` marker
- Dependabot config, with `uv.lock` tracked
