from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

try:
    import pyspark
    from pyspark.sql import SparkSession
except ImportError:
    pytest.skip("real PySpark is required for Gold value parity", allow_module_level=True)

if getattr(pyspark, "__file__", None) is None:
    pytest.skip("real PySpark is required for Gold value parity", allow_module_level=True)

from src.jobs.lakehouse_spark_lakehouse_job import (
    _bundled_hadoop_version,
    _spark_runtime_packages,
    build_dim_company_spark,
    build_feat_company_financial_4q_spark,
    spark_runtime_config,
)
from src.transforms.gold.dim_company import build_dim_company
from src.transforms.gold.fact_financial_statement import (
    build_fact_financial_statement,
    build_fact_financial_statement_spark,
)
from src.transforms.gold.fact_market_price import (
    build_fact_market_price,
    build_fact_market_price_spark,
)
from src.transforms.gold.fact_news_sentiment import (
    build_fact_news_sentiment,
    build_fact_news_sentiment_spark,
)

COMPANY_ROWS = [
    {
        "ticker": "aaa",
        "company_name": "Fixture Manufacturing",
        "exchange": "TEST",
        "industry": "Manufacturing",
        "sector": "Industrials",
        "listing_date": "2020-01-01",
        "delisted_flag": False,
        "created_ts": "2020-01-01T00:00:00+00:00",
    },
    {
        "ticker": "aaa",
        "company_name": "Fixture Manufacturing Holdings",
        "exchange": "TEST",
        "industry": "Manufacturing",
        "sector": "Industrials",
        "listing_date": "2020-01-01",
        "delisted_flag": False,
        "created_ts": "2025-02-01T00:00:00+00:00",
    },
]

FINANCIAL_ROWS = [
    {
        "ticker": "aaa",
        "report_period": "2024Q4",
        "statement_variant": "consolidated_unaudited",
        "report_release_date": "2025-01-15T08:00:00+00:00",
        "created_ts": "2025-01-15T08:05:00+00:00",
        "total_assets": 1_000_000,
        "total_liabilities": 600_000,
        "equity": 400_000,
        "current_assets": 350_000,
        "current_liabilities": 250_000,
        "retained_earnings": 120_000,
        "net_income": 45_000,
        "ebit": 70_000,
        "interest_expense": 10_000,
        "source_name": "test_fixture",
        "source_unit": "VND",
        "is_synthetic": True,
    },
    {
        "ticker": "aaa",
        "report_period": "2024Q4",
        "statement_variant": "consolidated_audited",
        "report_release_date": "2025-02-10T08:00:00+00:00",
        "created_ts": "2025-02-10T08:05:00+00:00",
        "total_assets": 1_020_000,
        "total_liabilities": 610_000,
        "equity": 410_000,
        "current_assets": 360_000,
        "current_liabilities": 255_000,
        "retained_earnings": 125_000,
        "net_income": 48_000,
        "ebit": 72_000,
        "interest_expense": 10_000,
        "source_name": "test_fixture",
        "source_unit": "VND",
        "is_synthetic": True,
    },
    {
        "ticker": "aaa",
        "report_period": "2025Q1",
        "statement_variant": "consolidated_unaudited",
        "report_release_date": "2025-05-10T08:00:00+00:00",
        "created_ts": "2025-05-10T08:05:00+00:00",
        "total_assets": 1_050_000,
        "total_liabilities": 620_000,
        "equity": 430_000,
        "current_assets": 370_000,
        "current_liabilities": 260_000,
        "retained_earnings": 130_000,
        "net_income": 50_000,
        "ebit": 75_000,
        "interest_expense": 10_000,
        "source_name": "test_fixture",
        "source_unit": "VND",
        "is_synthetic": True,
    },
]

