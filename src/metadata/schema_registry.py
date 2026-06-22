"""
Lightweight schema registry for the lakehouse.

Persists canonical schemas for each Bronze, Silver, and Gold table to
``project_metadata.schema_registry``. The PySpark transforms consult this registry to widen columns
safely during schema evolution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SchemaContract:
    dataset_name: str
    schema_version: str
    required: list[str]
    nullable: list[str]


DEFAULT_CONTRACTS = {
    "companies": SchemaContract(
        "companies",
        "v1",
        ["ticker", "company_name", "exchange", "created_ts"],
        ["industry", "sector", "listing_date", "delisted_flag", "company_size"],
    ),
    "financial_statements": SchemaContract(
        "financial_statements",
        "v1",
        [
            "ticker",
            "report_period",
            "fiscal_year",
            "fiscal_quarter",
            "total_assets",
            "total_liabilities",
            "equity",
            "created_ts",
        ],
        [
            "current_assets",
            "current_liabilities",
            "revenue",
            "ebit",
            "interest_expense",
            "net_income",
            "operating_cash_flow",
            "retained_earnings",
            "statement_type",
            "report_release_date",
            "event_timestamp",
        ],
    ),
    "market_prices_daily": SchemaContract(
        "market_prices_daily",
        "v1",
        ["ticker", "trading_date", "close_price", "volume", "created_ts"],
        [
            "open_price",
            "high_price",
            "low_price",
            "market_cap",
            "shares_outstanding",
            "event_timestamp",
        ],
    ),
}


class InMemorySchemaRegistry:
    def __init__(self, contracts: dict[str, SchemaContract] | None = None) -> None:
        self.contracts = contracts or DEFAULT_CONTRACTS

    def get_current(self, dataset_name: str) -> SchemaContract:
        try:
            return self.contracts[dataset_name]
        except KeyError as exc:
            raise KeyError(f"unknown dataset contract: {dataset_name}") from exc

    def export_json(self, output_path: str | Path) -> None:
        payload: dict[str, Any] = {
            name: {
                "schema_version": contract.schema_version,
                "required": contract.required,
                "nullable": contract.nullable,
            }
            for name, contract in self.contracts.items()
        }
        Path(output_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
