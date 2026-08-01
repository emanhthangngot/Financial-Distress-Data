"""Evidence-driven Spark plan for generated skew, cardinality, evolution, and duplicates."""

from __future__ import annotations

from typing import Any


def align_statement_versions_optimized(statements: Any) -> Any:
    """Merge physical schema versions without per-field branching."""
    from pyspark.sql import functions as F

    old = statements.filter(F.col("schema_version") == 1).drop(
        "operating_cash_flow", "retained_earnings", "statement_type"
    )
    new = statements.filter(F.col("schema_version") == 2)
    return old.unionByName(new, allowMissingColumns=True)


def _latest_by_key(dataframe: Any, keys: list[str]) -> Any:
    from pyspark.sql import functions as F

    value_columns = [column for column in dataframe.columns if column not in keys]
    latest = F.max_by(F.struct(*[F.col(column) for column in value_columns]), F.col("created_ts"))
    return (
        dataframe.groupBy(*keys)
        .agg(latest.alias("_latest"))
        .select(*keys, *[F.col(f"_latest.{column}").alias(column) for column in value_columns])
    )


def build_optimized_plan(companies: Any, statements: Any, salt_buckets: int = 8) -> Any:
    """Use latest-row aggregation, broadcast join, and deterministic salting."""
    from pyspark.sql import functions as F

    latest_companies = _latest_by_key(companies, ["ticker"])
    aligned = align_statement_versions_optimized(statements)
    latest_statements = _latest_by_key(aligned, ["ticker", "report_period"])
    joined = latest_statements.join(
        F.broadcast(latest_companies.select("ticker", "sector")),
        "ticker",
        "inner",
    ).withColumn("sector", F.coalesce(F.col("sector"), F.lit("Unknown")))
    per_company = joined.groupBy("sector", "ticker").agg(
        F.count("*").alias("statement_count"),
        F.count("source_record_id").alias("source_id_count"),
        F.sum(F.col("total_assets").cast("decimal(38,2)")).alias("total_assets"),
    )
    salted = per_company.withColumn("_salt", F.pmod(F.xxhash64("ticker"), F.lit(salt_buckets)))
    partial = salted.groupBy("sector", "_salt").agg(
        F.count("ticker").alias("company_count"),
        F.sum("statement_count").alias("statement_count"),
        F.sum("source_id_count").alias("source_id_count"),
        F.sum("total_assets").alias("total_assets"),
    )
    return (
        partial.groupBy("sector")
        .agg(
            F.sum("company_count").alias("company_count"),
            F.sum("statement_count").alias("statement_count"),
            F.sum("source_id_count").alias("source_id_count"),
            F.sum("total_assets").alias("total_assets"),
        )
        .orderBy("sector")
    )
