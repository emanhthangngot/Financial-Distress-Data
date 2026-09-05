"""
Gold-zone fact builder for market prices.

Projects the Silver market_price table into the Gold fact with adjusted close, daily return, and the
volume aggregate. Partitioned by year and month for analyst queries.
"""

from __future__ import annotations

from typing import Any

from src.transforms.keys import (
    date_key,
    fact_known_from_ts,
    resolve_company_version_key,
    resolve_company_version_key_spark,
)


def build_fact_market_price(
    rows: list[dict[str, Any]],
    dim_company_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    facts = []
    previous_close_by_ticker: dict[str, float] = {}
    for row in sorted(rows, key=lambda item: (item["ticker"], item["trading_date"])):
        fact = dict(row)
        fact["ticker"] = str(row["ticker"]).upper()
        fact["known_from_ts"] = fact_known_from_ts(row, "event_timestamp", "created_ts")
        fact["company_version_key"] = resolve_company_version_key(
            fact["ticker"], fact["known_from_ts"], dim_company_rows
        )
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


def build_fact_market_price_spark(
    dataframe: Any,
    dim_company_dataframe: Any,
) -> Any:
    try:
        from pyspark.sql import functions as F
        from pyspark.sql.window import Window
    except ImportError as exc:
        raise RuntimeError("PySpark is required for Spark Gold transforms.") from exc

    window = Window.partitionBy(F.upper(F.col("ticker"))).orderBy(F.col("trading_date"))
    previous_close = F.lag(F.col("close_price").cast("double")).over(window)
    daily_return = F.when(
        previous_close.isNull() | (previous_close == 0),
        F.lit(None).cast("double"),
    ).otherwise((F.col("close_price").cast("double") - previous_close) / previous_close)
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
        .withColumn("date_key", F.date_format(F.to_date("trading_date"), "yyyyMMdd").cast("int"))
        .withColumn("daily_return", daily_return)
        .withColumn("volatility_signal", F.abs(F.col("daily_return")) > F.lit(0.07))
    )
    if fact.filter(F.col("known_from_ts").isNull()).limit(1).count():
        raise ValueError("known_from_ts, event_timestamp, or created_ts is required")
    return resolve_company_version_key_spark(fact, dim_company_dataframe)
