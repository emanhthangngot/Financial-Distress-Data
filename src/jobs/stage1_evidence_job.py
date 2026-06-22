from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.catalog.duckdb_runner import run_duckdb_validation
from src.collectors.company_list_collector import collect_companies
from src.collectors.financial_statement_collector import collect_financial_statements
from src.collectors.market_price_collector import collect_market_prices
from src.collectors.source_adapters.vnstock_fixture_adapter import VnstockFixtureAdapter
from src.generators.config_loader import load_generator_config
from src.generators.streaming_problem_factory import (
    inject_streaming_duplicates,
    plan_burst,
    plan_late_arrivals,
)
from src.io.minio_writer import write_minio_dataset, write_minio_text
from src.io.paths import DEFAULT_BUCKET, stage1_dataset_object_keys
from src.metadata.metadata_writer import (
    PostgresMetadataWriter,
    psycopg_connection_factory,
    utc_now_iso,
)
from src.metadata.schema_registry import InMemorySchemaRegistry
from src.quality.dq_checks import check_freshness, check_not_null, check_unique
from src.security.secrets import require
from src.streaming.events import StreamEvent
from src.streaming.kafka_to_bronze_consumer import MicroBatchConsumer
from src.transforms.bronze_to_silver import bronze_to_silver
from src.transforms.silver_to_gold import (
    build_dim_company,
    build_dim_date,
    build_distress_labels,
    build_fact_financial_statement,
    build_fact_market_alert,
    build_fact_market_price,
    build_fact_news_sentiment,
    build_feat_company_financial_4q,
    build_feat_company_market_30d,
    build_feat_company_news_30d,
    build_feat_company_unified,
    build_obt_company_quarter_risk,
)

DEFAULT_EVIDENCE_DIR = Path("docs/evidence")
DEFAULT_ENV_PATH = Path(".env")
DEFAULT_EVIDENCE_PREFIX = "evidence/stage1"


@dataclass(frozen=True)
class EvidencePayload:
    datasets: dict[str, list[dict[str, Any]]]
    object_keys: list[str]
    row_counts: dict[str, int]
    stream_batches: list[dict[str, Any]]


def read_env_file(path: str | Path = DEFAULT_ENV_PATH) -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _config_value(name: str, env_file_values: dict[str, str]) -> str:
    value = os.getenv(name)
    if value:
        return value
    candidate = env_file_values.get(name)
    if candidate:
        return candidate
    raise RuntimeError(f"Required env var {name!r} is missing. Add it to .env or export it.")


def metadata_dsn(env_path: str | Path = DEFAULT_ENV_PATH) -> str:
    if dsn := os.getenv("PROJECT_METADATA_DSN"):
        return dsn

    env_file_values = read_env_file(env_path)
    user = _config_value("POSTGRES_USER", env_file_values)
    password = _config_value("POSTGRES_PASSWORD", env_file_values)
    database = _config_value("POSTGRES_DB", env_file_values)
    host_port = _config_value("POSTGRES_HOST_PORT", env_file_values)
    return f"postgresql://{user}:{password}@localhost:{host_port}/{database}"


def minio_host_endpoint(env_path: str | Path = DEFAULT_ENV_PATH) -> str:
    endpoint = os.getenv("MINIO_ENDPOINT")
    if endpoint:
        return endpoint.removeprefix("http://").removeprefix("https://")

    env_file_values = read_env_file(env_path)
    endpoint = env_file_values.get("MINIO_ENDPOINT", "localhost:9000")
    endpoint = endpoint.removeprefix("http://").removeprefix("https://")
    if endpoint.startswith("minio:"):
        return endpoint.replace("minio:", "localhost:", 1)
    return endpoint


def current_evidence_run_id() -> str:
    run_id = os.getenv("STAGE1_EVIDENCE_RUN_ID") or os.getenv("AIRFLOW_CTX_DAG_RUN_ID")
    if not run_id:
        run_id = utc_now_iso()
    return _sanitize_evidence_run_id(run_id)


def _sanitize_evidence_run_id(run_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.=\-]+", "_", run_id)


def evidence_prefix(run_id: str | None = None) -> str:
    safe_run_id = _sanitize_evidence_run_id(run_id) if run_id else current_evidence_run_id()
    return f"{DEFAULT_EVIDENCE_PREFIX}/run_id={safe_run_id}"


