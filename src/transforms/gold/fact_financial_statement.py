"""
Gold-zone fact builder for financial statements.

Projects the Silver financial_statement table into the Gold fact with surrogate keys,
currency-normalized amounts, and period-end dates. Both pure-Python and PySpark variants are
exposed.
"""

from __future__ import annotations

from typing import Any

from src.transforms.keys import (
    date_key,
    fact_known_from_ts,
    resolve_company_version_key,
    resolve_company_version_key_spark,
)


def build_fact_financial_statement(
    rows: list[dict[str, Any]],
    dim_company_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    facts = []
    for row in rows:
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
        fact["statement_variant"] = (
            row.get("statement_variant") or row.get("statement_type") or "consolidated"
        )
        fact["is_latest_vintage"] = bool(row.get("is_latest_vintage", True))
        facts.append(fact)
    return facts


def build_fact_financial_statement_spark(
    dataframe: Any,
    dim_company_dataframe: Any,
) -> Any:
    try:
        from pyspark.sql import functions as F
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
                F.lit("consolidated"),
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
    if fact.filter(F.col("known_from_ts").isNull()).limit(1).count():
        raise ValueError(
            "known_from_ts, report_release_date, event_timestamp, or created_ts is required"
        )
    return resolve_company_version_key_spark(fact, dim_company_dataframe)
