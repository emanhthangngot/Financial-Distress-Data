"""Keep platform agent tests isolated from the platform-only environment."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "pydantic",
    reason="platform agent tests require .venv-platform; the platform .venv stays dependency-clean",
)
pytest.importorskip(
    "httpx",
    reason="platform agent tests require .venv-platform; the platform .venv stays dependency-clean",
)
