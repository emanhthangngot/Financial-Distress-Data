from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from src.transforms.keys import date_key, stable_company_key


def _utc_iso(value: Any) -> str:
    text = str(value).strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    parsed = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


def merge_dim_company(
    existing_rows: list[dict[str, Any]], snapshots: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Merge ordered company snapshots into persistent SCD2 history."""
    output = [dict(row) for row in existing_rows]
    latest_by_ticker = {str(row["ticker"]).upper(): row for row in output if row.get("is_current")}
    tracked = ("industry", "sector", "exchange", "delisted_flag")
    rows = sorted(
        snapshots,
        key=lambda item: (
            str(item["ticker"]).upper(),
            _utc_iso(item["created_ts"]),
        ),
    )
    for row in rows:
        ticker = str(row["ticker"]).upper()
        previous = latest_by_ticker.get(ticker)
        changed = previous is None or any(
            previous.get(field) != row.get(field) for field in tracked
        )
        if not changed:
            continue
        valid_from = _utc_iso(row["created_ts"])
        if previous is not None:
            previous["valid_to_ts"] = valid_from
            previous["is_current"] = False
        dim_row = {
            "company_key": stable_company_key(ticker),
            "company_version_key": stable_company_key(f"{ticker}|{valid_from}"),
            "ticker": ticker,
            "company_name": row.get("company_name"),
            "exchange": row.get("exchange"),
            "industry": row.get("industry"),
            "sector": row.get("sector"),
            "listing_date": row.get("listing_date"),
            "delisted_flag": bool(row.get("delisted_flag", False)),
            "valid_from_ts": valid_from,
            "valid_to_ts": None,
            "is_current": True,
        }
        output.append(dim_row)
        latest_by_ticker[ticker] = dim_row
    return output


def build_dim_company(companies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return merge_dim_company([], companies)


def _as_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)[:10]).date()


def build_dim_date(
    start: str | date | datetime,
    end: str | date | datetime,
) -> list[dict[str, Any]]:
    rows = []
    current = _as_date(start)
    end_date = _as_date(end)
    while current <= end_date:
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
