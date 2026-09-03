"""Keep platform .ests out of the Phase 1-only environment."""

from __future__ import annotations

import importlib.util
from pathlib import Path

PLATFORM_ROOT = Path(__file__).resolve().parent
PLATFORM_AVAILABLE = importlib.util.find_spec("pydantic") is not None


def pytest_ignore_collect(collection_path: Path, config) -> bool:
    """Use ``.venv-phase2`` for platform .ests without mutating ``.venv``."""
    del config
    path = Path(collection_path).resolve()
    return not PLATFORM_AVAILABLE and (path == PLATFORM_ROOT or PLATFORM_ROOT in path.parents)
