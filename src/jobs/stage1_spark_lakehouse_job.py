from __future__ import annotations

import os
from typing import Any

from src.io.minio_writer import clear_minio_prefix
from src.io.paths import DEFAULT_BUCKET
from src.jobs.stage1_evidence_job import _ensure_bucket, _minio_client
from src.metadata.schema_registry import InMemorySchemaRegistry
from src.transforms.bronze_to_silver import bronze_to_silver_spark
from src.transforms.compute_distress_labels import compute_labels
from src.transforms.features.pit import (
    build_feat_company_financial_4q,
    build_feat_company_market_30d,
    build_feat_company_news_30d,
    build_feat_company_unified,
)
from src.transforms.gold.dim_company import build_dim_company, build_dim_date
from src.transforms.gold.fact_financial_statement import build_fact_financial_statement_spark
from src.transforms.gold.fact_market_alert import build_fact_market_alert
from src.transforms.gold.fact_market_price import build_fact_market_price_spark
from src.transforms.gold.fact_news_sentiment import build_fact_news_sentiment
from src.transforms.gold.obt_company_quarter_risk import build_obt_company_quarter_risk

SPARK_HADOOP_AWS_PACKAGE = "org.apache.hadoop:hadoop-aws:3.3.4"
SPARK_AWS_SDK_PACKAGE = "com.amazonaws:aws-java-sdk-bundle:1.12.262"


def spark_runtime_config(minio_endpoint: str | None = None) -> dict[str, str]:
    endpoint = minio_endpoint or os.getenv("MINIO_ENDPOINT", "http://minio:9000")
    return {
        "spark.jars.packages": f"{SPARK_HADOOP_AWS_PACKAGE},{SPARK_AWS_SDK_PACKAGE}",
        "spark.hadoop.fs.s3a.endpoint": endpoint,
        "spark.hadoop.fs.s3a.access.key": os.getenv("MINIO_ROOT_USER", "minioadmin"),
        "spark.hadoop.fs.s3a.secret.key": os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
        "spark.hadoop.fs.s3a.path.style.access": "true",
        "spark.hadoop.fs.s3a.connection.ssl.enabled": "false",
        "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
        "spark.sql.sources.partitionOverwriteMode": "dynamic",
    }


def _spark_session(app_name: str = "financial-distress-stage1-real-e2e") -> Any:
    try:
        from pyspark.sql import SparkSession
    except ImportError as exc:
        raise RuntimeError("PySpark is required for the Stage 1 real E2E Spark job.") from exc

    builder = SparkSession.builder.master("local[*]").appName(app_name)
    for key, value in spark_runtime_config().items():
        builder = builder.config(key, value)
    return builder.getOrCreate()


def _silver(
    spark: Any,
    bucket: str,
    dataset: str,
    required: list[str],
    nullable: list[str],
    dedup_keys: list[str],
) -> tuple[Any, Any]:
    bronze = spark.read.parquet(f"s3a://{bucket}/bronze/{dataset}/data.parquet")
    silver, failed = bronze_to_silver_spark(bronze, required, nullable, dedup_keys)
    _cast_nulltype_columns(silver).write.mode("overwrite").parquet(
        f"s3a://{bucket}/silver/{dataset}/"
    )
    return silver, failed


def _cast_nulltype_columns(dataframe: Any) -> Any:
    try:
        from pyspark.sql import functions as F
        from pyspark.sql.types import NullType
    except ImportError as exc:
        raise RuntimeError("PySpark is required to sanitize Spark Parquet writes.") from exc

    output = dataframe
    for field in dataframe.schema.fields:
        if isinstance(field.dataType, NullType):
            output = output.withColumn(field.name, F.col(field.name).cast("string"))
    return output


def _write_rows_with_spark(spark: Any, rows: list[dict[str, Any]], path: str) -> int:
    if not rows:
        return 0
    dataframe = spark.createDataFrame(*_rows_with_schema(rows))
    _cast_nulltype_columns(dataframe).write.mode("overwrite").parquet(path)
    return len(rows)


