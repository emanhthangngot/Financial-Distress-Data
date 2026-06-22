"""
Collector for the company master dimension.

Pulls the list of Vietnamese listed companies (ticker, exchange, sector, listing date) from the
configured source adapter and writes raw records to the Bronze zone under
``bronze/company_master/``.
"""

from __future__ import annotations

from src.collectors.source_adapters.vnstock_fixture_adapter import VnstockFixtureAdapter
from src.metadata.metadata_writer import MetadataWriter


def collect_companies(
    adapter: VnstockFixtureAdapter | None = None, metadata: MetadataWriter | None = None
) -> list[dict]:
    adapter = adapter or VnstockFixtureAdapter()
    rows = adapter.fetch_companies()
    if metadata is not None:
        metadata.log_run(
            "collect_company_master_data",
            "fetch_company_list_from_primary_source",
            "companies",
            "success",
            output_rows=len(rows),
        )
    return rows
