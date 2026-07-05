"""OeBB MCP Server — Austrian Federal Railways train data for LLMs."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("oebb-mcp-server")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0+unknown"