def _rows_with_schema(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], Any]:
    from datetime import date, datetime

    from pyspark.sql.types import (
        BooleanType,
        DoubleType,
        LongType,
        StringType,
        StructField,
        StructType,
    )

    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)

    schema_fields = []
    string_fields = set()
    for field in fields:
        values = [row.get(field) for row in rows if row.get(field) is not None]
        if not values:
            spark_type = StringType()
            string_fields.add(field)
        elif all(isinstance(value, bool) for value in values):
            spark_type = BooleanType()
        elif all(isinstance(value, int) and not isinstance(value, bool) for value in values):
            spark_type = LongType()
        elif all(
            isinstance(value, (int, float)) and not isinstance(value, bool) for value in values
        ):
            spark_type = DoubleType()
        else:
            spark_type = StringType()
            string_fields.add(field)
        schema_fields.append(StructField(field, spark_type, nullable=True))

    normalized_rows = []
    for row in rows:
        normalized = {}
        for field in fields:
            value = row.get(field)
            if field in string_fields and value is not None:
                if isinstance(value, (date, datetime)):
                    value = value.isoformat()
                else:
                    value = str(value)
            normalized[field] = value
        normalized_rows.append(normalized)

    return normalized_rows, StructType(schema_fields)


def _clear_output_prefixes(bucket: str) -> None:
    client = _minio_client()
    _ensure_bucket(client, bucket)
    for prefix in (
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
    ):
        clear_minio_prefix(client, bucket, prefix)


def _date_bounds(*row_groups: list[dict[str, Any]]) -> tuple[str, str]:
    values = []
    for rows in row_groups:
        for row in rows:
            value = (
                row.get("report_release_date")
                or row.get("trading_date")
                or row.get("event_timestamp")
                or row.get("created_ts")
            )
            if value:
                values.append(str(value)[:10])
    if not values:
        raise RuntimeError("cannot build dim_date without date-bearing rows")
    return min(values), max(values)


def _read_news_bronze_rows(spark: Any, bucket: str) -> list[dict[str, Any]]:
    path = f"s3a://{bucket}/bronze/kafka/financial.news_events/*/*/*/data.parquet"
    try:
        dataframe = spark.read.parquet(path)
    except Exception as exc:
        raise RuntimeError(
            "Stage 1 real E2E requires financial.news_events Bronze parquet before Gold build."
        ) from exc
    return [row.asDict(recursive=True) for row in dataframe.collect()]


def _read_alert_bronze_rows(spark: Any, bucket: str) -> list[dict[str, Any]]:
    path = f"s3a://{bucket}/bronze/kafka/financial.alert_events/*/*/*/data.parquet"
    try:
        dataframe = spark.read.parquet(path)
    except Exception as exc:
        raise RuntimeError(
            "Stage 1 real E2E requires financial.alert_events Bronze parquet before Gold build."
        ) from exc
    return [row.asDict(recursive=True) for row in dataframe.collect()]