def _with_ingest_ts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ingest_ts = utc_now_iso()
    return [{**row, "ingest_ts": ingest_ts} for row in rows]


def _date_key_to_iso(value: int) -> str:
    text = str(value)
    return f"{text[:4]}-{text[4:6]}-{text[6:8]}"


def _silver_dataset(
    rows: list[dict[str, Any]], dataset_name: str, dedup_keys: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    contract = InMemorySchemaRegistry().get_current(dataset_name)
    return bronze_to_silver(rows, contract.required, contract.nullable, dedup_keys)


def _stream_batches() -> list[dict[str, Any]]:
    consumer = MicroBatchConsumer(flush_record_count=2)
    consumer.add_event(
        StreamEvent.price_update(
            "AAA",
            "2026-01-01T09:00:00+00:00",
            "2026-01-01T09:00:01+00:00",
            10.0,
            100,
        ).as_record()
    )
    batches = consumer.add_event(
        StreamEvent.price_update(
            "AAA",
            "2026-01-01T09:00:02+00:00",
            "2026-01-01T09:00:03+00:00",
            10.1,
            120,
        ).as_record()
    )
    consumer.add_event(
        StreamEvent.news_sentiment(
            "AAA",
            "2026-01-01T09:00:06+00:00",
            "2026-01-01T09:00:07+00:00",
            -0.2,
            True,
            0.5,
        ).as_record()
    )
    batches.extend(
        consumer.add_event(
            StreamEvent.alert(
                "BBB",
                "2026-01-01T09:00:10+00:00",
                "2026-01-01T09:00:11+00:00",
                "price_drop",
            ).as_record()
        )
    )
    batches.extend(consumer.flush())
    return batches


def _coerce_tickers(tickers: list[str]) -> list[str]:
    """Drop unknown tickers so the configured adapter never sees the legacy ones."""
    return [t for t in tickers if t]


def build_generator_characteristics() -> dict[str, Any]:
    """Materialise a summary table that maps to the rubric's data generator lines.

    Returns a JSON-serialisable dict with six sections:

    * ``skew`` - top ticker share and per-ticker counts in the company rows.
    * ``cardinality`` - distinct ticker/industry/sector counts.
    * ``evolution`` - number of legacy-NULL cells in the financial statement rows.
    * ``duplication`` - duplicate count before and after the silver dedup step.
    * ``streaming`` - counts of burst, late-arrival, and duplicate events.
    * ``volume`` - bronze row counts and the storage format.
    """
    cfg = load_generator_config()
    adapter = VnstockFixtureAdapter(config=cfg) if cfg.enabled else VnstockFixtureAdapter()

    companies = adapter.fetch_companies()
    tickers = [c["ticker"] for c in companies]
    ticker_counts: dict[str, int] = {}
    for t in tickers:
        ticker_counts[t] = ticker_counts.get(t, 0) + 1
    top_ticker = cfg.skew.top_company_ticker if cfg.enabled else "AAA"
    top_count = ticker_counts.get(top_ticker, 0)
    top_share = (top_count / len(tickers)) if tickers else 0.0

    sample_tickers = _coerce_tickers(tickers) or ["AAA"]
    financial_rows: list[dict[str, Any]] = []
    for t in sample_tickers:
        financial_rows.extend(adapter.fetch_financial_statements(t, 2024, 2025))

    base_count = sum(1 for r in financial_rows if r.get("_is_duplicate") is not True)
    dup_count = sum(1 for r in financial_rows if r.get("_is_duplicate") is True)
    legacy_null_columns = cfg.evolution.legacy_null_columns if cfg.enabled else ()
    legacy_null_count = sum(
        1 for r in financial_rows for col in legacy_null_columns if r.get(col) is None
    )

    # After dedup: keep the business-key uniqueness that silver would apply.
    seen: set[tuple[Any, ...]] = set()
    after_dedup = 0
    for r in financial_rows:
        key = (r.get("ticker"), r.get("report_period"))
        if key in seen:
            continue
        seen.add(key)
        after_dedup += 1

    # Streaming: derive a representative sample using the same base events that
    # the smoke pipeline uses for the news_sentiment + alert factories.
    base_stream_events: list[StreamEvent] = [
        StreamEvent.price_update(
            "AAA",
            "2026-01-01T09:00:00+00:00",
            "2026-01-01T09:00:00+00:00",
            10.0,
            100,
        ),
        StreamEvent.price_update(
            "BBB",
            "2026-01-01T09:00:01+00:00",
            "2026-01-01T09:00:01+00:00",
            10.1,
            120,
        ),
    ]
    burst_events = (
        plan_burst(
            base_stream_events,
            window_seconds=cfg.streaming.burst.window_seconds,
            record_count=cfg.streaming.burst.record_count,
        )
        if cfg.enabled
        else []
    )
    late_events = (
        plan_late_arrivals(
            base_stream_events,
            max_lag_seconds=cfg.streaming.late_arrival.max_lag_seconds,
        )
        if cfg.enabled
        else []
    )
    dup_input = list(base_stream_events) + burst_events + late_events
    dup_events = (
        inject_streaming_duplicates(dup_input, rate=cfg.duplication.streaming_rate)
        if cfg.enabled
        else []
    )

    market_rows: list[dict[str, Any]] = []
    for t in sample_tickers:
        market_rows.extend(adapter.fetch_market_prices(t, 2024, 2025))

    return {
        "skew": {
            "top_ticker": top_ticker,
            "top_share": top_share,
            "ticker_counts": ticker_counts,
        },
        "cardinality": {
            "distinct_tickers": len(set(tickers)),
            "distinct_industries": len({c["industry"] for c in companies}),
            "distinct_sectors": len({c["sector"] for c in companies}),
        },
        "evolution": {
            "legacy_partition_cutoff": (
                cfg.evolution.legacy_partition_cutoff if cfg.enabled else None
            ),
            "legacy_null_columns": list(legacy_null_columns),
            "legacy_null_count": legacy_null_count,
        },
        "duplication": {
            "offline_rate": cfg.duplication.offline_rate if cfg.enabled else 0.0,
            "offline_base_count": base_count,
            "offline_count": dup_count,
            "after_dedup": after_dedup,
        },
        "streaming": {
            "burst_count": len(burst_events),
            "late_count": len(late_events),
            "duplicate_count": len(dup_events) - len(dup_input),
        },
        "volume": {
            "format": "parquet",
            "row_counts": {
                "bronze_companies": len(companies),
                "bronze_financial_statements": len(financial_rows),
                "bronze_market_prices": len(market_rows),
            },
        },
    }


def write_generator_characteristics_evidence(
    evidence_dir: str | Path,
    payload: dict[str, Any] | None = None,
) -> Path:
    """Persist the characteristics dict to ``stage1_generator_characteristics.json``."""
    output_dir = Path(evidence_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "stage1_generator_characteristics.json"
    out_path.write_text(
        json.dumps(
            payload if payload is not None else build_generator_characteristics(),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return out_path


def build_evidence_payload(bucket: str = DEFAULT_BUCKET) -> EvidencePayload:
    tickers = ["AAA", "BBB"]
    bronze_companies = _with_ingest_ts(collect_companies())
    bronze_financial_statements = _with_ingest_ts(collect_financial_statements(tickers, 2024, 2025))
    bronze_market_prices = _with_ingest_ts(collect_market_prices(tickers, 2024, 2025))

    silver_companies, failed_companies = _silver_dataset(bronze_companies, "companies", ["ticker"])
    silver_financial_statements, failed_financial_statements = _silver_dataset(
        bronze_financial_statements,
        "financial_statements",
        ["ticker", "report_period"],
    )
    silver_market_prices, failed_market_prices = _silver_dataset(
        bronze_market_prices,
        "market_prices_daily",
        ["ticker", "trading_date"],
    )

    gold_dim_company = build_dim_company(silver_companies)
    gold_fact_financial_statement = build_fact_financial_statement(silver_financial_statements)
    gold_fact_market_price = build_fact_market_price(silver_market_prices)
    gold_fact_news_sentiment = build_fact_news_sentiment(
        [
            StreamEvent.news_sentiment(
                "AAA",
                "2026-01-01T09:00:06+00:00",
                "2026-01-01T09:00:07+00:00",
                -0.2,
                True,
                0.5,
                "https://example.local/news/aaa-risk",
            ).as_record(),
            StreamEvent.news_sentiment(
                "BBB",
                "2026-01-01T09:00:08+00:00",
                "2026-01-01T09:00:09+00:00",
                -0.7,
                True,
                0.9,
                "https://example.local/news/bbb-distress",
            ).as_record(),
        ]
    )
    gold_fact_market_alert = build_fact_market_alert(
        [
            StreamEvent.alert(
                "BBB",
                "2026-01-01T09:00:10+00:00",
                "2026-01-01T09:00:11+00:00",
                "price_drop",
            ).as_record()
        ]
    )
    gold_distress_labels = build_distress_labels(gold_fact_financial_statement)
    gold_obt_company_quarter_risk = build_obt_company_quarter_risk(
        gold_fact_financial_statement,
        gold_distress_labels,
        gold_fact_market_price,
    )
    gold_feat_company_financial_4q = build_feat_company_financial_4q(gold_obt_company_quarter_risk)
    gold_feat_company_market_30d = build_feat_company_market_30d(gold_fact_market_price)
    gold_feat_company_news_30d = build_feat_company_news_30d(gold_fact_news_sentiment)
    gold_feat_company_unified = build_feat_company_unified(
        gold_obt_company_quarter_risk,
        gold_fact_market_price,
    )
    date_values = [
        *(row["date_key"] for row in gold_fact_financial_statement),
        *(row["date_key"] for row in gold_fact_market_price),
        *(row["date_key"] for row in gold_fact_news_sentiment),
        *(row["date_key"] for row in gold_fact_market_alert),
    ]
    gold_dim_date = build_dim_date(
        _date_key_to_iso(min(date_values)),
        _date_key_to_iso(max(date_values)),
    )

    datasets = {
        "bronze_companies": bronze_companies,
        "bronze_financial_statements": bronze_financial_statements,
        "bronze_market_prices": bronze_market_prices,
        "silver_companies": silver_companies,
        "silver_financial_statements": silver_financial_statements,
        "silver_market_prices": silver_market_prices,
        "gold_dim_company": gold_dim_company,
        "gold_dim_date": gold_dim_date,
        "gold_fact_financial_statement": gold_fact_financial_statement,
        "gold_fact_market_price": gold_fact_market_price,
        "gold_fact_market_alert": gold_fact_market_alert,
        "gold_fact_news_sentiment": gold_fact_news_sentiment,
        "gold_distress_labels": gold_distress_labels,
        "gold_obt_company_quarter_risk": gold_obt_company_quarter_risk,
        "gold_feat_company_financial_4q": gold_feat_company_financial_4q,
        "gold_feat_company_market_30d": gold_feat_company_market_30d,
        "gold_feat_company_news_30d": gold_feat_company_news_30d,
        "gold_feat_company_unified": gold_feat_company_unified,
        "failed_records": [
            *failed_companies,
            *failed_financial_statements,
            *failed_market_prices,
        ],
    }
    return EvidencePayload(
        datasets=datasets,
        object_keys=stage1_dataset_object_keys(bucket),
        row_counts={name: len(rows) for name, rows in datasets.items()},
        stream_batches=_stream_batches(),
    )


def write_evidence_files(payload: EvidencePayload, evidence_dir: str | Path) -> None:
    output_dir = Path(evidence_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "stage1_row_counts.json").write_text(
        json.dumps(payload.row_counts, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "stage1_minio_objects.txt").write_text(
        "\n".join(payload.object_keys) + "\n",
        encoding="utf-8",
    )
    (output_dir / "stage1_stream_batches.json").write_text(
        json.dumps(payload.stream_batches, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _minio_client() -> Any:
    try:
        from minio import Minio
    except ImportError as exc:
        raise RuntimeError(
            "Install runtime dependencies with .venv/bin/python -m pip install -e '.[runtime]'."
        ) from exc

    return Minio(
        minio_host_endpoint(),
        access_key=require("MINIO_ROOT_USER"),
        secret_key=require("MINIO_ROOT_PASSWORD"),
        secure=False,
    )


def _ensure_bucket(client: Any, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def write_minio_outputs(payload: EvidencePayload, bucket: str) -> None:
    client = _minio_client()
    _ensure_bucket(client, bucket)

    dataset_names = [name for name in payload.datasets if name != "failed_records"]
    dataset_by_key = dict(
        zip(
            payload.object_keys,
            [payload.datasets[name] for name in dataset_names],
            strict=True,
        )
    )
    for object_key, rows in dataset_by_key.items():
        write_minio_dataset(client, bucket, object_key, rows)


def build_evidence_artifacts(
    payload: EvidencePayload,
    duckdb_validation: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    artifacts = {
        "stage1_row_counts.json": json.dumps(payload.row_counts, indent=2, sort_keys=True),
        "stage1_minio_objects.txt": "\n".join(payload.object_keys) + "\n",
        "stage1_stream_batches.json": json.dumps(
            payload.stream_batches,
            indent=2,
            sort_keys=True,
        ),
    }
    if duckdb_validation is not None:
        artifacts["stage1_duckdb_validation.json"] = json.dumps(
            duckdb_validation,
            indent=2,
            default=str,
        )
    return artifacts


def write_minio_evidence_artifacts(
    payload: EvidencePayload,
    bucket: str,
    run_id: str | None = None,
    duckdb_validation: list[dict[str, Any]] | None = None,
) -> str:
    client = _minio_client()
    _ensure_bucket(client, bucket)
    prefix = evidence_prefix(run_id)
    for filename, text in build_evidence_artifacts(payload, duckdb_validation).items():
        content_type = "application/json" if filename.endswith(".json") else "text/plain"
        write_minio_text(client, bucket, f"{prefix}/{filename}", text, content_type)
    return f"s3://{bucket}/{prefix}/"


def write_postgres_metadata(
    payload: EvidencePayload,
    dag_id: str = "stage1_runtime_evidence",
    task_id: str = "materialize_fixture_lakehouse",
    dataset_name: str = "stage1_evidence",
) -> str:
    writer = PostgresMetadataWriter(psycopg_connection_factory(metadata_dsn()))
    run_id = writer.log_run(
        dag_id,
        task_id,
        dataset_name,
        "success",
        output_rows=sum(payload.row_counts.values()),
    )
    writer.log_backfill_request(
        "stage1_lakehouse",
        "2024-01-01",
        "2026-01-01",
        "completed",
        dag_id,
        run_id=run_id,
    )
    writer.log_source_request(
        run_id=run_id,
        source_system="vnstock_fixture",
        source_endpoint="fixture://stage1",
        ticker=None,
        report_period=None,
        request_status="success",
        retry_count=0,
        raw_payload_hash=None,
    )
    writer.upsert_collector_checkpoint(
        collector_name="stage1_fixture_collectors",
        source_system="vnstock_fixture",
        checkpoint_key="last_successful_run_id",
        checkpoint_value=run_id,
    )

    for dataset_name in ("silver_companies", "gold_fact_financial_statement"):
        result = check_unique(payload.datasets[dataset_name], dataset_name, ["ticker"])
        if dataset_name == "gold_fact_financial_statement":
            result = check_not_null(payload.datasets[dataset_name], dataset_name, "company_key")
        writer.log_dq_result(
            result.dataset_name,
            result.check_name,
            result.status,
            result.severity,
            result.metric_value,
            result.threshold_value,
            result.error_message,
            run_id,
        )

    freshness = check_freshness(
        payload.datasets["silver_market_prices"],
        "silver_market_prices",
        "2025-03-01T00:00:00+00:00",
        120,
        timestamp_field="event_timestamp",
    )
    writer.log_dq_result(
        freshness.dataset_name,
        freshness.check_name,
        freshness.status,
        freshness.severity,
        freshness.metric_value,
        freshness.threshold_value,
        freshness.error_message,
        run_id,
    )
    writer.update_dataset_freshness(
        "silver_market_prices",
        "2025-03-01T00:00:00+00:00",
        utc_now_iso(),
        freshness.metric_value or 0,
        freshness.threshold_value or 120,
        freshness.status,
    )
    return run_id


def materialize_stage1_evidence(
    bucket: str = DEFAULT_BUCKET,
    evidence_dir: str | Path = DEFAULT_EVIDENCE_DIR,
    dry_run: bool = False,
) -> EvidencePayload:
    payload = build_evidence_payload(bucket)
    write_evidence_files(payload, evidence_dir)
    if not dry_run:
        write_minio_outputs(payload, bucket)
        write_postgres_metadata(payload)
        duckdb_validation = run_duckdb_validation(evidence_dir)
        write_minio_evidence_artifacts(payload, bucket, duckdb_validation=duckdb_validation)
    return payload
