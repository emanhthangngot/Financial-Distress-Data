"""
Live vnstock adapter for the financial-distress pipeline.

Wraps the vnstock Python SDK to fetch real Vietnamese market data (company list, financial
statements, market prices) and yield records in the common schema. Disabled by default; the fixture
adapter is used in CI and during Phase 1 local development.
"""

from __future__ import annotations

from src.collectors.source_adapters.vnstock_fixture_adapter import VnstockFixtureAdapter

__all__ = ["VnstockFixtureAdapter"]