def run_stage1_spark_lakehouse(bucket: str = DEFAULT_BUCKET) -> dict[str, int]:
    _clear_output_prefixes(bucket)
    spark = _spark_session()
    registry = InMemorySchemaRegistry()
    try:
        companies_contract = registry.get_current("companies")
        statements_contract = registry.get_current("financial_statements")
        prices_contract = registry.get_current("market_prices_daily")

        silver_companies, failed_companies = _silver(
            spark,
            bucket,
            "companies",
            companies_contract.required,
            companies_contract.nullable,
            ["ticker"],
        )
        silver_financial_statements, failed_statements = _silver(
            spark,
            bucket,
            "financial_statements",
            statements_contract.required,
            statements_contract.nullable,
            ["ticker", "report_period"],
        )
        silver_market_prices, failed_prices = _silver(
            spark,
            bucket,
            "market_prices_daily",
            prices_contract.required,
            prices_contract.nullable,
            ["ticker", "trading_date"],
        )

        financial_fact = build_fact_financial_statement_spark(silver_financial_statements)
        market_fact = build_fact_market_price_spark(silver_market_prices)
        financial_fact.write.mode("overwrite").parquet(
            f"s3a://{bucket}/gold/fact_financial_statement/"
        )
        market_fact.write.mode("overwrite").parquet(f"s3a://{bucket}/gold/fact_market_price/")

        company_rows = [row.asDict(recursive=True) for row in silver_companies.collect()]
        financial_rows = [row.asDict(recursive=True) for row in financial_fact.collect()]
        market_rows = [row.asDict(recursive=True) for row in market_fact.collect()]
        news_rows = _read_news_bronze_rows(spark, bucket)
        alert_rows = _read_alert_bronze_rows(spark, bucket)
        news_fact_rows = build_fact_news_sentiment(news_rows)
        alert_fact_rows = build_fact_market_alert(alert_rows)
        label_rows = compute_labels(financial_rows)
        obt_rows = build_obt_company_quarter_risk(financial_rows, label_rows, market_rows)
        financial_feature_rows = build_feat_company_financial_4q(obt_rows)
        market_feature_rows = build_feat_company_market_30d(market_rows)
        news_feature_rows = build_feat_company_news_30d(news_fact_rows)
        feature_rows = build_feat_company_unified(obt_rows, market_rows)
        dim_rows = build_dim_company(company_rows)
        date_start, date_end = _date_bounds(
            financial_rows, market_rows, news_fact_rows, alert_fact_rows
        )
        date_rows = build_dim_date(date_start, date_end)

        _write_rows_with_spark(spark, dim_rows, f"s3a://{bucket}/gold/dim_company/")
        _write_rows_with_spark(spark, date_rows, f"s3a://{bucket}/gold/dim_date/")
        _write_rows_with_spark(spark, label_rows, f"s3a://{bucket}/gold/distress_labels/")
        _write_rows_with_spark(
            spark,
            news_fact_rows,
            f"s3a://{bucket}/gold/fact_news_sentiment/",
        )
        _write_rows_with_spark(
            spark,
            alert_fact_rows,
            f"s3a://{bucket}/gold/fact_market_alert/",
        )
        _write_rows_with_spark(
            spark,
            obt_rows,
            f"s3a://{bucket}/gold/obt_company_quarter_risk/",
        )
        _write_rows_with_spark(
            spark,
            financial_feature_rows,
            f"s3a://{bucket}/gold/feat_company_financial_4q/",
        )
        _write_rows_with_spark(
            spark,
            market_feature_rows,
            f"s3a://{bucket}/gold/feat_company_market_30d/",
        )
        _write_rows_with_spark(
            spark,
            news_feature_rows,
            f"s3a://{bucket}/gold/feat_company_news_30d/",
        )
        _write_rows_with_spark(
            spark,
            feature_rows,
            f"s3a://{bucket}/gold/feat_company_unified/",
        )

        failed_count = failed_companies.count() + failed_statements.count() + failed_prices.count()
        return {
            "silver_companies": silver_companies.count(),
            "silver_financial_statements": silver_financial_statements.count(),
            "silver_market_prices": silver_market_prices.count(),
            "gold_dim_company": len(dim_rows),
            "gold_dim_date": len(date_rows),
            "gold_fact_financial_statement": financial_fact.count(),
            "gold_fact_market_price": market_fact.count(),
            "gold_fact_market_alert": len(alert_fact_rows),
            "gold_fact_news_sentiment": len(news_fact_rows),
            "gold_distress_labels": len(label_rows),
            "gold_obt_company_quarter_risk": len(obt_rows),
            "gold_feat_company_financial_4q": len(financial_feature_rows),
            "gold_feat_company_market_30d": len(market_feature_rows),
            "gold_feat_company_news_30d": len(news_feature_rows),
            "gold_feat_company_unified": len(feature_rows),
            "failed_records": failed_count,
        }
    finally:
        spark.stop()
