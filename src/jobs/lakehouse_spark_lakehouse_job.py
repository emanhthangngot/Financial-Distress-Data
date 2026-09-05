"""
Main platform Spark lakehouse job.

Runs the end-to-end Bronze -> Silver -> Gold pipeline for platform, including the distress labeler
and the OBT builder. Invoked by the Spark DAGs and by the local evidence script.
"""

from __future__ import annotations

import os
from typing import Any

from src.io.minio_writer import clear_minio_prefix
from src.io.paths import DEFAULT_BUCKET
from src.jobs.lakehouse_evidence_job import _ensure_bucket, _minio_client
from src.metadata.schema_registry import InMemorySchemaRegistry
from src.security.secrets import require
from src.transforms.bronze_to_silver import bronze_to_silver_spark
from src.transforms.gold.dim_company import build_dim_date
from src.transforms.gold.fact_financial_statement import build_fact_financial_statement_spark
from src.transforms.gold.fact_market_alert import build_fact_market_alert_spark
from src.transforms.gold.fact_market_price import build_fact_market_price_spark
from src.transforms.gold.fact_news_sentiment import build_fact_news_sentiment_spark

SPARK_HADOOP_AWS_PACKAGE = "org.apache.hadoop:hadoop-aws:3.3.4"
SPARK_AWS_SDK_PACKAGE = "com.amazonaws:aws-java-sdk-bundle:1.12.262"


def spark_runtime_config(minio_endpoint: str | None = None) -> dict[str, str]:
    endpoint = minio_endpoint or os.getenv("MINIO_ENDPOINT", "http://minio:9000")
    return {
        "spark.jars.packages": f"{SPARK_HADOOP_AWS_PACKAGE},{SPARK_AWS_SDK_PACKAGE}",
        "spark.hadoop.fs.s3a.endpoint": endpoint,
        "spark.hadoop.fs.s3a.access.key": require("MINIO_ROOT_USER"),
        "spark.hadoop.fs.s3a.secret.key": require("MINIO_ROOT_PASSWORD"),
        "spark.hadoop.fs.s3a.path.style.access": "true",
        "spark.hadoop.fs.s3a.connection.ssl.enabled": "false",
        "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
        "spark.sql.sources.partitionOverwriteMode": "dynamic",
    }


def _spark_session(app_name: str = "financial-distress-lakehouse-real-e2e") -> Any:
    try:
        from pyspark.sql import SparkSession
    except ImportError as exc:
        raise RuntimeError("PySpark is required for the platform real E2E Spark job.") from exc

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
    *,
    preserve_vintages: bool = False,
) -> tuple[Any, Any]:
    bronze = spark.read.parquet(f"s3a://{bucket}/bronze/{dataset}/data.parquet")
    silver, failed = bronze_to_silver_spark(
        bronze,
        required,
        nullable,
        dedup_keys,
        preserve_vintages=preserve_vintages,
    )
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

    # Single-pass per-field type inference. Priority order matches the original
    # loop: bool -> int (non-bool) -> (int|float) (non-bool) -> string. A column
    # that mixes types is coerced to StringType deterministically.
    fields: list[str] = []
    field_state: dict[str, dict[str, bool]] = {}

    def _ensure_field(name: str) -> None:
        if name not in field_state:
            fields.append(name)
            field_state[name] = {
                "saw_value": False,
                "all_bool": True,
                "all_int_non_bool": True,
                "all_numeric_non_bool": True,
            }

    for row in rows:
        for name, value in row.items():
            _ensure_field(name)
            if value is None:
                continue
            state = field_state[name]
            state["saw_value"] = True
            if not isinstance(value, bool):
                state["all_bool"] = False
            if not (isinstance(value, int) and not isinstance(value, bool)):
                state["all_int_non_bool"] = False
            if not (isinstance(value, (int, float)) and not isinstance(value, bool)):
                state["all_numeric_non_bool"] = False

    schema_fields: list[StructField] = []
    string_fields: set[str] = set()
    for field in fields:
        state = field_state[field]
        if not state["saw_value"]:
            spark_type: Any = StringType()
            string_fields.add(field)
        elif state["all_bool"]:
            spark_type = BooleanType()
        elif state["all_int_non_bool"]:
            spark_type = LongType()
        elif state["all_numeric_non_bool"]:
            spark_type = DoubleType()
        else:
            spark_type = StringType()
            string_fields.add(field)
        schema_fields.append(StructField(field, spark_type, nullable=True))

    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        normalized: dict[str, Any] = {}
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


