"""Pytest configuration.

Puts `scripts/` on the import path so release tooling can be tested. Those
scripts are development tools, not part of the shipped package, so they live
outside `src/` and are not importable by default.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
