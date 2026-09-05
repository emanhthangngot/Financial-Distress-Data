"""
platform data quality job.

Runs the DQ check catalog against the Bronze, Silver, and Gold zones and persists the results. Used
by DAG 07 to gate downstream tasks.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from src.jobs.lakehouse_evidence_job import _ensure_bucket, _minio_client
from src.metadata.metadata_writer import utc_now_iso


def read_minio_parquet_rows(bucket: str, prefix: str) -> list[dict[str, Any]]:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("PyArrow is required to read platform DQ parquet inputs.") from exc

    client = _minio_client()
    _ensure_bucket(client, bucket)
    rows: list[dict[str, Any]] = []
    objects = [
        item.object_name
        for item in client.list_objects(bucket, prefix=prefix, recursive=True)
        if item.object_name.endswith(".parquet")
    ]
    if not objects:
        raise RuntimeError(f"No parquet objects found under s3://{bucket}/{prefix}")

    for object_name in objects:
        response = client.get_object(bucket, object_name)
        try:
            data = response.read()
        finally:
            response.close()
            response.release_conn()
        rows.extend(pq.read_table(BytesIO(data)).to_pylist())
    return rows


def build_actual_dq_checks(
    bucket: str, reference_timestamp: str | None = None
) -> list[dict[str, Any]]:
    silver_companies = read_minio_parquet_rows(bucket, "silver/companies/")
    gold_financial = read_minio_parquet_rows(bucket, "gold/fact_financial_statement/")
    gold_dim_company = read_minio_parquet_rows(bucket, "gold/dim_company/")
    gold_market = read_minio_parquet_rows(bucket, "gold/fact_market_price/")
    gold_alert = read_minio_parquet_rows(bucket, "gold/fact_market_alert/")
    gold_news = read_minio_parquet_rows(bucket, "gold/fact_news_sentiment/")
    gold_obt = read_minio_parquet_rows(bucket, "gold/obt_company_quarter_risk/")
    silver_market = read_minio_parquet_rows(bucket, "silver/market_prices_daily/")
    company_version_keys = {row.get("company_version_key") for row in gold_dim_company}

    return [
        {
            "type": "unique",
            "dataset_name": "silver_companies",
            "rows": silver_companies,
            "fields": ["ticker", "created_ts"],
        },
        {
            "type": "not_null",
            "dataset_name": "gold_fact_financial_statement",
            "rows": gold_financial,
            "field": "company_version_key",
        },
        {
            "type": "unique",
            "dataset_name": "gold_fact_financial_statement",
            "rows": gold_financial,
            "fields": [
                "ticker",
                "report_period",
                "statement_variant",
                "known_from_ts",
            ],
        },
        {
            "type": "referential_integrity",
            "dataset_name": "gold_fact_financial_statement",
            "fact_rows": gold_financial,
            "dimension_keys": company_version_keys,
            "field": "company_version_key",
        },
        {
            "type": "unique",
            "dataset_name": "gold_fact_market_price",
            "rows": gold_market,
            "fields": ["ticker", "trading_date", "known_from_ts"],
        },
        {
            "type": "referential_integrity",
            "dataset_name": "gold_fact_market_price",
            "fact_rows": gold_market,
            "dimension_keys": company_version_keys,
            "field": "company_version_key",
        },
        {
            "type": "unique",
            "dataset_name": "gold_fact_news_sentiment",
            "rows": gold_news,
            "fields": ["event_id"],
        },
        {
            "type": "unique",
            "dataset_name": "gold_fact_market_alert",
            "rows": gold_alert,
            "fields": ["event_id"],
        },
        {
            "type": "referential_integrity",
            "dataset_name": "gold_fact_market_alert",
            "fact_rows": gold_alert,
            "dimension_keys": company_version_keys,
            "field": "company_version_key",
        },
        {
            "type": "referential_integrity",
            "dataset_name": "gold_fact_news_sentiment",
            "fact_rows": gold_news,
            "dimension_keys": company_version_keys,
            "field": "company_version_key",
        },
        {
            "type": "unique",
            "dataset_name": "gold_obt_company_quarter_risk",
            "rows": gold_obt,
            "fields": ["ticker", "report_period"],
        },
        {
            "type": "freshness",
            "dataset_name": "silver_market_prices",
            "rows": silver_market,
            "reference_timestamp": reference_timestamp or utc_now_iso(),
            "sla_minutes": 120,
            "timestamp_field": "event_timestamp",
        },
    ]


def build_intentional_dq_failure_checks() -> list[dict[str, Any]]:
    return [
        {
            "type": "not_null",
            "dataset_name": "dq_failure_probe_companies",
            "rows": [{"ticker": None, "created_ts": "2026-01-01T00:00:00+00:00"}],
            "field": "ticker",
        }
    ]