def build_dim_company_spark(silver_companies_df: Any) -> Any:
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window

    normalized = silver_companies_df.withColumn("ticker", F.upper(F.col("ticker")))
    window_lag = Window.partitionBy("ticker").orderBy("created_ts")
    previous_created = F.lag("created_ts").over(window_lag)
    changed = previous_created.isNull()
    for field in (
        "company_name",
        "industry",
        "sector",
        "exchange",
        "listing_date",
        "delisted_flag",
    ):
        changed = changed | ~F.lag(F.col(field)).over(window_lag).eqNullSafe(F.col(field))

    filtered = normalized.withColumn("_changed", changed).filter(F.col("_changed")).drop("_changed")
    window_lead = Window.partitionBy("ticker").orderBy("created_ts")
    valid_from_ts = F.to_timestamp("created_ts")
    valid_to_ts = F.lead(valid_from_ts).over(window_lead)
    valid_from_text = F.concat(
        F.date_format(valid_from_ts, "yyyy-MM-dd'T'HH:mm:ss"),
        F.lit("+00:00"),
    )

    return (
        filtered.withColumn("valid_from_ts", valid_from_ts)
        .withColumn("valid_to_ts", valid_to_ts)
        .withColumn("is_current", F.col("valid_to_ts").isNull())
        .withColumn(
            "company_version_key",
            F.substring(
                F.sha2(
                    F.concat(
                        F.col("ticker"),
                        F.lit("|"),
                        valid_from_text,
                    ),
                    256,
                ),
                1,
                16,
            ),
        )
        .select(
            "company_version_key",
            "ticker",
            "company_name",
            "exchange",
            "industry",
            "sector",
            "listing_date",
            F.coalesce(F.col("delisted_flag").cast("boolean"), F.lit(False)).alias("delisted_flag"),
            "valid_from_ts",
            "valid_to_ts",
            "is_current",
        )
    )


