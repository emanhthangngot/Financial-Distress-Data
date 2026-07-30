"""Generate deterministic batch datasets with measurable data problems."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from src.generator.config import GeneratorConfig


@dataclass(frozen=True)
class OfflineData:
    companies: list[dict[str, Any]]
    financial_statements: list[dict[str, Any]]
    market_prices: list[dict[str, Any]]
    offline_duplicate_rate: float

    def datasets(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "companies": self.companies,
            "financial_statements": self.financial_statements,
            "market_prices_daily": self.market_prices,
        }

    def logical_rows(self) -> list[dict[str, Any]]:
        return [
            {"dataset": dataset, **row} for dataset, rows in self.datasets().items() for row in rows
        ]


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _quarter_period(index: int) -> tuple[str, int, int]:
    year = 2023 + index // 4
    quarter = index % 4 + 1
    return f"{year}Q{quarter}", year, quarter


def _duplicate_count(base_count: int, rate: float) -> int:
    if rate == 0:
        return 0
    return round(base_count * rate / (1 - rate))


def _inject_company_duplicates(
    rows: list[dict[str, Any]], rate: float, rng: random.Random
) -> list[dict[str, Any]]:
    duplicate_count = _duplicate_count(len(rows), rate)
    if not duplicate_count:
        return rows
    selected = rng.sample(rows, min(duplicate_count, len(rows)))
    duplicates: list[dict[str, Any]] = []
    for row in selected:
        duplicate = dict(row)
        duplicate["company_name"] = f"{row['company_name']} Updated"
        duplicate["created_ts"] = _iso(
            datetime.fromisoformat(row["created_ts"]) + timedelta(minutes=1)
        )
        duplicate["is_injected_duplicate"] = True
        duplicates.append(duplicate)
    return rows + duplicates


def generate_offline_data(config: GeneratorConfig) -> OfflineData:
    """Build company, statement, and price source rows for Bronze ingestion."""
    config.validate()
    rng = random.Random(config.seed)
    settings = config.offline
    sectors = ["Technology", "Retail", "Energy", "Healthcare"]
    exchanges = ["HNX", "UPCOM"]
    dominant_sectors = round(settings.companies * settings.dominant_sector_rate)
    dominant_exchanges = round(settings.companies * settings.dominant_exchange_rate)
    created_base = datetime(2026, 1, 1, tzinfo=UTC)
    companies: list[dict[str, Any]] = []
    statements: list[dict[str, Any]] = []
    prices: list[dict[str, Any]] = []

    for company_index in range(settings.companies):
        ticker = f"G{company_index:07d}"
        company_created = created_base + timedelta(seconds=company_index)
        companies.append(
            {
                "ticker": ticker,
                "company_name": f"Generated Company {company_index:07d}",
                "exchange": (
                    settings.dominant_exchange
                    if company_index < dominant_exchanges
                    else exchanges[company_index % len(exchanges)]
                ),
                "industry": "Generated",
                "sector": (
                    settings.dominant_sector
                    if company_index < dominant_sectors
                    else sectors[company_index % len(sectors)]
                ),
                "listing_date": "2020-01-02",
                "delisted_flag": False,
                "company_size": "large" if company_index % 5 == 0 else "mid",
                "created_ts": _iso(company_created),
                "source_system": "configurable_generator",
                "source_record_id": f"company-{company_index:012d}",
                "high_cardinality_id": (
                    f"entity-{company_index % settings.high_cardinality_ids:012d}"
                ),
                "schema_version": 2,
                "is_injected_duplicate": False,
            }
        )
        prices.append(
            {
                "ticker": ticker,
                "trading_date": "2026-01-02",
                "open_price": round(10 + rng.random() * 90, 2),
                "high_price": round(105 + rng.random() * 10, 2),
                "low_price": round(5 + rng.random() * 5, 2),
                "close_price": round(10 + rng.random() * 90, 2),
                "volume": 1000 + company_index,
                "market_cap": 1_000_000 + company_index * 100,
                "shares_outstanding": 100_000 + company_index,
                "event_timestamp": "2026-01-02T09:00:00+00:00",
                "created_ts": _iso(company_created),
                "source_system": "configurable_generator",
                "source_record_id": f"price-{company_index:012d}",
                "schema_version": 2,
            }
        )
        for quarter_index in range(settings.quarters):
            period, fiscal_year, fiscal_quarter = _quarter_period(quarter_index)
            schema_version = 1 if quarter_index < settings.schema_change_quarter - 1 else 2
            assets = 1_000_000 + company_index * 100 + quarter_index * 1000
            liabilities = int(assets * (0.45 + rng.random() * 0.25))
            release = date(fiscal_year, fiscal_quarter * 3, 28) + timedelta(days=30)
            statements.append(
                {
                    "ticker": ticker,
                    "report_period": period,
                    "fiscal_year": fiscal_year,
                    "fiscal_quarter": fiscal_quarter,
                    "total_assets": assets,
                    "total_liabilities": liabilities,
                    "equity": assets - liabilities,
                    "current_assets": int(assets * 0.4),
                    "current_liabilities": int(liabilities * 0.5),
                    "revenue": int(assets * 0.25),
                    "ebit": int(assets * 0.04),
                    "interest_expense": int(assets * 0.01),
                    "net_income": int(assets * 0.025),
                    "operating_cash_flow": None if schema_version == 1 else int(assets * 0.03),
                    "retained_earnings": None if schema_version == 1 else int(assets * 0.08),
                    "statement_type": "consolidated" if schema_version == 2 else None,
                    "report_release_date": release.isoformat(),
                    "event_timestamp": f"{release.isoformat()}T00:00:00+00:00",
                    "created_ts": _iso(company_created + timedelta(days=quarter_index)),
                    "source_system": "configurable_generator",
                    "source_record_id": f"statement-{company_index:012d}-{quarter_index:02d}",
                    "schema_version": schema_version,
                }
            )

    companies = _inject_company_duplicates(companies, settings.duplicate_rate, rng)
    duplicate_rows = sum(row["is_injected_duplicate"] for row in companies)
    return OfflineData(
        companies,
        statements,
        prices,
        duplicate_rows / len(companies),
    )
