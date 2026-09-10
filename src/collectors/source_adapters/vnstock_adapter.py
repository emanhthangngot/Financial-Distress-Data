"""
Live vnstock adapter for the financial-distress pipeline.

Re-exports VnstockLiveAdapter (the real implementation in
``vnstock_live_adapter.py``) and VnstockFixtureAdapter (the CI/default path). The checked-in
``configs/collector_config.yaml`` is the default mode; ``COLLECTOR_SOURCE_MODE`` overrides it.
Nothing in this module makes a network call at import time.
"""

from __future__ import annotations

from src.collectors.source_adapters.vnstock_fixture_adapter import VnstockFixtureAdapter
from src.collectors.source_adapters.vnstock_live_adapter import (
    VnstockLiveAdapter,
    VnstockUnavailableError,
)

__all__ = ["VnstockFixtureAdapter", "VnstockLiveAdapter", "VnstockUnavailableError"]


def build_source_adapter(
    *,
    source_mode: str | None = None,
    metadata_sink: object | None = None,
    run_id: str | None = None,
) -> VnstockFixtureAdapter | VnstockLiveAdapter:
    """Build the configured adapter without making a network call at import time.

    ``fixture`` remains the safe default for tests and local evidence. Manual/live
    runs opt in with ``COLLECTOR_SOURCE_MODE=online`` or an explicit argument.
    """
    import os
    from pathlib import Path

    if source_mode is None:
        source_mode = os.getenv("COLLECTOR_SOURCE_MODE")
    if source_mode is None:
        config_path = Path("configs/collector_config.yaml")
        try:
            import yaml

            raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            source_mode = raw_config.get("source_mode")
        except (FileNotFoundError, OSError, ValueError):
            source_mode = None
    mode = (source_mode or "fixture").lower()
    if mode in {"online", "live"}:
        return VnstockLiveAdapter(metadata_sink=metadata_sink, run_id=run_id)
    if mode == "fixture":
        return VnstockFixtureAdapter()
    raise ValueError(f"Unsupported collector source mode: {mode!r}")
