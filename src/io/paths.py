"""
Canonical S3A path scheme for Bronze, Silver, and Gold zones.

Single source of truth for MinIO bucket + zone + partition layout. Every PySpark job and DuckDB view
must resolve paths via this module so that the lakehouse layout is rename-safe.
"""

from __future__ import annotations

DEFAULT_BUCKET = "financial-distress-lake"


def dataset_object_key(bucket: str, layer: str, dataset_name: str) -> str:
    return f"{bucket}/{layer}/{dataset_name}/data.parquet"


def stage1_dataset_object_keys(bucket: str = DEFAULT_BUCKET) -> list[str]:
    datasets = [
        ("bronze", "companies"),
        ("bronze", "financial_statements"),
        ("bronze", "market_prices_daily"),
        ("silver", "companies"),
        ("silver", "financial_statements"),
        ("silver", "market_prices_daily"),
        ("gold", "dim_company"),
        ("gold", "dim_date"),
        ("gold", "fact_financial_statement"),
        ("gold", "fact_market_alert"),
        ("gold", "fact_market_price"),
        ("gold", "fact_news_sentiment"),
        ("gold", "distress_labels"),
        ("gold", "obt_company_quarter_risk"),
        ("gold", "feat_company_financial_4q"),
        ("gold", "feat_company_market_30d"),
        ("gold", "feat_company_news_30d"),
        ("gold", "feat_company_unified"),
    ]
    return [dataset_object_key(bucket, layer, dataset_name) for layer, dataset_name in datasets]
