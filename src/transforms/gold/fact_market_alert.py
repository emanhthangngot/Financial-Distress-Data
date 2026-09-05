"""
Gold-zone fact builder for market alerts.

Builds the alert fact from the streaming topic, deriving simple thresholds (e.g. daily drop > 7%)
and joining with company dimension. Powers the news/alert dashboard.
"""

from __future__ import annotations

from typing import Any

from src.transforms.keys import (
    date_key,
    fact_known_from_ts,
    resolve_company_version_key,
    resolve_company_version_key_spark,
)


def build_fact_market_alert(
    rows: list[dict[str, Any]],
    dim_company_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    facts = []
    latest: dict[str, dict[str, Any]] = {}
    for row in sorted(
        rows,
        key=lambda item: (item.get("event_id", ""), item.get("created_ts", "")),
        reverse=True,
    ):
        event_id = str(row["event_id"])
        if event_id in latest:
            continue
        latest[event_id] = row
        ticker = str(row["ticker"]).upper()
        fact = dict(row)
        fact["ticker"] = ticker
        fact["known_from_ts"] = fact_known_from_ts(row, "event_timestamp", "created_ts")
        fact["company_version_key"] = resolve_company_version_key(
            ticker, fact["known_from_ts"], dim_company_rows
        )
        fact["date_key"] = date_key(row["event_timestamp"])
        fact["alert_type"] = str(row.get("alert_type", "unknown"))
        facts.append(fact)
    return facts


def build_fact_market_alert_spark(
    dataframe: Any,
    dim_company_dataframe: Any,
) -> Any:
    try:
        from pyspark.sql import functions as F
        from pyspark.sql.window import Window
    except ImportError as exc:
        raise RuntimeError("PySpark is required for Spark Gold transforms.") from exc

    window = Window.partitionBy("event_id").orderBy(F.col("created_ts").desc_nulls_last())
    known_from_ts = F.coalesce(
        (
            F.to_timestamp("known_from_ts")
            if "known_from_ts" in dataframe.columns
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
        dataframe.withColumn("_row_number", F.row_number().over(window))
        .filter(F.col("_row_number") == 1)
        .drop("_row_number")
        .withColumn("ticker", F.upper(F.col("ticker")))
        .withColumn("known_from_ts", known_from_ts)
        .withColumn(
            "date_key",
            F.date_format(F.to_date("event_timestamp"), "yyyyMMdd").cast("int"),
        )
    )
    if fact.filter(F.col("known_from_ts").isNull()).limit(1).count():
        raise ValueError("known_from_ts, event_timestamp, or created_ts is required")
    return resolve_company_version_key_spark(fact, dim_company_dataframe)
