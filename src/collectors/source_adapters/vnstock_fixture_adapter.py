from __future__ import annotations

from datetime import date


class VnstockFixtureAdapter:
    """Deterministic adapter matching the vnstock boundary for tests and smoke runs."""

    source_name = "vnstock_fixture"

    def fetch_companies(self) -> list[dict]:
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
                "source_system": self.source_name,
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
                "source_system": self.source_name,
            },
        ]

    def fetch_financial_statements(self, ticker: str, start_year: int, end_year: int) -> list[dict]:
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
                        "source_system": self.source_name,
                    }
                )
        return rows

    def fetch_market_prices(self, ticker: str, start_year: int, end_year: int) -> list[dict]:
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
                        "source_system": self.source_name,
                    }
                )
        return rows