def compute_labels_spark(financial_fact_df: Any) -> Any:
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window

    latest_financial = (
        financial_fact_df.filter(F.col("is_latest_vintage"))
        if "is_latest_vintage" in financial_fact_df.columns
        else financial_fact_df
    )

    window = Window.partitionBy("ticker").orderBy("report_period")
    prev_net_income = F.lag("net_income").over(window)
    prev_report_period = F.lag("report_period").over(window)

    curr_q_index = F.substring(F.col("report_period"), 1, 4).cast("int") * 4 + F.substring(
        F.col("report_period"), 6, 1
    ).cast("int")
    prev_q_index = F.substring(prev_report_period, 1, 4).cast("int") * 4 + F.substring(
        prev_report_period, 6, 1
    ).cast("int")
    consecutive = (prev_q_index.isNotNull()) & (curr_q_index - prev_q_index == 1)

    working_capital = F.col("current_assets") - F.col("current_liabilities")
    x1 = F.when(F.col("total_assets") > 0, working_capital / F.col("total_assets")).otherwise(None)
    x2 = F.when(
        F.col("total_assets") > 0, F.col("retained_earnings") / F.col("total_assets")
    ).otherwise(None)
    x3 = F.when(F.col("total_assets") > 0, F.col("ebit") / F.col("total_assets")).otherwise(None)
    x4 = F.when(F.col("total_liabilities") == 0, F.lit(99.0)).otherwise(
        F.col("equity") / F.col("total_liabilities")
    )

    z_score = F.round(6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4, 4)

    debt_to_asset = F.when(
        F.col("total_assets") > 0, F.col("total_liabilities") / F.col("total_assets")
    ).otherwise(None)
    current_ratio = F.when(
        F.col("current_liabilities") > 0, F.col("current_assets") / F.col("current_liabilities")
    ).otherwise(None)
    interest_coverage = F.when(
        F.col("interest_expense") > 0, F.col("ebit") / F.col("interest_expense")
    ).otherwise(None)

    sector_col = F.col("sector") if "sector" in latest_financial.columns else F.lit(None)
    industry_col = F.col("industry") if "industry" in latest_financial.columns else F.lit(None)
    gics_sector_col = (
        F.col("gics_sector") if "gics_sector" in latest_financial.columns else F.lit(None)
    )
    gics_industry_col = (
        F.col("gics_industry_group")
        if "gics_industry_group" in latest_financial.columns
        else F.lit(None)
    )

    financial_terms = [
        "bank",
        "banks",
        "banking",
        "insurance",
        "insurers",
        "securities",
        "brokerage",
        "diversified financials",
        "financial services",
    ]
    is_fin = F.lit(False)
    for term in financial_terms:
        is_fin = (
            is_fin
            | F.lower(F.coalesce(sector_col, F.lit(""))).contains(term)
            | F.lower(F.coalesce(industry_col, F.lit(""))).contains(term)
            | F.lower(F.coalesce(gics_sector_col, F.lit(""))).contains(term)
            | F.lower(F.coalesce(gics_industry_col, F.lit(""))).contains(term)
        )

    high_debt = F.coalesce(debt_to_asset > 0.8, F.lit(False))
    low_curr_ratio = F.coalesce(current_ratio < 1.0, F.lit(False))
    two_q_loss = F.coalesce(
        (F.col("net_income") < 0) & (prev_net_income < 0) & consecutive, F.lit(False)
    )
    neg_equity = F.coalesce(F.col("equity") < 0, F.lit(False))
    weak_coverage = F.coalesce(interest_coverage < 1.0, F.lit(False))

    warning_count = (
        high_debt.cast("int")
        + low_curr_ratio.cast("int")
        + two_q_loss.cast("int")
        + neg_equity.cast("int")
        + weak_coverage.cast("int")
    )

    distress_label = F.when(is_fin, F.lit(None).cast("int")).otherwise(
        F.when(
            z_score.isNull(),
            F.when(warning_count >= 2, F.lit(1).cast("int")).otherwise(F.lit(None).cast("int")),
        ).otherwise(
            F.when((z_score < 1.1) | (warning_count >= 2), F.lit(1).cast("int"))
            .when((z_score > 2.6) & (warning_count < 2), F.lit(0).cast("int"))
            .otherwise(F.lit(0).cast("int"))
        )
    )

    label_confidence = F.when(is_fin, F.lit(None).cast("string")).otherwise(
        F.when(
            z_score.isNull(),
            F.when(warning_count >= 2, F.lit("medium")).otherwise(F.lit(None).cast("string")),
        ).otherwise(
            F.when(
                (z_score < 1.1) | (warning_count >= 2),
                F.when(z_score < 1.1, F.lit("high")).otherwise(F.lit("medium")),
            )
            .when((z_score > 2.6) & (warning_count < 2), F.lit("high"))
            .otherwise(F.lit("low"))
        )
    )

    training_eligible = F.when(is_fin, F.lit(False)).otherwise(
        F.when(
            z_score.isNull(), F.when(warning_count >= 2, F.lit(True)).otherwise(F.lit(False))
        ).otherwise(
            F.when((z_score < 1.1) | (warning_count >= 2), F.lit(True))
            .when((z_score > 2.6) & (warning_count < 2), F.lit(True))
            .otherwise(F.lit(False))
        )
    )

    reasons = F.array(
        [
            F.when(is_fin, F.lit("financial_sector_excluded")).otherwise(F.lit(None)),
            F.when(~is_fin & high_debt, F.lit("high_debt_to_asset")).otherwise(F.lit(None)),
            F.when(~is_fin & low_curr_ratio, F.lit("low_current_ratio")).otherwise(F.lit(None)),
            F.when(~is_fin & two_q_loss, F.lit("two_quarter_net_loss")).otherwise(F.lit(None)),
            F.when(~is_fin & neg_equity, F.lit("negative_equity")).otherwise(F.lit(None)),
            F.when(~is_fin & weak_coverage, F.lit("weak_interest_coverage")).otherwise(F.lit(None)),
            F.when(
                ~is_fin & z_score.isNotNull() & (z_score < 1.1), F.lit("z_score_distress_zone")
            ).otherwise(F.lit(None)),
            F.when(
                ~is_fin & z_score.isNotNull() & (z_score > 2.6) & (warning_count < 2),
                F.lit("z_score_safe_zone"),
            ).otherwise(F.lit(None)),
            F.when(
                ~is_fin
                & z_score.isNotNull()
                & ~(z_score < 1.1)
                & ~((z_score > 2.6) & (warning_count < 2)),
                F.lit("gray_zone_monitor"),
            ).otherwise(F.lit(None)),
            F.when(
                ~is_fin & (F.col("total_liabilities") == 0) & z_score.isNotNull(),
                F.lit("zero_liabilities_x4_capped"),
            ).otherwise(F.lit(None)),
            F.when(
                ~is_fin & z_score.isNull() & (warning_count >= 2), F.lit("z_score_null")
            ).otherwise(F.lit(None)),
            F.when(
                ~is_fin & z_score.isNull() & (warning_count < 2), F.lit("insufficient_data")
            ).otherwise(F.lit(None)),
        ]
    )
    clean_reasons = F.array_compact(reasons)
    distress_reason = F.array_join(clean_reasons, ";")

    return (
        latest_financial.withColumn("z_score", z_score)
        .withColumn("distress_label", distress_label)
        .withColumn("distress_reason", distress_reason)
        .withColumn("label_source", F.lit("rule_based_v1"))
        .withColumn("label_confidence", label_confidence)
        .withColumn("training_eligible", training_eligible)
        .withColumn("rule_version", F.lit("v1"))
        .select(
            "company_version_key",
            "ticker",
            "report_period",
            "known_from_ts",
            F.col("known_from_ts").alias("decision_ts"),
            F.coalesce(F.col("event_timestamp"), F.col("report_release_date")).alias(
                "event_timestamp"
            ),
            "created_ts",
            "distress_label",
            "distress_reason",
            "z_score",
            "label_source",
            "label_confidence",
            "training_eligible",
            "rule_version",
        )
    )


