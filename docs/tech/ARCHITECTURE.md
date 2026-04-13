# Architecture

## Purpose
Documents the project structure, module boundaries, layering, and data flow.

## Responsibilities
- Defining the architectural pattern and module layout
- Describing data flow across layers
- Specifying module boundaries and ownership
- Documenting session and lifecycle management

## Non-Responsibilities
- Technology choices and library details (see [TECH-STACK.md](TECH-STACK.md))
- Naming and code style rules (see [CONVENTIONS.md](CONVENTIONS.md))
- Domain concepts and terminology (see [../domain/OVERVIEW.md](../domain/OVERVIEW.md))

## Overview

### Architectural Pattern
Thin adapter: a FastMCP presentation layer wrapping a pure async HTTP client. Purely functional -- no classes outside the `FastMCP` instance. Data flows as plain `dict[str, Any]` throughout; no domain model objects.

### Project Structure
```
src/oebb_mcp_server/
  __init__.py          -- version string only
  server.py            -- FastMCP tool registration, session lifecycle, entry point
  oebb_api.py          -- pure async HTTP client (independently testable)
  const.py             -- all constants (endpoint, auth, config)
tests/
  test_oebb_api.py              -- unit tests (mocked HTTP)
  test_oebb_api_integration.py  -- integration tests (real API, CI-excluded)
```

One module per responsibility. No sub-packages.

### Module Boundaries

**`server.py` (Presentation Layer)**
- Owns: MCP tool registration via `@mcp.tool()`, `aiohttp.ClientSession` lifecycle (created per tool call via `async with`), JSON serialization of results
- Does not own: HTTP communication, request construction, response parsing
- Calls: `oebb_api.async_oebb_*()` functions, passing in the session

**`oebb_api.py` (Data Access Layer)**
- Owns: all HTTP communication with OeBB Scotty API, HAFAS request envelope construction, response parsing and normalization, station name-to-ID resolution
- Does not own: session creation/teardown, MCP protocol concerns
- Public functions: `async_oebb_search_station`, `async_oebb_station_board`, `async_oebb_trip_search`, `async_oebb_service_alerts`
- Private helpers: `_async_loc_match`, `_async_resolve_station`, `_build_request_body`, `_format_oebb_time`, `_format_oebb_date`

**`const.py` (Configuration)**
- Owns: all literal values -- API endpoint URL, auth token, client identity fields, API version, language, timeout
- Zero magic values exist in `server.py` or `oebb_api.py`

### Data Flow
```
LLM client
  -> stdio transport
    -> FastMCP framework (server.py)
      -> @mcp.tool() handler creates aiohttp.ClientSession
        -> async_oebb_*() in oebb_api.py
          -> POST JSON to OeBB Scotty mgate.exe
          -> Parse svcResL response
        <- dict[str, Any] (success) or {"message": "..."} (error)
      <- JSON string (indented) as MCP tool result
    <- MCP protocol response
  <- LLM receives tool result
```

When station names (not IDs) are provided, a preliminary `_async_loc_match` call resolves the name to a HAFAS `lid` before the primary API call.

### Session Management
- `aiohttp.ClientSession` is created per-tool-call in `server.py` using `async with`
- The session is passed into every `oebb_api` function as a parameter
- The API module never creates or owns a session
- No session reuse or connection pooling across calls

### Error Signaling
- Errors are communicated as sentinel dicts: `{"message": "<reason>"}`
- No exceptions are raised across module boundaries
- Callers in `server.py` pass results directly to `_format_result()` without checking
- Categories: `TimeoutError` -> `"Timeout"`, `aiohttp.ClientError` -> `"No data"`, API errors -> `errTxt` from response, station not found -> descriptive message

## Dependencies
- `server.py` depends on `oebb_api.py` and `const.py`
- `oebb_api.py` depends on `const.py`, `aiohttp`, `asyncio`
- `const.py` has no internal dependencies
- No circular dependencies exist

## Design Decisions
- **Dicts over dataclasses**: data flows as plain dicts for simplicity; the project is small enough that formal models add overhead without benefit. Rationale not documented -- needs team input if the project grows.
- **Per-call sessions**: each tool invocation creates a fresh `aiohttp.ClientSession`. Simplifies lifecycle management at the cost of connection reuse.
- **Sentinel dicts over exceptions**: error signaling via `{"message": "..."}` avoids exception handling complexity in the thin server layer. Every public function has the same return type.
- **No caching**: all data is fetched live per request. Appropriate for a real-time transit data server.

## Known Risks
- Per-call session creation prevents HTTP connection reuse; may become a performance concern under high call volume.
- All data flows as untyped dicts -- no compile-time guarantees on response shape.
- Single flat package structure may not scale if the project grows significantly.

## Extension Guidelines
- New MCP tools: add `@mcp.tool()` function in `server.py`, corresponding `async_oebb_*()` in `oebb_api.py`
- New API methods: add to `oebb_api.py` following the existing pattern (build request, POST, parse response, return dict or sentinel)
- New constants: add to `const.py` with `OEBB_` prefix
- If the project grows beyond 5-6 modules, consider introducing sub-packages by responsibility
