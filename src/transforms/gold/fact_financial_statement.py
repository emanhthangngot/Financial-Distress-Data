"""
Gold-zone fact builder for financial statements.

Projects the Silver financial_statement table into the Gold fact with surrogate keys,
currency-normalized amounts, and period-end dates. Both pure-Python and PySpark variants are
exposed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.transforms.keys import (
    date_key,
    fact_known_from_ts,
    resolve_company_version_key,
    resolve_company_version_key_spark,
)

_STATEMENT_VARIANTS = {
    "consolidated_audited": 1,
    "consolidated_unaudited": 2,
    "separate_audited": 3,
    "separate_unaudited": 4,
}


def _timestamp_sort_key(value: Any) -> float:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).timestamp()


def _statement_variant(row: dict[str, Any]) -> str:
    value = row.get("statement_variant") or row.get("statement_type")
    normalized = str(value or "").strip().lower()
    if normalized not in _STATEMENT_VARIANTS:
        raise ValueError(f"unknown_statement_variant: {value!r}")
    return normalized


def build_fact_financial_statement(
    rows: list[dict[str, Any]],
    dim_company_rows: list[dict[str, Any]],
    *,
    failed_records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    facts = []
    for row in rows:
        try:
            statement_variant = _statement_variant(row)
        except ValueError as exc:
            if failed_records is not None:
                failed_records.append(
                    {
                        "failure_reason": str(exc),
                        "raw_payload": dict(row),
                    }
                )
                continue
            raise
        known_from_ts = fact_known_from_ts(
            row, "report_release_date", "event_timestamp", "created_ts"
        )
        fact = dict(row)
        fact["ticker"] = str(row["ticker"]).upper()
        fact["known_from_ts"] = known_from_ts
        fact["company_version_key"] = resolve_company_version_key(
            fact["ticker"], known_from_ts, dim_company_rows
        )
        fact["date_key"] = date_key(known_from_ts)
        fact["statement_variant"] = statement_variant
        facts.append(fact)
    latest_keys: set[tuple[str, str]] = set()
    for fact in sorted(
        facts,
        key=lambda item: (
            item["ticker"],
            item["report_period"],
            -_timestamp_sort_key(item["known_from_ts"]),
            _STATEMENT_VARIANTS[item["statement_variant"]],
            (-_timestamp_sort_key(item["created_ts"]) if item.get("created_ts") else float("inf")),
            item["statement_variant"],
        ),
    ):
        key = (fact["ticker"], fact["report_period"])
        fact["is_latest_vintage"] = key not in latest_keys
        latest_keys.add(key)
    return facts


def build_fact_financial_statement_spark(
    dataframe: Any,
    dim_company_dataframe: Any,
) -> Any:
    try:
        from pyspark.sql import functions as F
        from pyspark.sql.window import Window
    except ImportError as exc:
        raise RuntimeError("PySpark is required for Spark Gold transforms.") from exc

    known_from_ts = F.coalesce(
        (
            F.to_timestamp("known_from_ts")
            if "known_from_ts" in dataframe.columns
            else F.lit(None).cast("timestamp")
        ),
        (
            F.to_timestamp("report_release_date")
            if "report_release_date" in dataframe.columns
            else F.lit(None).cast("timestamp")
        ),
        (
            F.to_timestamp("event_timestamp")
            if "event_timestamp" in dataframe.columns
            else F.lit(None).cast("timestamp")
        ),
        (
            F.to_timestamp("created_ts")
            if "created_ts" in dataframe.columns
            else F.lit(None).cast("timestamp")
        ),
    )
    fact = (
        dataframe.withColumn("ticker", F.upper(F.col("ticker")))
        .withColumn("known_from_ts", known_from_ts)
        .withColumn(
            "statement_variant",
            F.lower(
                F.trim(
                    F.coalesce(
                        (
                            F.col("statement_variant")
                            if "statement_variant" in dataframe.columns
                            else F.lit(None).cast("string")
                        ),
                        (
                            F.col("statement_type")
                            if "statement_type" in dataframe.columns
                            else F.lit(None).cast("string")
                        ),
                    )
                )
            ),
        )
        .withColumn(
            "is_latest_vintage",
            F.coalesce(
                (
                    F.col("is_latest_vintage").cast("boolean")
                    if "is_latest_vintage" in dataframe.columns
                    else F.lit(None).cast("boolean")
                ),
                F.lit(True),
            ),
        )
        .withColumn(
            "date_key",
            F.date_format(F.to_date("known_from_ts"), "yyyyMMdd").cast("int"),
        )
    )
    invalid_variant = F.col("statement_variant").isNull() | ~F.col("statement_variant").isin(
        sorted(_STATEMENT_VARIANTS)
    )
    if fact.filter(invalid_variant).limit(1).count():
        raise ValueError("unknown_statement_variant")
    variant_rank = F.create_map(
        *[item for key, rank in _STATEMENT_VARIANTS.items() for item in (F.lit(key), F.lit(rank))]
    )[F.col("statement_variant")]
    election_window = Window.partitionBy("ticker", "report_period").orderBy(
        F.col("known_from_ts").desc(),
        variant_rank.asc(),
        F.col("created_ts").desc_nulls_last(),
        F.col("statement_variant").asc(),
    )
    fact = (
        fact.withColumn("_variant_rank", variant_rank)
        .withColumn(
            "is_latest_vintage",
            F.row_number().over(election_window) == 1,
        )
        .drop("_variant_rank")
    )
    if fact.filter(F.col("known_from_ts").isNull()).limit(1).count():
        raise ValueError(
            "known_from_ts, report_release_date, event_timestamp, or created_ts is required"
        )
    return resolve_company_version_key_spark(fact, dim_company_dataframe)
