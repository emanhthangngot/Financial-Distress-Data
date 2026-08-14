"""
Fixture-backed vnstock adapter for offline and CI runs.

Replays deterministic fixtures (offline + streaming) instead of calling the live vnstock SDK, with
knobs for skew, cardinality, late arrivals, and burst rates documented in
``docs/01_data_generator.md``. The default adapter for Phase 1 development and CI.
"""

from __future__ import annotations

import random
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.collectors.fixture_config import FixtureGeneratorConfig


def _legacy_companies(source_name: str) -> list[dict]:
    return [
        {
            "ticker": "AAA",
            "company_name": "AAA Corp",
            "exchange": "HOSE",
            "industry": "Manufacturing",
            "sector": "Industrials",
            "listing_date": "2015-01-01",
            "delisted_flag": False,
            "created_ts": "2026-01-01T00:00:00+00:00",
            "source_system": source_name,
        },
        {
            "ticker": "BBB",
            "company_name": "BBB Real Estate",
            "exchange": "HNX",
            "industry": "Real Estate",
            "sector": "Financials",
            "listing_date": "2018-06-01",
            "delisted_flag": False,
            "created_ts": "2026-01-01T00:00:00+00:00",
            "source_system": source_name,
        },
    ]


def _build_company_rows(
    *,
    source_name: str,
    rng: random.Random,
    top_ticker: str,
    top_share: float,
    tail_tickers: tuple[str, ...],
    industries_pool: tuple[str, ...],
    sectors_pool: tuple[str, ...],
    companies_count: int,
) -> list[dict]:
    """Generate ``companies_count`` rows honouring skew/pools.

    The skew share is rounded to the nearest integer so that, for
    ``companies_count=5`` and ``top_share=0.6``, the top ticker accounts for
    exactly 3 rows. Tail rows pick a ticker from ``tail_tickers`` (with
    cycle when the pool is smaller than needed) and an industry/sector drawn
    from the configured pools.
    """
    rows: list[dict] = []
    top_n = round(top_share * companies_count)
    top_n = max(0, min(companies_count, top_n))

    for i in range(companies_count):
        if i < top_n:
            ticker = top_ticker
        else:
            tail = tail_tickers if tail_tickers else ("ZZZ",)
            ticker = tail[i - top_n] if (i - top_n) < len(tail) else tail[(i - top_n) % len(tail)]
        industry = rng.choice(industries_pool) if industries_pool else "Unknown"
        sector = rng.choice(sectors_pool) if sectors_pool else "Unknown"
        rows.append(
            {
                "ticker": ticker,
                "company_name": f"{ticker} Co",
                "exchange": "HOSE",
                "industry": industry,
                "sector": sector,
                "listing_date": "2015-01-01",
                "delisted_flag": False,
                "created_ts": "2026-01-01T00:00:00+00:00",
                "source_system": source_name,
            }
        )
    return rows


def _build_financial_rows(
    *,
    ticker: str,
    start_year: int,
    end_year: int,
    source_name: str,
    rng: random.Random,
    legacy_null_columns: tuple[str, ...],
    legacy_partition_cutoff: str,
    offline_rate: float,
    stressed_tickers: tuple[str, ...] = ("BBB",),
) -> list[dict]:
    rows: list[dict] = []
    for year in range(start_year, end_year + 1):
        for quarter in range(1, 5):
            report_period = f"{year}Q{quarter}"
            stressed = ticker in stressed_tickers and year >= end_year
            row = {
                "ticker": ticker,
                "report_period": report_period,
                "fiscal_year": year,
                "fiscal_quarter": quarter,
                "total_assets": 1000,
                "current_assets": 300 if not stressed else 100,
                "current_liabilities": 200 if not stressed else 250,
                "total_liabilities": 500 if not stressed else 900,
                "equity": 500 if not stressed else -50,
                "revenue": 600,
                "ebit": 120 if not stressed else 10,
                "interest_expense": 20,
                "net_income": 80 if not stressed else -30,
                "operating_cash_flow": 90 if not stressed else -20,
                "retained_earnings": 150 if not stressed else -100,
                "report_release_date": date(year, quarter * 3, 28).isoformat(),
                "event_timestamp": date(year, quarter * 3, 28).isoformat(),
                "created_ts": f"{year}-{quarter * 3:02d}-28T00:00:00+00:00",
                "source_system": source_name,
            }
            if legacy_null_columns and report_period < legacy_partition_cutoff:
                for col in legacy_null_columns:
                    row[col] = None
            rows.append(row)

    dup_count = int(offline_rate * len(rows))
    if dup_count and rows:
        for _ in range(dup_count):
            clone = dict(rows[rng.randrange(len(rows))])
            clone["_is_duplicate"] = True
            rows.append(clone)
    return rows


