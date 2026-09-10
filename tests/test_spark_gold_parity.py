from __future__ import annotations

import os
import sys
from datetime import date

import pytest
from pyspark.sql.types import StringType, StructField, StructType

from src.transforms.gold.fact_financial_statement import (
    build_fact_financial_statement,
    build_fact_financial_statement_spark,
)
from src.transforms.gold.fact_market_price import (
    build_fact_market_price,
    build_fact_market_price_spark,
)
from src.transforms.keys import company_version_key

try:
    from pyspark.sql import SparkSession
except ImportError:  # pragma: no cover - exercised by the lightweight CI stub
    SparkSession = None  # type: ignore[assignment]


pytestmark = pytest.mark.skipif(SparkSession is None, reason="PySpark runtime is unavailable")


@pytest.fixture(scope="module")
def spark():
    os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    session = (
        SparkSession.builder.master("local[2]")
        .appName("financial-distress-gold-parity-test")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    yield session
    session.stop()


def _dimension() -> list[dict[str, object]]:
    return [
        {
            "ticker": "ABC",
            "valid_from_ts": "2020-01-01T00:00:00+00:00",
            "valid_to_ts": None,
            "company_version_key": company_version_key("ABC", "2020-01-01T00:00:00+00:00"),
        }
    ]


def _dimension_dataframe(spark):
    schema = StructType(
        [
            StructField("ticker", StringType(), nullable=False),
            StructField("valid_from_ts", StringType(), nullable=False),
            StructField("valid_to_ts", StringType(), nullable=True),
            StructField("company_version_key", StringType(), nullable=False),
        ]
    )
    return spark.createDataFrame(_dimension(), schema=schema)


def test_financial_variant_election_matches_python(spark) -> None:
    rows = [
        {
            "ticker": "ABC",
            "report_period": "2024Q1",
            "statement_variant": "consolidated_unaudited",
            "known_from_ts": "2024-04-01T00:00:00+00:00",
            "created_ts": "2024-04-01T01:00:00+00:00",
        },
        {
            "ticker": "ABC",
            "report_period": "2024Q1",
            "statement_variant": "consolidated_audited",
            "known_from_ts": "2024-04-01T00:00:00+00:00",
            "created_ts": "2024-04-02T01:00:00+00:00",
        },
    ]
    python_rows = build_fact_financial_statement(rows, _dimension())
    spark_rows = (
        build_fact_financial_statement_spark(
            spark.createDataFrame(rows), _dimension_dataframe(spark)
        )
        .select("statement_variant", "is_latest_vintage")
        .collect()
    )
    assert sorted(
        (row["statement_variant"], row["is_latest_vintage"]) for row in python_rows
    ) == sorted((row["statement_variant"], row["is_latest_vintage"]) for row in spark_rows)


def test_market_daily_return_and_null_volatility_match_python(spark) -> None:
    rows = [
        {
            "ticker": "ABC",
            "trading_date": date(2024, 1, 1),
            "close_price": 100.0,
            "known_from_ts": "2024-01-01T00:00:00+00:00",
        },
        {
            "ticker": "ABC",
            "trading_date": date(2024, 1, 2),
            "close_price": 110.0,
            "known_from_ts": "2024-01-02T00:00:00+00:00",
        },
    ]
    python_rows = build_fact_market_price(rows, _dimension())
    spark_rows = (
        build_fact_market_price_spark(spark.createDataFrame(rows), _dimension_dataframe(spark))
        .select("trading_date", "daily_return", "volatility_signal")
        .orderBy("trading_date")
        .collect()
    )
    assert [(row["daily_return"], row["volatility_signal"]) for row in python_rows] == [
        (row["daily_return"], row["volatility_signal"]) for row in spark_rows
    ]