def build_obt_company_quarter_risk_spark(financial_fact_df: Any, labels_df: Any) -> Any:
    from pyspark.sql import functions as F

    latest_financial = (
        financial_fact_df.filter(F.col("is_latest_vintage"))
        if "is_latest_vintage" in financial_fact_df.columns
        else financial_fact_df
    )
    joined = latest_financial.alias("fin").join(
        labels_df.alias("lbl"),
        F.col("fin.company_version_key") == F.col("lbl.company_version_key"),
        "left",
    )

    total_assets = F.col("fin.total_assets").cast("double")
    total_liabilities = F.col("fin.total_liabilities").cast("double")
    equity = F.col("fin.equity").cast("double")
    current_liabilities = F.col("fin.current_liabilities").cast("double")
    interest_expense = F.col("fin.interest_expense").cast("double")

    current_ratio = F.when(
        current_liabilities > 0, F.col("fin.current_assets").cast("double") / current_liabilities
    ).otherwise(None)
    debt_to_asset = F.when(total_assets > 0, total_liabilities / total_assets).otherwise(None)
    debt_to_equity = F.when(equity > 0, total_liabilities / equity).otherwise(None)
    roa = F.when(total_assets > 0, F.col("fin.net_income").cast("double") / total_assets).otherwise(
        None
    )
    roe = F.when(equity > 0, F.col("fin.net_income").cast("double") / equity).otherwise(None)
    ebit_interest_coverage = F.when(
        interest_expense > 0, F.col("fin.ebit").cast("double") / interest_expense
    ).otherwise(None)

    select_exprs = [F.col(f"fin.{col}").alias(col) for col in latest_financial.columns]
    select_exprs.extend(
        [
            current_ratio.alias("current_ratio"),
            debt_to_asset.alias("debt_to_asset"),
            debt_to_equity.alias("debt_to_equity"),
            roa.alias("roa"),
            roe.alias("roe"),
            ebit_interest_coverage.alias("ebit_interest_coverage"),
            F.col("lbl.distress_label").alias("distress_label"),
            F.col("lbl.distress_reason").alias("distress_reason"),
            F.col("lbl.z_score").alias("z_score"),
            F.col("lbl.label_source").alias("label_source"),
            F.col("lbl.label_confidence").alias("label_confidence"),
            F.col("lbl.training_eligible").alias("training_eligible"),
        ]
    )

    return joined.select(*select_exprs)


