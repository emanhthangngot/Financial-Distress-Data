"""
Live vnstock adapter for the financial-distress pipeline.

Re-exports VnstockLiveAdapter (the real implementation, src/collectors/source_adapters/
vnstock_live_adapter.py) and VnstockFixtureAdapter (the CI/default path). Disabled by default —
``configs/collector_config.yaml``'s ``source_mode: online`` declares intent, but callers must
explicitly instantiate VnstockLiveAdapter to use it; nothing in this module makes a network call
at import time.
"""

from __future__ import annotations

from src.collectors.source_adapters.vnstock_fixture_adapter import VnstockFixtureAdapter
from src.collectors.source_adapters.vnstock_live_adapter import (
    VnstockLiveAdapter,
    VnstockUnavailableError,
)

__all__ = ["VnstockFixtureAdapter", "VnstockLiveAdapter", "VnstockUnavailableError"]
