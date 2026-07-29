# Changelog

## Unreleased

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
