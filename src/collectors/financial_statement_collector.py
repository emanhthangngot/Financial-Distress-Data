from __future__ import annotations

from src.collectors.source_adapters.vnstock_adapter import VnstockFixtureAdapter
from src.metadata.metadata_writer import MetadataWriter


def collect_financial_statements(
    tickers: list[str],
    start_year: int,
    end_year: int,
    adapter: VnstockFixtureAdapter | None = None,
    metadata: MetadataWriter | None = None,
) -> list[dict]:
    adapter = adapter or VnstockFixtureAdapter()
    rows: list[dict] = []
    for ticker in tickers:
        rows.extend(adapter.fetch_financial_statements(ticker, start_year, end_year))
    if metadata is not None:
        metadata.log_run(
            "collect_financial_statement_api",
            "call_financial_statement_api",
            "financial_statements",
            "success",
            output_rows=len(rows),
        )
    return rows