def build_feat_company_financial_4q_spark(obt_df: Any) -> Any:
    from pyspark.sql import functions as F

    known_from_ts = F.coalesce(
        F.col("known_from_ts"),
        F.col("report_release_date"),
        F.col("event_timestamp"),
        F.col("created_ts"),
    )
    return (
        obt_df.withColumn("ticker", F.upper(F.col("ticker")))
        .withColumn("known_from_ts", known_from_ts)
        .withColumn("event_timestamp", F.col("known_from_ts"))
        .withColumn("feature_family", F.lit("financial_4q"))
        .select(
            "ticker",
            "report_period",
            "event_timestamp",
            "known_from_ts",
            "current_ratio",
            "debt_to_asset",
            "debt_to_equity",
            "roa",
            "roe",
            "ebit_interest_coverage",
            "z_score",
            "feature_family",
        )
    )


def build_feat_company_market_30d_spark(market_fact_df: Any) -> Any:
    from pyspark.sql import functions as F

    known_from_ts = F.coalesce(
        F.col("known_from_ts"), F.col("event_timestamp"), F.col("created_ts")
    )
    return (
        market_fact_df.withColumn("ticker", F.upper(F.col("ticker")))
        .withColumn("known_from_ts", known_from_ts)
        .withColumn("event_timestamp", F.col("known_from_ts"))
        .withColumn("feature_family", F.lit("market_30d"))
        .select(
            "ticker",
            "event_timestamp",
            "known_from_ts",
            "trading_date",
            "close_price",
            "volume",
            "daily_return",
            "volatility_signal",
            "feature_family",
        )
    )


def build_feat_company_news_30d_spark(news_fact_df: Any) -> Any:
    from pyspark.sql import functions as F

    return (
        news_fact_df.withColumn("ticker", F.upper(F.col("ticker")))
        .withColumn("event_timestamp", F.col("known_from_ts"))
        .withColumn("feature_family", F.lit("news_30d"))
        .select(
            "ticker",
            "event_timestamp",
            "known_from_ts",
            "sentiment_score",
            "risk_keyword_flag",
            "severity_score",
            "feature_family",
        )
    )


def build_feat_company_unified_spark(obt_df: Any, market_df: Any) -> Any:
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window

    ref = obt_df.alias("ref")
    feat = market_df.alias("feat")

    joined = ref.join(
        feat,
        (F.col("ref.ticker") == F.col("feat.ticker"))
        & (F.col("feat.known_from_ts") <= F.col("ref.known_from_ts")),
        "left",
    )

    select_exprs = [F.col(f"ref.{col}").alias(col) for col in obt_df.columns]
    for col in market_df.columns:
        select_exprs.append(F.col(f"feat.{col}").alias(f"feature_{col}"))

    projected = joined.select(*select_exprs)

    window = Window.partitionBy("ticker", "report_period").orderBy(
        F.col("feature_event_timestamp").desc_nulls_last()
    )

    return (
        projected.withColumn("_rn", F.row_number().over(window))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )


