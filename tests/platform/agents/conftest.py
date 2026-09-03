"""Keep platform .gent tests isolated from the Phase 1-only environment."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "pydantic",
    reason="platform .gent tests require .venv-phase2; the Stage 1 .venv stays dependency-clean",
)
pytest.importorskip(
    "httpx",
    reason="platform .gent tests require .venv-phase2; the Stage 1 .venv stays dependency-clean",
)
