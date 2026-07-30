# Testing

## Purpose
Documents the test structure, patterns, tooling, and conventions used in the project.

## Responsibilities
- Defining test file organization and naming
- Specifying mock patterns and assertion style
- Documenting the unit/integration test split
- Listing test commands

## Non-Responsibilities
- Code style rules (see [CONVENTIONS.md](CONVENTIONS.md))
- Architecture and module boundaries (see [ARCHITECTURE.md](ARCHITECTURE.md))

## Overview

### Test Structure
```
tests/
  test_oebb_api.py              -- unit tests (mocked HTTP, runs in CI)
  test_server_json.py           -- MCP Registry publish constraints (runs in CI)
  test_oebb_api_integration.py  -- integration tests (real OeBB API, CI-excluded)
```

### Release-metadata tests
`test_server_json.py` checks `server.json` against constraints the MCP Registry only enforces at publish
time -- description length (<=100), package identifier matching `pyproject.toml`, transport and registry
type, the OIDC namespace, and the `mcp-name:` ownership marker in the README.

That timing is the point. The registry validates *after* the PyPI upload has succeeded and the tag is
pushed, and the failed job cannot be re-run (the workflow checks out the tag) nor the tag moved (PyPI
rejects a re-upload, failing the job the registry step needs). Every rejection therefore costs a version
number -- the sibling `calc-mcp-server` burned two that way on 2026-07-30. These tests move both checks
into CI, minutes before a release rather than during one.

### Test File Naming
- Unit tests: `test_<module>.py`
- Integration tests: `test_<module>_integration.py`

### Test Method Naming
- Pattern: `test_<function>_<scenario>()` with `-> None` return annotation
- Examples: `test_oebb_search_station_success`, `test_oebb_station_board_by_id`, `test_oebb_trip_search_missing_from`

### Test Organization
- Arrange-Act-Assert pattern
- Tests grouped by function with `# --- Section header ---` comment banners
- Sample data defined as module-level `SAMPLE_*` constants, not inline

### Async Testing
- `pytest-asyncio` with `asyncio_mode = "auto"` in `pyproject.toml`
- Tests still carry explicit `@pytest.mark.asyncio` decorators for clarity

### Mocking
- `unittest.mock` only (`AsyncMock`, `MagicMock`) -- no third-party mock library
- Shared `_make_session()` factory helper supports:
  - Single response
  - Response sequence (list)
  - Error injection

### Assertions
- Plain `assert` statements, no helper methods
- Error paths: `assert result == {"message": "..."}` (exact sentinel match)
- Success paths: `assert "message" not in result` first, then individual field checks

### Integration Tests
- Marked with `@pytest.mark.integration`
- Use real `aiohttp.ClientSession` against live OeBB API
- Excluded from CI: `pytest tests/ -v -m "not integration"`
- Run manually: `pytest tests/ -v -m integration`

### Commands
| Command | Scope | Runs in CI |
|---------|-------|------------|
| `pytest tests/ -v -m "not integration"` | Unit tests | Yes |
| `pytest tests/ -v -m integration` | Integration tests | No |

## Dependencies
- `pytest` -- test runner
- `pytest-asyncio` -- async test support
- `unittest.mock` (stdlib) -- mocking

## Design Decisions
- **stdlib mock over pytest-mock/responses**: keeps dev dependencies minimal for a small project.
- **Auto asyncio mode with explicit decorators**: `asyncio_mode = "auto"` avoids boilerplate, but decorators are kept for readability.
- **Integration tests excluded from CI**: avoids flaky CI from external API dependency; run manually for validation.

## Known Risks
- Unit tests only cover `oebb_api.py`; no direct unit tests for `server.py` tool handlers.
- Integration tests depend on OeBB API availability and response format stability.

## Extension Guidelines
- New unit tests: add to `test_oebb_api.py` or create `test_<module>.py` for new modules
- New integration tests: add to `test_oebb_api_integration.py` with `@pytest.mark.integration`
- Follow `test_<function>_<scenario>` naming
- Use `_make_session()` helper for mocked HTTP in unit tests
- Define sample data as `SAMPLE_*` module-level constants
