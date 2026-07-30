"""Intentionally unoptimized but correct Spark benchmark plan."""

from __future__ import annotations

from typing import Any

EVOLVED_FIELDS = {
    "operating_cash_flow": "double",
    "retained_earnings": "double",
    "statement_type": "string",
}


def align_statement_versions_baseline(statements: Any) -> Any:
    """Align old/new schemas manually to preserve a measurable baseline."""
    from pyspark.sql import functions as F

    old = statements.filter(F.col("schema_version") == 1)
    for field, spark_type in EVOLVED_FIELDS.items():
        old = old.drop(field).withColumn(field, F.lit(None).cast(spark_type))
    new = statements.filter(F.col("schema_version") == 2)
    return old.select(*new.columns).union(new.select(*new.columns))


def build_baseline_plan(companies: Any, statements: Any) -> Any:
    """Build a shuffle-heavy reference result for correctness comparison."""
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window

    company_window = Window.partitionBy("ticker").orderBy(F.col("created_ts").desc())
    latest_companies = (
        companies.withColumn("_rn", F.row_number().over(company_window))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )
    statement_window = Window.partitionBy("ticker", "report_period").orderBy(
        F.col("created_ts").desc()
    )
    aligned = align_statement_versions_baseline(statements)
    latest_statements = (
        aligned.withColumn("_rn", F.row_number().over(statement_window))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )
    joined = latest_statements.join(
        latest_companies.select("ticker", "sector"),
        "ticker",
        "inner",
    ).withColumn("sector", F.coalesce(F.col("sector"), F.lit("Unknown")))
    return (
        joined.groupBy("sector")
        .agg(
            F.countDistinct("ticker").alias("company_count"),
            F.count("*").alias("statement_count"),
            F.countDistinct("source_record_id").alias("source_id_count"),
            F.sum(F.col("total_assets").cast("decimal(38,2)")).alias("total_assets"),
        )
        .orderBy("sector")
    )
