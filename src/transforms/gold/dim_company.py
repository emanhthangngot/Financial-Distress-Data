"""
Gold-zone dimension builders (dim_company, dim_date).

Builds the company and date dimensions from the Silver zone, normalized for surrogate keys.
Re-exported by ``src.transforms.silver_to_gold``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from src.transforms.keys import company_version_key, date_key


def _utc_iso(value: Any) -> str:
    text = str(value).strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    parsed = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


def merge_dim_company(
    existing_rows: list[dict[str, Any]], snapshots: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Merge snapshots monotonically without rewriting closed SCD2 history."""
    output = [dict(row) for row in existing_rows]
    tracked = (
        "company_name",
        "industry",
        "sector",
        "exchange",
        "listing_date",
        "delisted_flag",
    )
    versions = {(str(row["ticker"]).upper(), _utc_iso(row["valid_from_ts"])): row for row in output}
    for row in sorted(
        snapshots,
        key=lambda item: (str(item["ticker"]).upper(), _utc_iso(item["created_ts"])),
    ):
        ticker = str(row["ticker"]).upper()
        valid_from = _utc_iso(row["created_ts"])
        existing = versions.get((ticker, valid_from))
        if existing is not None:
            if all(
                existing.get(field)
                == (bool(row.get(field, False)) if field == "delisted_flag" else row.get(field))
                for field in tracked
            ):
                continue
            raise ValueError(f"late_scd2_snapshot for ticker={ticker} valid_from_ts={valid_from}")
        prior = [item for item in output if str(item["ticker"]).upper() == ticker]
        if prior and valid_from <= max(item["valid_from_ts"] for item in prior):
            raise ValueError(f"late_scd2_snapshot for ticker={ticker} valid_from_ts={valid_from}")
        previous = max(prior, key=lambda item: item["valid_from_ts"], default=None)
        if previous is not None:
            previous["valid_to_ts"] = valid_from
            previous["is_current"] = False
        dim_row = {
            "company_version_key": company_version_key(ticker, valid_from),
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
        versions[(ticker, valid_from)] = dim_row
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
