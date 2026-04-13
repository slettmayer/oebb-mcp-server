# Conventions

## Purpose
Documents naming patterns, code style, import ordering, error handling, and logging conventions.

## Responsibilities
- Defining naming rules for files, functions, constants, and variables
- Specifying code style requirements
- Documenting error handling and logging patterns
- Establishing import ordering rules

## Non-Responsibilities
- Architecture and module boundaries (see [ARCHITECTURE.md](ARCHITECTURE.md))
- Technology choices (see [TECH-STACK.md](TECH-STACK.md))
- Test-specific conventions (see [TESTING.md](TESTING.md))

## Overview

### File Naming
- Source files: `snake_case.py`
- Module names match their responsibility: `server`, `oebb_api`, `const`

### Function Naming
| Category | Pattern | Example |
|----------|---------|---------|
| Public async | `async_oebb_<verb>_<noun>` | `async_oebb_search_station` |
| Private async | `_async_<verb>_<noun>` | `_async_loc_match` |
| Private sync | `_<verb>_<noun>` | `_build_request_body` |
| MCP tools | `<verb>_<noun>` (no prefix) | `search_station`, `trip_search` |

### Variable Naming
- `snake_case` for all variables
- Plural for collections: `stations`, `journeys`, `connections`, `legs`, `alerts`
- `*_count` suffix for totals: `results_count`, `journeys_count`

### Constants
- `UPPER_SNAKE_CASE` with `OEBB_` prefix: `OEBB_API_ENDPOINT`, `OEBB_AUTH_AID`
- All constants live exclusively in `const.py` -- no inline magic values anywhere
- Test fixture data uses `SAMPLE_*` prefix

### Logger
- One per module: `_LOGGER = logging.getLogger(__name__)`
- Always `%s`-style formatting, never f-strings: `_LOGGER.warning("Error: %s", msg)`
- Log levels: `error` for infrastructure failures (timeout, network), `warning` for logical/API failures

### Imports
Strict ordering enforced by ruff `I` rule:
1. `from __future__ import annotations` (mandatory in every file)
2. Standard library
3. Third-party packages
4. Local imports

### Type Annotations
- Full annotations on all function signatures
- Lowercase built-in generics: `dict[str, Any]`, `list[str]` (enabled by `from __future__ import annotations`)

### Code Style
- 4-space indentation (PEP 8)
- 88-character max line length (Black-compatible)
- Double quotes (ruff formatter default)
- `noqa` comments used sparingly for intentional suppressions (e.g., `# noqa: DTZ007` for timezone-naive datetime)

### Error Handling
- Errors signaled as sentinel dicts: `{"message": "<reason>"}`
- No exceptions raised across module boundaries
- Caught exceptions: `TimeoutError`, `aiohttp.ClientError`, bare `Exception`
- Station resolution failures return descriptive messages without logging

### Return Types
- All public `async_oebb_*` functions return `dict[str, Any]`
- Success: dict with domain keys (e.g., `stations`, `connections`)
- Error: dict with single `"message"` key
- Callers check: `"message" not in result` to distinguish success from failure

## Dependencies
- ruff enforces import ordering, line length, quote style, and pyupgrade rules
- `from __future__ import annotations` enables lowercase generics

## Design Decisions
- **Sentinel dicts over exceptions**: keeps the thin server layer free of try/except blocks. Every function has the same return type contract.
- **%s logging over f-strings**: avoids eager string interpolation; arguments are only formatted if the log level is active.
- **No custom exception hierarchy**: deliberate choice for a small project where error categories are few and well-defined.

## Known Risks
- Untyped dict returns provide no compile-time guarantees on response shape.
- Bare `Exception` catch in API client is broad; could mask unexpected errors.

## Extension Guidelines
- New functions must follow the naming pattern for their category (see table above)
- New constants go in `const.py` with `OEBB_` prefix
- All new files must start with `from __future__ import annotations`
- Run `ruff check .` and `ruff format .` before committing