def _build_market_rows(
    *,
    ticker: str,
    start_year: int,
    end_year: int,
    source_name: str,
    rng: random.Random,
    offline_rate: float,
) -> list[dict]:
    rows: list[dict] = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 4):
            trading_date = date(year, month, 1).isoformat()
            rows.append(
                {
                    "ticker": ticker,
                    "trading_date": trading_date,
                    "open_price": 10.0,
                    "high_price": 10.5,
                    "low_price": 9.5,
                    "close_price": 10.0 + month,
                    "volume": 10000 * month,
                    "market_cap": 1_000_000,
                    "event_timestamp": trading_date,
                    "created_ts": f"{trading_date}T00:00:00+00:00",
                    "source_system": source_name,
                }
            )
    dup_count = int(offline_rate * len(rows))
    if dup_count and rows:
        for _ in range(dup_count):
            clone = dict(rows[rng.randrange(len(rows))])
            clone["_is_duplicate"] = True
            rows.append(clone)
    return rows


class VnstockFixtureAdapter:
    """Deterministic adapter matching the vnstock boundary for tests and smoke runs.

    When ``config`` is ``None`` or ``config.enabled is False`` the adapter
    returns the legacy hard-coded fixture rows. Otherwise, it consumes the
    generator knobs (skew, cardinality, evolution, duplication) to produce
    deterministic rows that satisfy the mini-coursework rubric.
    """

    source_name = "vnstock_fixture"

    def __init__(self, config: FixtureGeneratorConfig | None = None) -> None:
        self._config = config
        self._rng_seed = config.fixture_seed if config is not None else 0

    def _rng(self) -> random.Random:
        return random.Random(self._rng_seed)

    def _use_knobs(self) -> bool:
        return self._config is not None and self._config.enabled

    def fetch_companies(self) -> list[dict]:
        if not self._use_knobs():
            return _legacy_companies(self.source_name)
        cfg = self._config  # type: ignore[assignment]
        return _build_company_rows(
            source_name=self.source_name,
            rng=self._rng(),
            top_ticker=cfg.skew.top_company_ticker,
            top_share=cfg.skew.top_company_share,
            tail_tickers=cfg.skew.tail_tickers,
            industries_pool=cfg.cardinality.industries_pool,
            sectors_pool=cfg.cardinality.sectors_pool,
            companies_count=cfg.cardinality.companies_count,
        )

    def fetch_financial_statements(self, ticker: str, start_year: int, end_year: int) -> list[dict]:
        if not self._use_knobs():
            return _legacy_financial_statements(ticker, start_year, end_year, self.source_name)
        cfg = self._config  # type: ignore[assignment]
        return _build_financial_rows(
            ticker=ticker,
            start_year=start_year,
            end_year=end_year,
            source_name=self.source_name,
            rng=self._rng(),
            legacy_null_columns=cfg.evolution.legacy_null_columns,
            legacy_partition_cutoff=cfg.evolution.legacy_partition_cutoff,
            offline_rate=cfg.duplication.offline_rate,
            stressed_tickers=cfg.stressed_tickers,
        )

    def fetch_market_prices(self, ticker: str, start_year: int, end_year: int) -> list[dict]:
        if not self._use_knobs():
            return _legacy_market_prices(ticker, start_year, end_year, self.source_name)
        cfg = self._config  # type: ignore[assignment]
        return _build_market_rows(
            ticker=ticker,
            start_year=start_year,
            end_year=end_year,
            source_name=self.source_name,
            rng=self._rng(),
            offline_rate=cfg.duplication.offline_rate,
        )


def _legacy_financial_statements(
    ticker: str, start_year: int, end_year: int, source_name: str
) -> list[dict]:
    rows = []
    for year in range(start_year, end_year + 1):
        for quarter in range(1, 5):
            report_period = f"{year}Q{quarter}"
            stressed = ticker == "BBB" and year >= end_year
            rows.append(
                {
                    "ticker": ticker,
                    "report_period": report_period,
                    "fiscal_year": year,
                    "fiscal_quarter": quarter,
                    "total_assets": 1000,
                    "current_assets": 300 if not stressed else 100,
                    "current_liabilities": 200 if not stressed else 250,
                    "total_liabilities": 500 if not stressed else 900,
                    "equity": 500 if not stressed else -50,
                    "revenue": 600,
                    "ebit": 120 if not stressed else 10,
                    "interest_expense": 20,
                    "net_income": 80 if not stressed else -30,
                    "operating_cash_flow": 90 if not stressed else -20,
                    "retained_earnings": 150 if not stressed else -100,
                    "report_release_date": date(year, quarter * 3, 28).isoformat(),
                    "event_timestamp": date(year, quarter * 3, 28).isoformat(),
                    "created_ts": f"{year}-{quarter * 3:02d}-28T00:00:00+00:00",
                    "source_system": source_name,
                }
            )
    return rows


def _legacy_market_prices(
    ticker: str, start_year: int, end_year: int, source_name: str
) -> list[dict]:
    rows = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 4):
            trading_date = date(year, month, 1).isoformat()
            rows.append(
                {
                    "ticker": ticker,
                    "trading_date": trading_date,
                    "open_price": 10.0,
                    "high_price": 10.5,
                    "low_price": 9.5,
                    "close_price": 10.0 + month,
                    "volume": 10000 * month,
                    "market_cap": 1_000_000,
                    "event_timestamp": trading_date,
                    "created_ts": f"{trading_date}T00:00:00+00:00",
                    "source_system": source_name,
                }
            )
    return rows
