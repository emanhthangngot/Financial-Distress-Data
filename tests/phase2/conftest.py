"""Keep Phase 2 tests out of the Phase 1-only environment."""

from __future__ import annotations

import importlib.util
from pathlib import Path

PHASE2_ROOT = Path(__file__).resolve().parent
PHASE2_AVAILABLE = importlib.util.find_spec("pydantic") is not None


def pytest_ignore_collect(collection_path: Path, config) -> bool:
    """Use ``.venv-phase2`` for Phase 2 tests without mutating ``.venv``."""
    del config
    path = Path(collection_path).resolve()
    return not PHASE2_AVAILABLE and (path == PHASE2_ROOT or PHASE2_ROOT in path.parents)
