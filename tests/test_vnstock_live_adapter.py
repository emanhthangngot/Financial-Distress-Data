"""VnstockLiveAdapter contract tests (phase-04-data-plane.md).

Never hits the network: a fake ``vnstock`` module is injected via
``sys.modules`` before each call, shaped exactly like the real 4.0.7
package's return values (measured live against VNM this session — see
ADR-020). Retry/failure/checkpoint behavior is exercised against a fake
metadata sink instead of a real Postgres-backed MetadataWriter.
"""

from __future__ import annotations

import sys
import types
from typing import Any

import pandas as pd
import pytest

from src.collectors.source_adapters.vnstock_live_adapter import (
    VnstockLiveAdapter,
    VnstockUnavailableError,
    _to_dong,
)


class FakeMetadataSink:
    def __init__(self) -> None:
        self.source_requests: list[dict[str, Any]] = []
        self.failed_records: list[dict[str, Any]] = []
        self.checkpoints: list[dict[str, Any]] = []

    def log_source_request(self, **kwargs: Any) -> str:
        self.source_requests.append(kwargs)
        return "req-1"

    def log_failed_record(self, **kwargs: Any) -> None:
        self.failed_records.append(kwargs)

    def upsert_collector_checkpoint(self, **kwargs: Any) -> None:
        self.checkpoints.append(kwargs)


@pytest.fixture
def fake_vnstock(monkeypatch: pytest.MonkeyPatch):
    """Install a fake ``vnstock`` module shaped like the real 4.0.7 package."""

    module = types.ModuleType("vnstock")

    class FakeListing:
        def symbols_by_exchange(self) -> pd.DataFrame:
            return pd.DataFrame(
                [
                    {
                        "symbol": "VNM",
                        "organ_name": "CTCP Sữa Việt Nam",
                        "exchange": "HOSE",
                    },
                    {
                        "symbol": "AAA",
                        "organ_name": "AAA Corp",
                        "exchange": "HOSE",
                    },
                ]
            )

    class FakeQuote:
        def __init__(self, source: str, symbol: str) -> None:
            self.source = source
            self.symbol = symbol

        def history(self, **kwargs: Any) -> pd.DataFrame:
            # Real KBS quotes arrive in nghìn đồng (measured: VNM close ~60.3).
            return pd.DataFrame(
                [
                    {
                        "time": pd.Timestamp("2026-08-03"),
                        "open": 60.9,
                        "high": 61.0,
                        "low": 60.0,
                        "close": 60.3,
                        "volume": 6377600,
                    }
                ]
            )

    class FakeFinance:
        def __init__(self, source: str, symbol: str, period: str) -> None:
            self.source = source
            self.symbol = symbol
            self.period = period

        def balance_sheet(self) -> pd.DataFrame:
            return pd.DataFrame(
                [
                    {"item_id": "total_assets", "2026-Q2": 4.089226e13, "2026-Q1": 3.87e13},
                    {"item_id": "current_assets", "2026-Q2": 4.0e13, "2026-Q1": 3.8e13},
                    {"item_id": "current_liabilities", "2026-Q2": 1.0e13, "2026-Q1": 0.9e13},
                    {"item_id": "liabilities", "2026-Q2": 1.5e13, "2026-Q1": 1.4e13},
                    {"item_id": "owners_equity", "2026-Q2": 2.5e13, "2026-Q1": 2.4e13},
                    {"item_id": "undistributed_earnings", "2026-Q2": 5.0e12, "2026-Q1": 4.5e12},
                ]
            )

        def income_statement(self) -> pd.DataFrame:
            return pd.DataFrame(
                [
                    {"item_id": "net_sales", "2026-Q2": 1.0e13, "2026-Q1": 0.9e13},
                    {"item_id": "operating_profit_loss", "2026-Q2": 2.0e12, "2026-Q1": 1.8e12},
                    {"item_id": "interest_expenses", "2026-Q2": 1.0e11, "2026-Q1": 9.0e10},
                    {"item_id": "net_profit_loss_after_tax", "2026-Q2": 1.5e12, "2026-Q1": 1.3e12},
                ]
            )

        def cash_flow(self) -> pd.DataFrame:
            return pd.DataFrame(
                [
                    {
                        "item_id": "net_cash_inflows_outflows_from_operating_activities",
                        "2026-Q2": 1.8e12,
                        "2026-Q1": 1.6e12,
                    }
                ]
            )

    module.Listing = FakeListing
    module.Quote = FakeQuote
    module.Finance = FakeFinance
    monkeypatch.setitem(sys.modules, "vnstock", module)
    return module


