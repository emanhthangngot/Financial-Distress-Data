"""
Canonical S3A path scheme for Bronze, Silver, and Gold zones.

Single source of truth for MinIO bucket + zone + partition layout. Every PySpark job and DuckDB view
must resolve paths via this module so that the lakehouse layout is rename-safe.
"""

from __future__ import annotations

DEFAULT_BUCKET = "financial-distress-lake"


def dataset_object_key(bucket: str, layer: str, dataset_name: str) -> str:
    return f"{bucket}/{layer}/{dataset_name}/data.parquet"


def lakehouse_dataset_object_keys(bucket: str = DEFAULT_BUCKET) -> list[str]:
    # NOTE: these are the v1 physical MinIO object names, matching what
    # src/jobs/lakehouse_spark_lakehouse_job.py actually reads/writes today.
    # The v2 logical schema (sql/schema_evidence.sql, raw_/stg_/
    # fact_distress_label) is landed; renaming the physical storage layer to
    # match — and adding real partitioning — is deferred: it requires
    # rewiring every read/write call in the Spark job in lockstep, not just
    # this list, and is unverified without a running Spark+MinIO stack.
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


def partitioned_object_key(bucket: str, layer: str, dataset_name: str, partition_value: str) -> str:
    """Hive-style partitioned prefix for a Gold dataset (AC-P2-12).

    ``partition_value`` is a pre-formatted partition string, e.g.
    ``known_from_month=2023-08`` for ``month(known_from_ts)`` (statements) or
    ``trading_date=2023-08-01`` for ``day(trading_date)`` (prices) — the two
    partition grains the plan specifies. Callers own the formatting; this
    function only owns the path shape so every writer stays rename-safe.
    """
    return f"{bucket}/{layer}/{dataset_name}/{partition_value}/data.parquet"
