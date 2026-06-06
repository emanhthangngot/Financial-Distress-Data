from __future__ import annotations

from datetime import date, timedelta
from typing import Any

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
