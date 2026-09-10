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
    """Build price facts after selecting the as-of vintage for each trading day."""
    prepared = []
    for row in rows:
        fact = dict(row)
        fact["ticker"] = str(row["ticker"]).upper()
        fact["known_from_ts"] = fact_known_from_ts(row, "event_timestamp", "created_ts")
        fact["company_version_key"] = resolve_company_version_key(
            fact["ticker"], fact["known_from_ts"], dim_company_rows
        )
        fact["date_key"] = date_key(row["trading_date"])
        prepared.append(fact)
    output = []
    for fact in sorted(
        prepared,
        key=lambda item: (item["ticker"], item["trading_date"], item["known_from_ts"]),
    ):
        current_ts = fact["known_from_ts"]
        prior_dates = {
            item["trading_date"]
            for item in prepared
            if item["ticker"] == fact["ticker"] and item["trading_date"] < fact["trading_date"]
        }
        previous_close = None
        if prior_dates:
            prior_date = max(prior_dates)
            candidates = [
                item
                for item in prepared
                if item["ticker"] == fact["ticker"]
                and item["trading_date"] == prior_date
                and item["known_from_ts"] <= current_ts
            ]
            if candidates:
                previous_close = float(
                    max(candidates, key=lambda item: item["known_from_ts"])["close_price"]
                )
        close_price = float(fact["close_price"])
        fact["daily_return"] = (
            None if previous_close in (None, 0) else (close_price - previous_close) / previous_close
        )
        fact["volatility_signal"] = bool(
            fact["daily_return"] is not None and abs(fact["daily_return"]) > 0.07
        )
        output.append(fact)
    return output


def build_fact_market_price_spark(
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
    base = (
        dataframe.withColumn("ticker", F.upper(F.col("ticker")))
        .withColumn("known_from_ts", known_from_ts)
        .withColumn("date_key", F.date_format(F.to_date("trading_date"), "yyyyMMdd").cast("int"))
        .withColumn("__row_id", F.monotonically_increasing_id())
    )
    current = base.alias("current")
    previous = base.alias("previous")
    prior_dates = (
        current.join(
            previous,
            (F.col("current.ticker") == F.col("previous.ticker"))
            & (F.col("previous.trading_date") < F.col("current.trading_date"))
            & (F.col("previous.known_from_ts") <= F.col("current.known_from_ts")),
            "left",
        )
        .groupBy(F.col("current.__row_id").alias("__row_id"))
        .agg(F.max(F.col("previous.trading_date")).alias("__prior_date"))
    )
    previous_as_of = (
        current.join(
            previous,
            (F.col("current.ticker") == F.col("previous.ticker"))
            & (F.col("previous.known_from_ts") <= F.col("current.known_from_ts")),
            "left",
        )
        .join(
            prior_dates,
            F.col("current.__row_id") == F.col("__row_id"),
            "left",
        )
        .filter(F.col("previous.trading_date") == F.col("__prior_date"))
        .groupBy(F.col("current.__row_id").alias("__row_id"))
        .agg(
            F.max_by(
                F.col("previous.close_price").cast("double"),
                F.col("previous.known_from_ts"),
            ).alias("__previous_close")
        )
    )
    fact = (
        base.join(previous_as_of, "__row_id", "left")
        .withColumn(
            "daily_return",
            F.when(
                F.col("__previous_close").isNull() | (F.col("__previous_close") == 0),
                F.lit(None).cast("double"),
            ).otherwise(
                (F.col("close_price").cast("double") - F.col("__previous_close"))
                / F.col("__previous_close")
            ),
        )
        .withColumn("volatility_signal", F.abs(F.col("daily_return")) > F.lit(0.07))
        .drop("__previous_close", "__row_id")
    )
    if fact.filter(F.col("known_from_ts").isNull()).limit(1).count():
        raise ValueError("known_from_ts, event_timestamp, or created_ts is required")
    return resolve_company_version_key_spark(fact, dim_company_dataframe)
