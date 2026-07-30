"""
Collector for OHLCV market price history.

Fetches daily market prices for each ticker in the company master and writes them to
``bronze/market_price/`` partitioned by exchange and trade_date. The streaming variant emits price
ticks into Kafka.
"""

from __future__ import annotations

from src.collectors.source_adapters.vnstock_fixture_adapter import VnstockFixtureAdapter
from src.metadata.metadata_writer import MetadataWriter


def collect_market_prices(
    tickers: list[str],
    start_year: int,
    end_year: int,
    adapter: VnstockFixtureAdapter | None = None,
    metadata: MetadataWriter | None = None,
) -> list[dict]:
    adapter = adapter or VnstockFixtureAdapter()
    rows: list[dict] = []
    for ticker in tickers:
        rows.extend(adapter.fetch_market_prices(ticker, start_year, end_year))
    if metadata is not None:
        metadata.log_run(
            "collect_market_price_api",
            "call_historical_price_api",
            "market_prices_daily",
            "success",
            output_rows=len(rows),
        )
    return rows
