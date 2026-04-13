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
FastMCP server wrapping a pure async OeBB API client. All code lives in `src/oebb_mcp_server/`.

- `server.py` -- FastMCP server, registers 4 tools, runs on stdio transport
- `oebb_api.py` -- pure async HTTP client for OeBB Scotty API (independently testable)
- `const.py` -- OeBB API constants (endpoint, auth, client config)

Data flow: MCP tool call -> `server.py` handler -> `oebb_api.async_oebb_*()` -> OeBB Scotty API -> JSON response -> MCP tool result.

## Tech Stack
- Python 3.12+, `from __future__ import annotations` in every file
- `mcp[cli]` (FastMCP) for MCP server framework
- `aiohttp` for async HTTP
- `ruff` for linting/formatting, `pytest` + `pytest-asyncio` for testing
- `uv` for environment management
- GitHub Actions CI (validate on push/PR)

## Core Conventions
- All async functions use `async_` prefix
- Constants in `const.py` only -- no inline magic values
- Logger: `_LOGGER = logging.getLogger(__name__)` with `%s` formatting (not f-strings)
- Import order: `__future__` -> stdlib -> third-party -> local
- Errors signaled via sentinel dict with `"message"` key, not exceptions
- OeBB Scotty API is reverse-engineered (not officially documented) -- response structure may change without notice
