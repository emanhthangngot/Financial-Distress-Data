from __future__ import annotations

from typing import Any

from src.transforms.keys import date_key, stable_company_key


def build_fact_market_price(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts = []
    previous_close_by_ticker: dict[str, float] = {}
    for row in sorted(rows, key=lambda item: (item["ticker"], item["trading_date"])):
        fact = dict(row)
        fact["ticker"] = str(row["ticker"]).upper()
        fact["company_key"] = stable_company_key(fact["ticker"])
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


def build_fact_market_price_spark(dataframe: Any) -> Any:
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
    return (
        dataframe.withColumn("ticker", F.upper(F.col("ticker")))
        .withColumn("company_key", F.substring(F.sha2(F.upper(F.col("ticker")), 256), 1, 16))
        .withColumn("date_key", F.date_format(F.to_date("trading_date"), "yyyyMMdd").cast("int"))
        .withColumn("daily_return", daily_return)
        .withColumn("volatility_signal", F.abs(F.col("daily_return")) > F.lit(0.07))
    )
