# Tech Stack

## Purpose
Documents the languages, frameworks, build tools, and key libraries used in this project.

## Responsibilities
- Defining the runtime and language requirements
- Listing framework choices and their architectural roles
- Documenting build, lint, and test tooling
- Tracking external API dependencies

## Non-Responsibilities
- Project structure and module boundaries (see [ARCHITECTURE.md](ARCHITECTURE.md))
- Code style and naming rules (see [CONVENTIONS.md](CONVENTIONS.md))
- Test patterns and commands (see [TESTING.md](TESTING.md))

## Overview

### Language
- Python 3.12+ -- `requires-python = ">=3.12"` in `pyproject.toml`
- `.python-version` pins local development to 3.12, the version CI installs. Without it `uv` picks the
  newest interpreter on the machine, so local and CI diverge silently -- stdlib `math` error messages
  were reworded after 3.12, for instance, so a test asserting on them passes locally and fails in CI
- `from __future__ import annotations` required in every file

### Framework
- **MCPServer** (`mcp[cli]`, the Python SDK's high-level server API) -- exposes Python async functions as Model Context Protocol tools over stdio transport. Tools registered via `@mcp.tool()` decorator. The framework handles MCP protocol serialization, tool schema generation from type hints/docstrings, and transport lifecycle. `@mcp.tool()` returns the plain undecorated function, so tools stay directly callable/testable.

### Build and Environment
- **Hatchling** -- PEP 517 build backend declared in `pyproject.toml`
- **uv** -- environment and dependency management (`uv sync`); also the recommended runtime launcher (`uvx`)

### Linting and Formatting
- **ruff** -- single tool for both linting and formatting; configured in `pyproject.toml`
- Rule sets enabled: `E` (pycodestyle errors), `W` (pycodestyle warnings), `F` (pyflakes), `I` (isort), `UP` (pyupgrade), `B` (flake8-bugbear), `SIM` (flake8-simplify)
- Max line length: 88 characters (Black-compatible)
- Target version: Python 3.12

### HTTP Client
- **aiohttp** -- async HTTP client for all outbound requests to OeBB Scotty API
- `asyncio.timeout` (stdlib, Python 3.11+) for timeout enforcement -- no `async_timeout` shim

### External API
- **OeBB Scotty API** (`https://fahrplan.oebb.at/bin/mgate.exe`) -- HAFAS-based reverse-engineered JSON API. Sole data source. No official documentation exists.
- Wire format: proprietary JSON-RPC-like envelope (`svcReqL`/`svcResL`), standard HAFAS method names (`LocMatch`, `StationBoard`, `TripSearch`, `HimSearch`)
- Authentication: hardcoded AID token

### CI/CD
- **GitHub Actions** -- defined in `.github/workflows/validate.yml`
- Triggers: push to `main` and all pull requests
- Jobs: `ruff` (lint + format check), `test` (unit tests only), `gate` (fan-in that fails if either prior job fails)
- The `test` job installs via `uv sync --locked`, so it uses the committed `uv.lock` exactly and fails if
  the lock has drifted from `pyproject.toml`. This is what makes Dependabot's `uv.lock` bumps meaningful --
  an unlocked install would silently resolve different versions than the ones under review.
- Integration tests are excluded from CI

### No Infrastructure
No Docker, Kubernetes, Terraform, or cloud platform configuration. Distributed as a PyPI package, run locally via `uvx`.

## Dependencies
- Runtime: `mcp[cli]>=2,<3`, `aiohttp>=3.0.0`
- The `mcp` major is bounded (`<3`) because the SDK breaks its high-level server API across majors:
  **mcp 2.0.0** (2026-07-28) removed `mcp.server.fastmcp` and replaced `FastMCP` with
  `mcp.server.MCPServer`. Bump the bound deliberately, not via Dependabot -- see the
  [migration guide](https://py.sdk.modelcontextprotocol.io/migration/).
- Dev: `ruff`, `pytest`, `pytest-asyncio` -- all in the `dev` group and pinned by `uv.lock`, so CI lints
  and tests with the same versions used locally
- External: OeBB Scotty API (HAFAS)

## Design Decisions
- **uv over pip/poetry**: chosen for speed and deterministic resolution. Enables `uvx` one-command server launch.
- **aiohttp over httpx**: project predates httpx adoption; aiohttp provides mature async HTTP client.
- **ruff as sole linter/formatter**: replaces Black, isort, flake8, and multiple plugins with a single fast tool.
- **No local datastore**: all data is fetched live from OeBB API per request; no caching layer.

## Known Risks
- OeBB Scotty API is reverse-engineered and undocumented -- response structure may change without notice.
- Hardcoded auth token in `const.py` -- if OeBB rotates the token, the server breaks.
- No connection pooling -- a new `aiohttp.ClientSession` is created per tool call.

## Extension Guidelines
- Add new Python dependencies to `pyproject.toml` under `[project.dependencies]`, then `uv sync`.
- Add new dev dependencies under `[project.optional-dependencies]` or `[dependency-groups]`.
- New ruff rules: add to the `select` list in `[tool.ruff.lint]`.