def run_lakehouse_spark_lakehouse(
    bucket: str = DEFAULT_BUCKET, evidence_run_id: str | None = None
) -> dict[str, int]:
    _clear_output_prefixes(bucket)
    spark = _spark_session()
    registry = InMemorySchemaRegistry()
    try:
        from pyspark.sql import functions as F
        from pyspark.sql.types import (
            BooleanType,
            DoubleType,
            IntegerType,
            StringType,
            StructField,
            StructType,
        )

        companies_contract = registry.get_current("companies")
        statements_contract = registry.get_current("financial_statements")
        prices_contract = registry.get_current("market_prices_daily")

        silver_companies, failed_companies = _silver(
            spark,
            bucket,
            "companies",
            companies_contract.required,
            companies_contract.nullable,
            ["ticker", "created_ts"],
        )
        silver_financial_statements, failed_statements = _silver(
            spark,
            bucket,
            "financial_statements",
            statements_contract.required,
            statements_contract.nullable,
            ["ticker", "report_period"],
            preserve_vintages=True,
        )

        batch_prices_df = spark.read.parquet(
            f"s3a://{bucket}/bronze/market_prices_daily/data.parquet"
        )
        try:
            streaming_prices_df = spark.read.parquet(
                f"s3a://{bucket}/bronze/kafka/financial.price_events/*/*/*/*.parquet"
            )
            if evidence_run_id is not None and "evidence_run_id" in streaming_prices_df.columns:
                streaming_prices_df = streaming_prices_df.filter(
                    F.col("evidence_run_id") == evidence_run_id
                )
            aligned_stream_df = streaming_prices_df.select(
                F.col("ticker"),
                F.substring(F.col("event_timestamp"), 1, 10).alias("trading_date"),
                F.col("price").cast("double").alias("close_price"),
                F.col("volume").cast("long"),
                F.col("created_ts"),
                F.col("price").cast("double").alias("open_price"),
                F.col("price").cast("double").alias("high_price"),
                F.col("price").cast("double").alias("low_price"),
                F.lit(None).cast("double").alias("market_cap"),
                F.lit(None).cast("double").alias("shares_outstanding"),
                F.col("event_timestamp"),
            )
            cols = [
                "ticker",
                "trading_date",
                "close_price",
                "volume",
                "created_ts",
                "open_price",
                "high_price",
                "low_price",
                "market_cap",
                "shares_outstanding",
                "event_timestamp",
            ]
            bronze_prices_df = batch_prices_df.select(*cols).union(aligned_stream_df.select(*cols))
        except Exception:
            bronze_prices_df = batch_prices_df

        silver_market_prices, failed_prices = bronze_to_silver_spark(
            bronze_prices_df,
            prices_contract.required,
            prices_contract.nullable,
            ["ticker", "trading_date"],
            preserve_vintages=True,
        )
        _cast_nulltype_columns(silver_market_prices).write.mode("overwrite").parquet(
            f"s3a://{bucket}/silver/market_prices_daily/"
        )

        # 2. Dim Company (Spark-native SCD Type 2)
        dim_company_df = build_dim_company_spark(silver_companies)
        dim_company_df.write.mode("overwrite").parquet(f"s3a://{bucket}/gold/dim_company/")

        # 3. Fact Financial Statement & Fact Market Price
        financial_fact = build_fact_financial_statement_spark(
            silver_financial_statements, dim_company_df
        )
        market_fact = build_fact_market_price_spark(silver_market_prices, dim_company_df)
        financial_fact.write.mode("overwrite").parquet(
            f"s3a://{bucket}/gold/fact_financial_statement/"
        )
        market_fact.write.mode("overwrite").parquet(f"s3a://{bucket}/gold/fact_market_price/")

        # 4. News facts (Spark-native with fallback)
        try:
            news_bronze_df = spark.read.parquet(
                f"s3a://{bucket}/bronze/kafka/financial.news_events/*/*/*/*.parquet"
            )
            if evidence_run_id is not None and "evidence_run_id" in news_bronze_df.columns:
                news_bronze_df = news_bronze_df.filter(F.col("evidence_run_id") == evidence_run_id)
        except Exception:
            schema = StructType(
                [
                    StructField("event_id", StringType(), True),
                    StructField("ticker", StringType(), True),
                    StructField("event_timestamp", StringType(), True),
                    StructField("created_ts", StringType(), True),
                    StructField("sentiment_score", DoubleType(), True),
                    StructField("risk_keyword_flag", BooleanType(), True),
                    StructField("severity_score", DoubleType(), True),
                    StructField("source_url", StringType(), True),
                    StructField("known_from_ts", StringType(), True),
                    StructField("company_version_key", StringType(), True),
                    StructField("date_key", IntegerType(), True),
                ]
            )
            news_fact_df = spark.createDataFrame([], schema)
        else:
            news_fact_df = build_fact_news_sentiment_spark(news_bronze_df, dim_company_df)
        news_fact_df.write.mode("overwrite").parquet(f"s3a://{bucket}/gold/fact_news_sentiment/")

        # 5. Alert facts (Spark-native with fallback)
        try:
            alert_bronze_df = spark.read.parquet(
                f"s3a://{bucket}/bronze/kafka/financial.alert_events/*/*/*/*.parquet"
            )
            if evidence_run_id is not None and "evidence_run_id" in alert_bronze_df.columns:
                alert_bronze_df = alert_bronze_df.filter(
                    F.col("evidence_run_id") == evidence_run_id
                )
        except Exception:
            schema = StructType(
                [
                    StructField("event_id", StringType(), True),
                    StructField("ticker", StringType(), True),
                    StructField("event_timestamp", StringType(), True),
                    StructField("created_ts", StringType(), True),
                    StructField("alert_type", StringType(), True),
                    StructField("known_from_ts", StringType(), True),
                    StructField("company_version_key", StringType(), True),
                    StructField("date_key", IntegerType(), True),
                ]
            )
            alert_fact_df = spark.createDataFrame([], schema)
        else:
            alert_fact_df = build_fact_market_alert_spark(alert_bronze_df, dim_company_df)
        alert_fact_df.write.mode("overwrite").parquet(f"s3a://{bucket}/gold/fact_market_alert/")

        # 6. Distress labels (Spark-native)
        labels_df = compute_labels_spark(financial_fact)
        labels_df.write.mode("overwrite").parquet(f"s3a://{bucket}/gold/distress_labels/")

        # 7. OBT Company Quarter Risk (Spark-native)
        obt_df = build_obt_company_quarter_risk_spark(financial_fact, labels_df)
        obt_df.write.mode("overwrite").parquet(f"s3a://{bucket}/gold/obt_company_quarter_risk/")

        # 8. Feature Tables (Spark-native)
        financial_feature_df = build_feat_company_financial_4q_spark(obt_df)
        market_feature_df = build_feat_company_market_30d_spark(market_fact)
        news_feature_df = build_feat_company_news_30d_spark(news_fact_df)
        feature_df = build_feat_company_unified_spark(obt_df, market_fact)

        financial_feature_df.write.mode("overwrite").parquet(
            f"s3a://{bucket}/gold/feat_company_financial_4q/"
        )
        market_feature_df.write.mode("overwrite").parquet(
            f"s3a://{bucket}/gold/feat_company_market_30d/"
        )
        news_feature_df.write.mode("overwrite").parquet(
            f"s3a://{bucket}/gold/feat_company_news_30d/"
        )
        feature_df.write.mode("overwrite").parquet(f"s3a://{bucket}/gold/feat_company_unified/")

        # 9. Dim Date bounds
        date_bounds_df = (
            financial_fact.select(
                F.coalesce(F.col("report_release_date"), F.col("event_timestamp"))
                .cast("string")
                .alias("d")
            )
            .union(market_fact.select(F.col("trading_date").cast("string").alias("d")))
            .union(news_fact_df.select(F.col("event_timestamp").cast("string").alias("d")))
            .union(alert_fact_df.select(F.col("event_timestamp").cast("string").alias("d")))
            .select(F.min("d"), F.max("d"))
        )
        db_row = date_bounds_df.collect()[0]
        date_start, date_end = db_row[0][:10], db_row[1][:10]
        date_rows = build_dim_date(date_start, date_end)
        _write_rows_with_spark(spark, date_rows, f"s3a://{bucket}/gold/dim_date/")

        failed_count = failed_companies.count() + failed_statements.count() + failed_prices.count()
        return {
            "silver_companies": silver_companies.count(),
            "silver_financial_statements": silver_financial_statements.count(),
            "silver_market_prices": silver_market_prices.count(),
            "gold_dim_company": dim_company_df.count(),
            "gold_dim_date": len(date_rows),
            "gold_fact_financial_statement": financial_fact.count(),
            "gold_fact_market_price": market_fact.count(),
            "gold_fact_market_alert": alert_fact_df.count(),
            "gold_fact_news_sentiment": news_fact_df.count(),
            "gold_distress_labels": labels_df.count(),
            "gold_obt_company_quarter_risk": obt_df.count(),
            "gold_feat_company_financial_4q": financial_feature_df.count(),
            "gold_feat_company_market_30d": market_feature_df.count(),
            "gold_feat_company_news_30d": news_feature_df.count(),
            "gold_feat_company_unified": feature_df.count(),
            "failed_records": failed_count,
        }
    finally:
        spark.stop()
