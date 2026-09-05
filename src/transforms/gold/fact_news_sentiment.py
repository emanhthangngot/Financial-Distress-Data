"""
Gold-zone fact builder for news sentiment.

Aggregates daily news sentiment per ticker from the Silver news table into a Gold fact with mean,
positive, negative, and volume-weighted scores.
"""

from __future__ import annotations

from typing import Any

from src.transforms.keys import (
    date_key,
    fact_known_from_ts,
    resolve_company_version_key,
    resolve_company_version_key_spark,
)


def build_fact_news_sentiment(
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
        fact["sentiment_score"] = (
            None if row.get("sentiment_score") is None else float(row["sentiment_score"])
        )
        fact["risk_keyword_flag"] = bool(row.get("risk_keyword_flag", False))
        fact["severity_score"] = (
            None if row.get("severity_score") is None else float(row["severity_score"])
        )
        facts.append(fact)
    return facts


def build_fact_news_sentiment_spark(
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
            "date_key",
            F.date_format(F.to_date("event_timestamp"), "yyyyMMdd").cast("int"),
        )
    )
    if fact.filter(F.col("known_from_ts").isNull()).limit(1).count():
        raise ValueError("known_from_ts, event_timestamp, or created_ts is required")
    return resolve_company_version_key_spark(fact, dim_company_dataframe)