def test_to_dong_multiplies_kbs_price_scale() -> None:
    """F17: KBS delivers nghìn đồng; the adapter must multiply by 1000."""
    assert _to_dong(60.3) == 60300.0


def test_to_dong_passes_through_none() -> None:
    assert _to_dong(None) is None


def test_fetch_companies_returns_real_exchange_and_name(fake_vnstock) -> None:
    adapter = VnstockLiveAdapter(min_request_delay_seconds=0)
    rows = adapter.fetch_companies()

    assert len(rows) == 2
    vnm = next(r for r in rows if r["ticker"] == "VNM")
    assert vnm["exchange"] == "HOSE"
    assert vnm["company_name"] == "CTCP Sữa Việt Nam"
    assert vnm["source_system"] == "vnstock"


def test_fetch_market_prices_normalizes_to_dong(fake_vnstock) -> None:
    adapter = VnstockLiveAdapter(min_request_delay_seconds=0)
    rows = adapter.fetch_market_prices("vnm", 2026, 2026)

    assert len(rows) == 1
    row = rows[0]
    assert row["ticker"] == "VNM"
    assert row["close_price"] == 60300.0
    assert row["open_price"] == 60900.0
    assert row["source_unit"] == "VND"


def test_fetch_financial_statements_maps_item_ids_and_stays_whole_dong(fake_vnstock) -> None:
    adapter = VnstockLiveAdapter(min_request_delay_seconds=0)
    rows = adapter.fetch_financial_statements("vnm", 2018, 2025)

    assert len(rows) == 2
    q2 = next(r for r in rows if r["report_period"] == "2026Q2")
    assert q2["total_assets"] == 4.089226e13
    assert q2["revenue"] == 1.0e13
    assert q2["ebit"] == 2.0e12
    assert q2["net_income"] == 1.5e12
    assert q2["operating_cash_flow"] == 1.8e12
    assert q2["source_unit"] == "VND"
    assert "known_from_ts" in q2


def test_fetch_financial_statements_checkpoints_per_ticker(fake_vnstock) -> None:
    sink = FakeMetadataSink()
    adapter = VnstockLiveAdapter(min_request_delay_seconds=0, metadata_sink=sink, run_id="run-1")
    adapter.fetch_financial_statements("vnm", 2018, 2025)

    assert len(sink.checkpoints) == 2  # one per period row, per current checkpoint call site
    assert all(c["checkpoint_value"] == "VNM" for c in sink.checkpoints)
    assert any(r["request_status"] == "success" for r in sink.source_requests)


def test_fetch_companies_routes_failure_to_failed_records(monkeypatch: pytest.MonkeyPatch) -> None:
    module = types.ModuleType("vnstock")

    class BrokenListing:
        def symbols_by_exchange(self) -> pd.DataFrame:
            raise RuntimeError("rate limited")

    module.Listing = BrokenListing
    monkeypatch.setitem(sys.modules, "vnstock", module)

    sink = FakeMetadataSink()
    adapter = VnstockLiveAdapter(
        min_request_delay_seconds=0, max_retries=0, retry_backoff_seconds=0, metadata_sink=sink
    )
    rows = adapter.fetch_companies()

    assert rows == []
    assert len(sink.failed_records) == 1
    assert sink.failed_records[0]["dataset_name"] == "raw_companies"
    assert "rate limited" in sink.failed_records[0]["failure_reason"]


def test_fetch_market_prices_retries_before_succeeding(monkeypatch: pytest.MonkeyPatch) -> None:
    module = types.ModuleType("vnstock")
    call_count = {"n": 0}

    class FlakyQuote:
        def __init__(self, source: str, symbol: str) -> None:
            pass

        def history(self, **kwargs: Any) -> pd.DataFrame:
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise RuntimeError("transient network error")
            return pd.DataFrame(
                [
                    {
                        "time": pd.Timestamp("2026-08-03"),
                        "open": 1.0,
                        "high": 1.0,
                        "low": 1.0,
                        "close": 1.0,
                        "volume": 1,
                    }
                ]
            )

    module.Quote = FlakyQuote
    monkeypatch.setitem(sys.modules, "vnstock", module)

    adapter = VnstockLiveAdapter(
        min_request_delay_seconds=0, max_retries=2, retry_backoff_seconds=0
    )
    rows = adapter.fetch_market_prices("VNM", 2026, 2026)

    assert call_count["n"] == 2
    assert len(rows) == 1


def test_missing_vnstock_package_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "vnstock", None)  # simulates ModuleNotFoundError on import
    adapter = VnstockLiveAdapter()
    with pytest.raises(VnstockUnavailableError, match="not installed"):
        adapter.fetch_companies()
