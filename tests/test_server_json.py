"""Validate `server.json` against the MCP Registry's constraints.

These run locally and in CI, minutes before a release rather than during one.
The registry only validates at publish time — which is *after* the PyPI upload
has already succeeded and the git tag is immovable, so a rejection there cannot
be fixed by re-running the job. It costs a whole version number.

That is not hypothetical. The sibling `calc-mcp-server` burned two versions to
it on 2026-07-30: 0.1.0 on `expected length <= 100` for a 116-character
description, then 0.1.1 on a missing `mcp-name:` ownership marker. Both times
PyPI and the GitHub Release succeeded and only the registry step failed.

This repo currently satisfies every check — the description is 87 characters.
These tests exist so a future edit cannot quietly cross the cap.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent

# https://registry.modelcontextprotocol.io — the publish endpoint rejects a
# longer description with a 422. The limit is not expressed in the JSON schema
# the file references, so nothing else in the toolchain catches it.
MAX_DESCRIPTION_LENGTH = 100


def _server_json() -> dict[str, Any]:
    return json.loads((REPO_ROOT / "server.json").read_text())


def _pyproject() -> dict[str, Any]:
    return tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())


def test_description_is_within_the_registry_limit() -> None:
    description = _server_json()["description"]
    assert len(description) <= MAX_DESCRIPTION_LENGTH, (
        f"server.json description is {len(description)} characters; the MCP "
        f"Registry rejects anything over {MAX_DESCRIPTION_LENGTH}"
    )


def test_package_identifier_matches_the_distribution_name() -> None:
    """A mismatch publishes a registry entry pointing at the wrong package."""
    package = _server_json()["packages"][0]
    assert package["identifier"] == _pyproject()["project"]["name"]
    assert package["registryType"] == "pypi"
    assert package["transport"]["type"] == "stdio"


def test_name_uses_the_owned_github_namespace() -> None:
    """The namespace is what the OIDC login in release.yml proves ownership of."""
    assert _server_json()["name"] == "io.github.slettmayer/oebb-mcp-server"


def test_readme_carries_the_registry_ownership_marker() -> None:
    """The registry proves PyPI ownership by finding this line in the README.

    Without it the publish fails with "ownership validation failed" — and like
    the description limit, only at publish time, after PyPI already has the
    version. It must be the README that ships in the distribution, which
    `pyproject.toml`'s `readme` field points at.
    """
    readme_name = _pyproject()["project"]["readme"]
    readme = (REPO_ROOT / readme_name).read_text()
    marker = f"mcp-name: {_server_json()['name']}"
    assert marker in readme, f"{readme_name} must contain '{marker}'"


def test_versions_agree_with_each_other() -> None:
    """Both are placeholders rewritten from the tag, but they must start equal.

    `release.yml` sets `.version` and `.packages[0].version` from the tag in one
    jq expression, so a mismatch here means the committed file drifted rather
    than that the release would ship one.
    """
    server_json = _server_json()
    assert server_json["version"] == server_json["packages"][0]["version"]
