"""Keep platform .gent tests isolated from the platform-only environment."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "pydantic",
    reason="platform .gent tests require .venv-platform; the platform .venv stays dependency-clean",
)
pytest.importorskip(
    "httpx",
    reason="platform .gent tests require .venv-platform; the platform .venv stays dependency-clean",
)
