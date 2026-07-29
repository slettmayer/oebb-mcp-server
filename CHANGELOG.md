# Changelog

## Unreleased

- Changed: migrated to the mcp Python SDK v2 (`mcp[cli]>=2,<3`). `mcp.server.fastmcp.FastMCP` became `mcp.server.MCPServer`; the `@mcp.tool()` and `mcp.run()` surface is unchanged, and `@mcp.tool()` still returns the plain undecorated function. This lifts the temporary `<2` pin below, so Dependabot can track the v2 line again.
- Fixed: the server now advertises its own package version over the wire. v1's `FastMCP` had no `version` parameter and reported the *SDK* version (`1.28.1`) as the server version; v2 added the parameter but defaults it to an empty string, so passing `__version__` explicitly is what keeps the field meaningful.
- Fixed: the CI `ruff` job now installs from the committed `uv.lock` (`ruff` moved into the `dev` dependency group) instead of an unpinned `pip install ruff`. Same class of drift as the `mcp` bug below: a ruff release could fail the build with no change to this repo, and CI could lint with a different version than any developer.
- Fixed: constrained `mcp[cli]` to `>=1.28.1,<2`. The mcp 2.0.0 release (2026-07-28) reworked the SDK and removed `mcp.server.fastmcp`, so any fresh install resolved a version this server cannot import.
- Changed: the CI `test` job now installs with `uv sync --locked` instead of `pip install -e .`. The previous command ignored the committed `uv.lock` entirely, so dependency bumps were never actually exercised by CI and unpinned upstream releases could break the build without any change to this repo.

## 0.1.0

- Initial release
- MCP server with 4 tools: `search_station`, `station_board`, `trip_search`, `service_alerts`
- Station search by name with coordinates and IDs
- Live departures/arrivals at any OeBB station
- Trip search with time planning, departure/arrival mode, and direct-only filter
- Service alerts and disruption information with product type filtering
- First public distribution: published to [PyPI](https://pypi.org/project/oebb-mcp-server/) (installable via `uvx oebb-mcp-server`) and listed in the [official MCP Registry](https://registry.modelcontextprotocol.io)
- Tag-driven release pipeline: PyPI Trusted Publishing (OIDC), GitHub Release, and MCP Registry publish on `v*` tags
- Version single-sourced from git tags via `hatch-vcs`; added PyPI metadata (authors, URLs, classifiers, keywords) and a `py.typed` marker
