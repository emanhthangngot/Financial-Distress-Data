from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from src.transforms.compute_distress_labels import compute_labels
from src.transforms.keys import date_key, stable_company_key


def build_dim_company(companies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = sorted(companies, key=lambda item: (item["ticker"], item.get("created_ts", "")))
    output: list[dict[str, Any]] = []
    latest_by_ticker: dict[str, dict[str, Any]] = {}
    tracked = ("industry", "sector", "exchange", "delisted_flag")
    for row in rows:
        ticker = str(row["ticker"]).upper()
        previous = latest_by_ticker.get(ticker)
        changed = previous is None or any(
            previous.get(field) != row.get(field) for field in tracked
        )
        if not changed:
            continue
        if previous is not None:
            previous["valid_to_ts"] = row.get("created_ts")
            previous["is_current"] = False
        dim_row = {
            "company_key": stable_company_key(ticker),
            "ticker": ticker,
            "company_name": row.get("company_name"),
            "exchange": row.get("exchange"),
            "industry": row.get("industry"),
            "sector": row.get("sector"),
            "listing_date": row.get("listing_date"),
            "delisted_flag": bool(row.get("delisted_flag", False)),
            "valid_from_ts": row.get("created_ts"),
            "valid_to_ts": None,
            "is_current": True,
        }
        output.append(dim_row)
        latest_by_ticker[ticker] = dim_row
    return output


def build_dim_date(start: date, end: date) -> list[dict[str, Any]]:
    rows = []
    current = start
    while current <= end:
        rows.append(
            {
                "date_key": date_key(current),
                "calendar_date": current.isoformat(),
                "day_of_week": current.weekday() + 1,
                "month": current.month,
                "quarter": (current.month - 1) // 3 + 1,
                "year": current.year,
                "is_weekend": current.weekday() >= 5,
            }
        )
        current += timedelta(days=1)
    return rows


def build_fact_financial_statement(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts = []
    for row in rows:
        reference_date = (
            row.get("report_release_date")
            or row.get("event_timestamp")
            or f"{row['fiscal_year']}-01-01"
        )
        fact = dict(row)
        fact["ticker"] = str(row["ticker"]).upper()
        fact["company_key"] = stable_company_key(fact["ticker"])
        fact["date_key"] = date_key(reference_date)
        facts.append(fact)
    return facts


def build_fact_market_price(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts = []
    previous_close_by_ticker: dict[str, float] = {}
    for row in sorted(rows, key=lambda item: (item["ticker"], item["trading_date"])):
        fact = dict(row)
        fact["ticker"] = str(row["ticker"]).upper()
        fact["company_key"] = stable_company_key(fact["ticker"])
        fact["date_key"] = date_key(row["trading_date"])
        previous_close = previous_close_by_ticker.get(fact["ticker"])
        close_price = float(row["close_price"])
        fact["daily_return"] = (
            None if previous_close in (None, 0) else (close_price - previous_close) / previous_close
        )
        fact["volatility_signal"] = bool(
            fact["daily_return"] is not None and abs(fact["daily_return"]) > 0.07
        )
        previous_close_by_ticker[fact["ticker"]] = close_price
        facts.append(fact)
    return facts


def build_distress_labels(financial_statement_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return compute_labels(financial_statement_rows)


def build_obt_company_quarter_risk(
    financial_facts: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    market_facts: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    label_by_key = {(row["ticker"], row["report_period"]): row for row in labels}
    output = []
    for row in financial_facts:
        label = label_by_key.get((row["ticker"], row["report_period"]), {})
        total_assets = (
            float(row["total_assets"]) if row.get("total_assets") not in (None, 0) else None
        )
        total_liabilities = (
            float(row["total_liabilities"]) if row.get("total_liabilities") is not None else None
        )
        equity = float(row["equity"]) if row.get("equity") not in (None, 0) else None
        current_liabilities = (
            float(row["current_liabilities"])
            if row.get("current_liabilities") not in (None, 0)
            else None
        )
        interest_expense = (
            float(row["interest_expense"]) if row.get("interest_expense") not in (None, 0) else None
        )
        obt = {
            **row,
            "current_ratio": (
                None
                if current_liabilities is None
                else float(row.get("current_assets") or 0) / current_liabilities
            ),
            "debt_to_asset": (
                None
                if total_assets is None or total_liabilities is None
                else total_liabilities / total_assets
            ),
            "debt_to_equity": (
                None if equity is None or total_liabilities is None else total_liabilities / equity
            ),
            "roa": (
                None if total_assets is None else float(row.get("net_income") or 0) / total_assets
            ),
            "roe": None if equity is None else float(row.get("net_income") or 0) / equity,
            "ebit_interest_coverage": (
                None if interest_expense is None else float(row.get("ebit") or 0) / interest_expense
            ),
            "distress_label": label.get("distress_label"),
            "distress_reason": label.get("distress_reason"),
            "z_score": label.get("z_score"),
        }
        output.append(obt)
    return output


def pit_join_features(
    references: list[dict[str, Any]], features: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    by_ticker: dict[str, list[dict[str, Any]]] = {}
    for feature in features:
        by_ticker.setdefault(str(feature["ticker"]).upper(), []).append(feature)
    for ticker_features in by_ticker.values():
        ticker_features.sort(key=lambda item: item["event_timestamp"], reverse=True)
    for reference in references:
        ticker = str(reference["ticker"]).upper()
        ref_ts = reference["event_timestamp"]
        candidate = next(
            (
                feature
                for feature in by_ticker.get(ticker, [])
                if str(feature["event_timestamp"]) <= str(ref_ts)
            ),
            {},
        )
        output.append(
            {**reference, **{f"feature_{key}": value for key, value in candidate.items()}}
        )
    return output