MARKET_ROWS = [
    {
        "ticker": "aaa",
        "trading_date": "2025-02-02",
        "event_timestamp": "2025-02-02T10:00:00+00:00",
        "created_ts": "2025-02-02T10:01:00+00:00",
        "close_price": 100_000,
        "volume": 1_000,
        "source_name": "test_fixture",
        "source_unit": "VND",
        "is_synthetic": True,
    },
    {
        "ticker": "aaa",
        "trading_date": "2025-02-03",
        "event_timestamp": "2025-02-03T10:00:00+00:00",
        "created_ts": "2025-02-03T10:01:00+00:00",
        "close_price": 110_000,
        "volume": 1_100,
        "source_name": "test_fixture",
        "source_unit": "VND",
        "is_synthetic": True,
    },
    {
        "ticker": "aaa",
        "trading_date": "2025-02-02",
        "event_timestamp": "2025-02-04T10:00:00+00:00",
        "created_ts": "2025-02-04T10:01:00+00:00",
        "close_price": 80_000,
        "volume": 1_050,
        "source_name": "test_fixture",
        "source_unit": "VND",
        "is_synthetic": True,
    },
    {
        "ticker": "aaa",
        "trading_date": "2025-02-03",
        "event_timestamp": "2025-02-05T10:00:00+00:00",
        "created_ts": "2025-02-05T10:01:00+00:00",
        "close_price": 84_000,
        "volume": 1_150,
        "source_name": "test_fixture",
        "source_unit": "VND",
        "is_synthetic": True,
    },
]

NEWS_ROWS = [
    {
        "event_id": "fixture-news-1",
        "ticker": "aaa",
        "event_timestamp": "2025-02-06T09:00:00+00:00",
        "created_ts": "2025-02-06T09:01:00+00:00",
        "sentiment_score": -0.4,
        "risk_keyword_flag": True,
        "severity_score": 0.8,
        "source_url": "fixture://news/1",
        "source_name": "test_fixture",
        "is_synthetic": True,
    },
]

FINANCIAL_FIELDS = (
    "ticker",
    "report_period",
    "statement_variant",
    "known_from_ts",
    "report_release_date",
    "created_ts",
    "company_version_key",
    "date_key",
    "is_latest_vintage",
    "total_assets",
    "total_liabilities",
    "equity",
    "current_assets",
    "current_liabilities",
    "retained_earnings",
    "net_income",
    "ebit",
    "interest_expense",
    "source_name",
    "source_unit",
    "is_synthetic",
)

MARKET_FIELDS = (
    "ticker",
    "trading_date",
    "known_from_ts",
    "event_timestamp",
    "created_ts",
    "company_version_key",
    "date_key",
    "close_price",
    "volume",
    "daily_return",
    "volatility_signal",
    "source_name",
    "source_unit",
    "is_synthetic",
)

NEWS_FIELDS = (
    "event_id",
    "ticker",
    "event_timestamp",
    "known_from_ts",
    "created_ts",
    "company_version_key",
    "date_key",
    "sentiment_score",
    "risk_keyword_flag",
    "severity_score",
    "source_name",
    "is_synthetic",
)

TIMESTAMP_FIELDS = {
    "known_from_ts",
    "report_release_date",
    "event_timestamp",
    "created_ts",
}


@pytest.fixture(scope="module")
def spark():
    previous_worker_python = os.environ.get("PYSPARK_PYTHON")
    os.environ["PYSPARK_PYTHON"] = sys.executable
    session = (
        SparkSession.builder.master("local[1]")
        .appName("gold-value-parity")
        .config("spark.ui.enabled", "false")
        .config("spark.pyspark.python", sys.executable)
        .config("spark.pyspark.driver.python", sys.executable)
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "1")
        .getOrCreate()
    )
    try:
        yield session
    finally:
        session.stop()
        if previous_worker_python is None:
            os.environ.pop("PYSPARK_PYTHON", None)
        else:
            os.environ["PYSPARK_PYTHON"] = previous_worker_python


def _utc_iso(value: object) -> str:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.astimezone(UTC).isoformat()


def _project(rows: list[dict[str, object]], fields: tuple[str, ...]) -> list[tuple[object, ...]]:
    projected = []
    for row in rows:
        values = []
        for field in fields:
            value = row[field]
            if field in TIMESTAMP_FIELDS:
                value = _utc_iso(value)
            elif isinstance(value, float):
                value = round(value, 12)
            values.append(value)
        projected.append(tuple(values))
    return sorted(projected, key=repr)


def test_runtime_packages_match_hadoop_bundled_with_installed_pyspark(monkeypatch) -> None:
    monkeypatch.setenv("MINIO_ROOT_USER", "test-user")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "test-password")

    hadoop_version = _bundled_hadoop_version()
    jars_dir = Path(pyspark.__file__).resolve().parent / "jars"
    packages = set(spark_runtime_config("http://minio:9000")["spark.jars.packages"].split(","))

    assert (jars_dir / f"hadoop-client-api-{hadoop_version}.jar").is_file()
    assert (jars_dir / f"hadoop-client-runtime-{hadoop_version}.jar").is_file()
    assert f"org.apache.hadoop:hadoop-aws:{hadoop_version}" in packages
    assert "software.amazon.awssdk:bundle:2.35.4" in packages
    assert not any(package.startswith("com.amazonaws:aws-java-sdk") for package in packages)


