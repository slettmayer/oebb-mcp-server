# OeBB MCP Server
> MCP server for OeBB (Austrian Federal Railways) train data, usable by LLMs via the Model Context Protocol.

## Quick Reference
- **Lint**: `ruff check .`
- **Format**: `ruff format .`
- **Test (unit)**: `pytest tests/ -v -m "not integration"`
- **Test (integration, real API)**: `pytest tests/ -v -m integration`
- **Run server**: `uvx --from . oebb-mcp-server` or `python -m oebb_mcp_server.server`
- **Validate (CI)**: Ruff + pytest unit tests (all must pass via `gate` job)

## Architecture Overview
Thin adapter: MCP presentation layer wrapping a pure async OeBB API client. Purely functional, no classes. All code in `src/oebb_mcp_server/`.

- `server.py` -- MCPServer tool registration, session lifecycle, stdio entry point
- `oebb_api.py` -- pure async HTTP client for OeBB Scotty API (independently testable)
- `const.py` -- all constants (endpoint, auth, client config)

Data flow: MCP tool call -> `server.py` handler -> `oebb_api.async_oebb_*()` -> OeBB Scotty API -> JSON -> MCP tool result.

See [Architecture](docs/tech/ARCHITECTURE.md) for module boundaries and data flow detail.

## Tech Stack
- Python 3.12+, `from __future__ import annotations` in every file
- `mcp[cli]` (`mcp.server.MCPServer`) for MCP server framework -- v2 line, pinned `>=2,<3`
- `aiohttp` for async HTTP
- `ruff` for linting/formatting, `pytest` + `pytest-asyncio` for testing
- `uv` for environment management, `hatchling` build backend
- GitHub Actions CI (validate on push/PR)

See [Tech Stack](docs/tech/TECH-STACK.md) for full detail.

## Core Conventions
- All async functions use `async_` prefix; MCP tools use plain `verb_noun`
- Constants in `const.py` only -- no inline magic values
- Logger: `_LOGGER = logging.getLogger(__name__)` with `%s` formatting (not f-strings)
- Import order: `__future__` -> stdlib -> third-party -> local
- Errors signaled via sentinel dict `{"message": "..."}`, not exceptions
- OeBB Scotty API is reverse-engineered -- response structure may change without notice

See [Conventions](docs/tech/CONVENTIONS.md) for naming tables and full rules.

## Business Domain
Read-only MCP gateway to OeBB live train data. Four tools: station search, station board (departures/arrivals), trip search (connections), and service alerts (disruptions). All data fetched live from the OeBB Scotty HAFAS API with no local caching.

See [Domain Overview](docs/domain/OVERVIEW.md) for concepts, feature boundaries, and HAFAS terminology.

## Structural Risks
- OeBB Scotty API is reverse-engineered and undocumented -- breaking changes possible without notice
- Hardcoded auth token in `const.py` -- rotation requires code change
- Per-call `aiohttp.ClientSession` creation -- no connection pooling
- No unit tests for `server.py` tool handlers
- All data flows as untyped `dict[str, Any]` -- no compile-time shape guarantees

## Detailed Guides
- [Technical Context](docs/tech/README.md) -- architecture, tech stack, conventions, testing
- [Domain Context](docs/domain/README.md) -- business domain, entities, terminology, integrations
- [Documentation Guide](docs/README.md) -- how to maintain these docs
