from __future__ import annotations

from typing import Any

from src.transforms.keys import date_key, stable_company_key


def build_fact_financial_statement(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts = []
    for row in rows:
        reference_date = (
            row.get("report_release_date")
            or row.get("event_timestamp")
            or f"{row['fiscal_year']}-01-01"
        )
        fact = dict(row)
        fact["ticker"] = str(row["ticker"]).upper()
        fact["company_key"] = stable_company_key(fact["ticker"])
        fact["date_key"] = date_key(reference_date)
        facts.append(fact)
    return facts


def build_fact_financial_statement_spark(dataframe: Any) -> Any:
    try:
        from pyspark.sql import functions as F
    except ImportError as exc:
        raise RuntimeError("PySpark is required for Spark Gold transforms.") from exc

    reference_date = F.coalesce(
        F.to_date("report_release_date"),
        F.to_date("event_timestamp"),
        F.to_date(F.concat(F.col("fiscal_year").cast("string"), F.lit("-01-01"))),
    )
    return (
        dataframe.withColumn("ticker", F.upper(F.col("ticker")))
        .withColumn("company_key", F.substring(F.sha2(F.upper(F.col("ticker")), 256), 1, 16))
        .withColumn("date_key", F.date_format(reference_date, "yyyyMMdd").cast("int"))
    )