def test_runtime_package_resolution_rejects_mismatched_hadoop_jars(tmp_path, monkeypatch) -> None:
    (tmp_path / "hadoop-client-api-3.5.0.jar").touch()
    (tmp_path / "hadoop-client-runtime-3.3.4.jar").touch()
    monkeypatch.setattr(
        "src.jobs.lakehouse_spark_lakehouse_job._pyspark_jars_dir",
        lambda: tmp_path,
    )

    with pytest.raises(RuntimeError, match="Unable to resolve one bundled Hadoop version"):
        _bundled_hadoop_version()


def test_runtime_packages_support_hadoop_3_3_4_v1_connector(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.jobs.lakehouse_spark_lakehouse_job._bundled_hadoop_version",
        lambda: "3.3.4",
    )

    assert _spark_runtime_packages() == (
        "org.apache.hadoop:hadoop-aws:3.3.4," "com.amazonaws:aws-java-sdk-bundle:1.12.262"
    )


def test_financial_gold_values_match_python_for_same_fixture_rows(spark) -> None:
    python_dimension = build_dim_company(COMPANY_ROWS)
    spark_dimension = build_dim_company_spark(spark.createDataFrame(COMPANY_ROWS))

    python_facts = build_fact_financial_statement(FINANCIAL_ROWS, python_dimension)
    spark_facts = [
        row.asDict(recursive=True)
        for row in build_fact_financial_statement_spark(
            spark.createDataFrame(FINANCIAL_ROWS), spark_dimension
        ).collect()
    ]

    assert _project(spark_facts, FINANCIAL_FIELDS) == _project(python_facts, FINANCIAL_FIELDS)


def test_market_gold_values_match_python_for_same_fixture_rows(spark) -> None:
    python_dimension = build_dim_company(COMPANY_ROWS)
    spark_dimension = build_dim_company_spark(spark.createDataFrame(COMPANY_ROWS))

    python_facts = build_fact_market_price(MARKET_ROWS, python_dimension)
    spark_facts = [
        row.asDict(recursive=True)
        for row in build_fact_market_price_spark(
            spark.createDataFrame(MARKET_ROWS), spark_dimension
        ).collect()
    ]

    assert _project(spark_facts, MARKET_FIELDS) == _project(python_facts, MARKET_FIELDS)


def test_news_input_produces_nonzero_value_matching_gold_facts(spark) -> None:
    python_dimension = build_dim_company(COMPANY_ROWS)
    spark_dimension = build_dim_company_spark(spark.createDataFrame(COMPANY_ROWS))

    python_facts = build_fact_news_sentiment(NEWS_ROWS, python_dimension)
    spark_facts = [
        row.asDict(recursive=True)
        for row in build_fact_news_sentiment_spark(
            spark.createDataFrame(NEWS_ROWS), spark_dimension
        ).collect()
    ]

    assert len(spark_facts) == len(python_facts) == len(NEWS_ROWS) == 1
    assert _project(spark_facts, NEWS_FIELDS) == _project(python_facts, NEWS_FIELDS)


def test_spark_financial_feature_writer_matches_feast_source_contract(spark) -> None:
    rows = [
        {
            "ticker": "aaa",
            "report_period": f"2025Q{quarter}",
            "known_from_ts": f"2025-{quarter * 3:02d}-01T00:00:00+00:00",
            "report_release_date": f"2025-{quarter * 3:02d}-01T00:00:00+00:00",
            "event_timestamp": f"2025-{quarter * 3:02d}-01T00:00:00+00:00",
            "created_ts": f"2025-{quarter * 3:02d}-01T00:01:00+00:00",
            "current_ratio": 1.0,
            "debt_to_asset": 0.5,
            "debt_to_equity": 1.0,
            "roa": 0.1,
            "roe": 0.2,
            "ebit_interest_coverage": 3.0,
            "z_score": 2.0,
        }
        for quarter in range(1, 5)
    ]

    output = build_feat_company_financial_4q_spark(spark.createDataFrame(rows))
    result = output.orderBy("known_from_ts").collect()

    assert {
        "created_timestamp",
        "window_period_count",
        "feature_completeness",
    }.issubset(output.columns)
    assert result[-1]["window_period_count"] == 4
    assert result[-1]["feature_completeness"] == pytest.approx(1.0)
