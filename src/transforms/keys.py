"""Deterministic dimension and date keys used across Silver and Gold.

Centralizes SCD2 version identity and range resolution so every fact builder applies the same
closed-open validity rule.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from hashlib import sha256
from typing import Any


def _timestamp(value: Any, *, field: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, datetime.min.time(), tzinfo=UTC)
    else:
        text = str(value or "").strip().replace("Z", "+00:00")
        if not text:
            raise ValueError(f"{field} is required")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"{field} must be an ISO timestamp, got {value!r}") from exc
    parsed = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def company_version_key(ticker: str, valid_from: str | date | datetime) -> str:
    normalized_ticker = str(ticker or "").strip().upper()
    if not normalized_ticker:
        raise ValueError("ticker is required for company_version_key")
    if isinstance(valid_from, datetime):
        valid_from_text = _timestamp(valid_from, field="valid_from").isoformat()
    elif isinstance(valid_from, date):
        valid_from_text = datetime.combine(valid_from, datetime.min.time(), tzinfo=UTC).isoformat()
    else:
        valid_from_text = str(valid_from or "").strip()
        _timestamp(valid_from_text, field="valid_from")
    return sha256(f"{normalized_ticker}|{valid_from_text}".encode()).hexdigest()[:16]


def resolve_company_version_key(
    ticker: str,
    known_from_ts: str | date | datetime,
    dim_company_rows: list[dict[str, Any]],
) -> str:
    normalized_ticker = str(ticker or "").strip().upper()
    if not normalized_ticker:
        raise ValueError("ticker is required to resolve company_version_key")
    known_from = _timestamp(known_from_ts, field="known_from_ts")
    matches = []
    for row in dim_company_rows:
        if str(row.get("ticker") or "").strip().upper() != normalized_ticker:
            continue
        valid_from = _timestamp(row.get("valid_from_ts"), field="valid_from_ts")
        valid_to_value = row.get("valid_to_ts")
        valid_to = (
            _timestamp(valid_to_value, field="valid_to_ts")
            if valid_to_value not in (None, "")
            else None
        )
        if valid_from <= known_from and (valid_to is None or known_from < valid_to):
            matches.append(row)
    if len(matches) != 1:
        raise ValueError(
            "company version resolution requires exactly one match for "
            f"ticker={normalized_ticker!r}, known_from_ts={known_from.isoformat()!r}; "
            f"found {len(matches)}"
        )
    version_key = matches[0].get("company_version_key")
    if not version_key:
        raise ValueError(
            f"resolved dimension row for ticker={normalized_ticker!r} has no company_version_key"
        )
    return str(version_key)


def fact_known_from_ts(row: dict[str, Any], *fallback_fields: str) -> Any:
    value = row.get("known_from_ts")
    if value in (None, ""):
        value = next(
            (row.get(field) for field in fallback_fields if row.get(field) not in (None, "")),
            None,
        )
    _timestamp(value, field="known_from_ts")
    return value


def resolve_company_version_key_spark(
    dataframe: Any,
    dim_company_dataframe: Any,
    *,
    known_from_column: str = "known_from_ts",
) -> Any:
    """Attach one SCD2 version key per fact row and reject unresolved or overlapping ranges."""

    try:
        from pyspark.sql import functions as F
    except ImportError as exc:
        raise RuntimeError("PySpark is required for Spark company version resolution.") from exc

    fact = (
        dataframe.drop("company_version_key")
        .withColumn("__fact_row_id", F.monotonically_increasing_id())
        .alias("fact")
    )
    dimension = dim_company_dataframe.alias("dimension")
    known_from = F.to_timestamp(F.col(f"fact.{known_from_column}"))
    valid_from = F.to_timestamp(F.col("dimension.valid_from_ts"))
    valid_to = F.to_timestamp(F.col("dimension.valid_to_ts"))
    joined = fact.join(
        dimension,
        (F.upper(F.col("fact.ticker")) == F.upper(F.col("dimension.ticker")))
        & (valid_from <= known_from)
        & (valid_to.isNull() | (known_from < valid_to)),
        "left",
    )
    violations = (
        joined.groupBy(F.col("fact.__fact_row_id").alias("__fact_row_id"))
        .agg(F.count(F.col("dimension.company_version_key")).alias("__match_count"))
        .filter(F.col("__match_count") != 1)
        .limit(1)
        .collect()
    )
    if violations:
        raise ValueError(
            "company version resolution requires exactly one SCD2 range match per fact row; "
            f"found match_count={violations[0]['__match_count']}"
        )
    return joined.select(
        "fact.*",
        F.col("dimension.company_version_key").alias("company_version_key"),
    ).drop("__fact_row_id")


def date_key(value: str | date | datetime) -> int:
    if isinstance(value, datetime):
        value = value.date()
    elif isinstance(value, str):
        value = datetime.fromisoformat(value[:10]).date()
    if not isinstance(value, date):
        raise ValueError("date_key requires a date, datetime, or ISO date string")
    return int(value.strftime("%Y%m%d"))
