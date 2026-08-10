"""Keep Phase 2 agent tests isolated from the Phase 1-only environment."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "pydantic",
    reason="Phase 2 agent tests require .venv-phase2; the Stage 1 .venv stays dependency-clean",
)
pytest.importorskip(
    "httpx",
    reason="Phase 2 agent tests require .venv-phase2; the Stage 1 .venv stays dependency-clean",
)
