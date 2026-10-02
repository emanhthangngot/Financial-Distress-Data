"""Keep platform tests out of the platform-only environment."""

from __future__ import annotations

import importlib.util
from pathlib import Path

PLATFORM_ROOT = Path(__file__).resolve().parent
PLATFORM_AVAILABLE = all(
    importlib.util.find_spec(module) is not None for module in ("pydantic", "httpx", "hypothesis")
)


def pytest_ignore_collect(collection_path: Path, config) -> bool:
    """Use ``.venv-platform`` for platform tests without mutating ``.venv``."""
    del config
    path = Path(collection_path).resolve()
    return not PLATFORM_AVAILABLE and (path == PLATFORM_ROOT or PLATFORM_ROOT in path.parents)
