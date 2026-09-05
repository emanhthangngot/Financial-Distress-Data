"""platform rejection persistence and pre-publication quality gates."""

from __future__ import annotations

import json
from typing import Any

from src.jobs.lakehouse_evidence_job import metadata_dsn
from src.metadata.metadata_writer import PostgresMetadataWriter, psycopg_connection_factory

PUBLISHED_PREFIXES = [
    "silver/companies/",
    "silver/financial_statements/",
    "silver/market_prices_daily/",
    "gold/dim_company/",
    "gold/fact_financial_statement/",
    "gold/fact_market_price/",
    "gold/distress_labels/",
    "gold/dim_date/",
    "gold/obt_company_quarter_risk/",
    "gold/fact_market_alert/",
    "gold/fact_news_sentiment/",
    "gold/feat_company_financial_4q/",
    "gold/feat_company_market_30d/",
    "gold/feat_company_news_30d/",
    "gold/feat_company_unified/",
]


def persist_failed_rows(failed_by_dataset: dict[str, Any], run_id: str) -> int:
    """Persist Spark quarantine rows into PostgreSQL before publication."""
    writer = PostgresMetadataWriter(psycopg_connection_factory(metadata_dsn()))
    count = 0
    for dataset, dataframe in failed_by_dataset.items():
        records = []
        for row in dataframe.select("failure_reason", "raw_payload").toLocalIterator():
            raw_payload = row["raw_payload"]
            records.append(
                {
                    "failure_reason": row["failure_reason"],
                    "raw_payload": (
                        json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
                    ),
                }
            )
        writer.log_failed_records(dataset, records, run_id=run_id)
        count += len(records)
    return count


def validate_publication_counts(counts: dict[str, int]) -> None:
    """Reject a publication missing any core Silver or Gold dataset."""
    required = (
        "silver_companies",
        "silver_financial_statements",
        "silver_market_prices",
        "gold_dim_company",
        "gold_fact_financial_statement",
        "gold_fact_market_price",
    )
    missing = [name for name in required if counts.get(name, 0) <= 0]
    if missing:
        raise RuntimeError(f"publication DQ failed for empty datasets: {', '.join(missing)}")


def validate_spark_outputs(
    dim_company: Any,
    silver_companies: Any,
    financial_fact: Any,
    market_fact: Any,
    alert_fact: Any,
    news_fact: Any,
    obt: Any,
) -> None:
    """Run critical uniqueness and referential checks before publication."""
    checks = (
        (silver_companies, ["ticker", "created_ts"], "silver_companies"),
        (
            financial_fact,
            ["ticker", "report_period", "statement_variant", "known_from_ts"],
            "fact_financial_statement",
        ),
        (market_fact, ["ticker", "trading_date", "known_from_ts"], "fact_market_price"),
        (alert_fact, ["event_id"], "fact_market_alert"),
        (news_fact, ["event_id"], "fact_news_sentiment"),
        (obt, ["ticker", "report_period"], "obt_company_quarter_risk"),
    )
    errors = []
    for dataframe, keys, name in checks:
        if dataframe.groupBy(*keys).count().filter("count > 1").limit(1).count():
            errors.append(f"{name} duplicate key: {keys}")

    dimension_keys = dim_company.select("company_version_key").distinct()
    for dataframe, name in (
        (financial_fact, "fact_financial_statement"),
        (market_fact, "fact_market_price"),
        (alert_fact, "fact_market_alert"),
        (news_fact, "fact_news_sentiment"),
    ):
        missing = (
            dataframe.filter("company_version_key IS NULL")
            .select("company_version_key")
            .union(
                dataframe.select("company_version_key").join(
                    dimension_keys,
                    "company_version_key",
                    "left_anti",
                )
            )
            .limit(1)
            .count()
        )
        if missing:
            errors.append(f"{name} has missing company_version_key relationship")
    if errors:
        raise RuntimeError("publication DQ failed: " + "; ".join(errors))
