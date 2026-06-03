# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.collectors.company_list_collector import collect_companies
from src.collectors.financial_statement_collector import collect_financial_statements
from src.collectors.market_price_collector import collect_market_prices
from src.metadata.metadata_writer import (
    PostgresMetadataWriter,
    psycopg_connection_factory,
    utc_now_iso,
)
from src.metadata.schema_registry import InMemorySchemaRegistry
from src.quality.dq_checks import check_freshness, check_not_null, check_unique
from src.streaming.events import StreamEvent
from src.streaming.kafka_to_bronze_consumer import MicroBatchConsumer
from src.transforms.bronze_to_silver import bronze_to_silver
from src.transforms.silver_to_gold import (
    build_dim_company,
    build_distress_labels,
    build_fact_financial_statement,
    build_fact_market_price,
    build_feat_company_unified,
    build_obt_company_quarter_risk,
)

DEFAULT_BUCKET = "financial-distress-lake"
DEFAULT_EVIDENCE_DIR = Path("docs/evidence")
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


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


def _config_value(name: str, env_file_values: dict[str, str], default: str) -> str:
    return os.getenv(name) or env_file_values.get(name) or default


def metadata_dsn(env_path: str | Path = DEFAULT_ENV_PATH) -> str:
    if dsn := os.getenv("PROJECT_METADATA_DSN"):
        return dsn

    env_file_values = read_env_file(env_path)
    user = _config_value("POSTGRES_USER", env_file_values, "airflow")
    password = _config_value("POSTGRES_PASSWORD", env_file_values, "airflow")
    database = _config_value("POSTGRES_DB", env_file_values, "financial_distress")
    host_port = _config_value("POSTGRES_HOST_PORT", env_file_values, "5432")
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


def _with_ingest_ts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ingest_ts = utc_now_iso()
    return [{**row, "ingest_ts": ingest_ts} for row in rows]


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
    return consumer.add_event(
        StreamEvent.price_update(
            "AAA",
            "2026-01-01T09:00:02+00:00",
            "2026-01-01T09:00:03+00:00",
            10.1,
            120,
        ).as_record()
    )


def build_evidence_payload(bucket: str = DEFAULT_BUCKET) -> EvidencePayload:
    tickers = ["AAA", "BBB"]
    bronze_companies = _with_ingest_ts(collect_companies())
    bronze_financial_statements = _with_ingest_ts(
        collect_financial_statements(tickers, 2024, 2025)
    )
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
    gold_distress_labels = build_distress_labels(gold_fact_financial_statement)
    gold_obt_company_quarter_risk = build_obt_company_quarter_risk(
        gold_fact_financial_statement,
        gold_distress_labels,
        gold_fact_market_price,
    )
    gold_feat_company_unified = build_feat_company_unified(
        gold_obt_company_quarter_risk,
        gold_fact_market_price,
    )

    datasets = {
        "bronze_companies": bronze_companies,
        "bronze_financial_statements": bronze_financial_statements,
        "bronze_market_prices": bronze_market_prices,
        "silver_companies": silver_companies,
        "silver_financial_statements": silver_financial_statements,
        "silver_market_prices": silver_market_prices,
        "gold_dim_company": gold_dim_company,
        "gold_fact_financial_statement": gold_fact_financial_statement,
        "gold_fact_market_price": gold_fact_market_price,
        "gold_distress_labels": gold_distress_labels,
        "gold_obt_company_quarter_risk": gold_obt_company_quarter_risk,
        "gold_feat_company_unified": gold_feat_company_unified,
        "failed_records": [
            *failed_companies,
            *failed_financial_statements,
            *failed_market_prices,
        ],
    }
    object_keys = [
        f"{bucket}/bronze/companies/data.parquet",
        f"{bucket}/bronze/financial_statements/data.parquet",
        f"{bucket}/bronze/market_prices_daily/data.parquet",
        f"{bucket}/silver/companies/data.parquet",
        f"{bucket}/silver/financial_statements/data.parquet",
        f"{bucket}/silver/market_prices_daily/data.parquet",
        f"{bucket}/gold/dim_company/data.parquet",
        f"{bucket}/gold/fact_financial_statement/data.parquet",
        f"{bucket}/gold/fact_market_price/data.parquet",
        f"{bucket}/gold/distress_labels/data.parquet",
        f"{bucket}/gold/obt_company_quarter_risk/data.parquet",
        f"{bucket}/gold/feat_company_unified/data.parquet",
    ]
    return EvidencePayload(
        datasets=datasets,
        object_keys=object_keys,
        row_counts={name: len(rows) for name, rows in datasets.items()},
        stream_batches=_stream_batches(),
    )


def _field_names(rows: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    return names


def _arrow_type(values: list[Any]) -> Any:
    import pyarrow as pa

    non_null = [value for value in values if value is not None]
    if not non_null:
        return pa.string()
    if all(isinstance(value, bool) for value in non_null):
        return pa.bool_()
    if all(isinstance(value, int) and not isinstance(value, bool) for value in non_null):
        return pa.int64()
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in non_null):
        return pa.float64()
    return pa.string()


def _to_parquet_bytes(rows: list[dict[str, Any]]) -> bytes:
    import pyarrow as pa
    import pyarrow.parquet as pq

    fields = _field_names(rows)
    arrays = []
    for field in fields:
        values = [row.get(field) for row in rows]
        arrow_type = _arrow_type(values)
        if pa.types.is_string(arrow_type):
            values = [None if value is None else str(value) for value in values]
        arrays.append(pa.array(values, type=arrow_type))

    table = pa.Table.from_arrays(arrays, names=fields)
    output = io.BytesIO()
    pq.write_table(table, output)
    return output.getvalue()


def _write_minio_dataset(
    client: Any,
    bucket: str,
    bucket_and_key: str,
    rows: list[dict[str, Any]],
) -> None:
    object_key = bucket_and_key.removeprefix(f"{bucket}/")
    data = _to_parquet_bytes(rows)
    client.put_object(
        bucket,
        object_key,
        io.BytesIO(data),
        len(data),
        content_type="application/octet-stream",
    )


def write_minio_outputs(payload: EvidencePayload, bucket: str) -> None:
    try:
        from minio import Minio
    except ImportError as exc:
        raise RuntimeError(
            "Install runtime dependencies with .venv/bin/python -m pip install -e '.[runtime]'."
        ) from exc

    endpoint = minio_host_endpoint()
    client = Minio(
        endpoint,
        access_key=os.getenv("MINIO_ROOT_USER", "minioadmin"),
        secret_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
        secure=False,
    )
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)

    dataset_names = [name for name in payload.datasets if name != "failed_records"]
    dataset_by_key = dict(
        zip(
            payload.object_keys,
            [payload.datasets[name] for name in dataset_names],
            strict=True,
        )
    )
    for object_key, rows in dataset_by_key.items():
        _write_minio_dataset(client, bucket, object_key, rows)


def write_postgres_metadata(payload: EvidencePayload) -> None:
    writer = PostgresMetadataWriter(psycopg_connection_factory(metadata_dsn()))
    run_id = writer.log_run(
        "stage1_runtime_evidence",
        "materialize_fixture_lakehouse",
        "stage1_evidence",
        "success",
        output_rows=sum(payload.row_counts.values()),
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


def write_evidence_files(payload: EvidencePayload, evidence_dir: Path) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "stage1_row_counts.json").write_text(
        json.dumps(payload.row_counts, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (evidence_dir / "stage1_minio_objects.txt").write_text(
        "\n".join(payload.object_keys) + "\n",
        encoding="utf-8",
    )
    (evidence_dir / "stage1_stream_batches.json").write_text(
        json.dumps(payload.stream_batches, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _validation_statements() -> list[str]:
    sql = Path("sql/duckdb_validation_queries.sql").read_text(encoding="utf-8")
    return [statement.strip() for statement in sql.split(";") if statement.strip()]


def write_duckdb_validation(evidence_dir: Path) -> None:
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError(
            "DuckDB validation requires runtime dependencies: "
            ".venv/bin/python -m pip install -e '.[runtime]'."
        ) from exc

    connection = duckdb.connect(":memory:")
    try:
        connection.execute(Path("sql/duckdb_create_views.sql").read_text(encoding="utf-8"))
        outputs = []
        for statement in _validation_statements():
            result = connection.execute(statement)
            outputs.append(
                {
                    "query": statement,
                    "columns": [column[0] for column in result.description or []],
                    "rows": result.fetchall(),
                }
            )
    finally:
        connection.close()

    (evidence_dir / "stage1_duckdb_validation.json").write_text(
        json.dumps(outputs, indent=2, default=str),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize Stage 1 runtime evidence.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build payload and local evidence files only.",
    )
    parser.add_argument("--bucket", default=os.getenv("FINANCIAL_DISTRESS_BUCKET", DEFAULT_BUCKET))
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_evidence_payload(args.bucket)
    write_evidence_files(payload, Path(args.evidence_dir))
    if not args.dry_run:
        write_minio_outputs(payload, args.bucket)
        write_postgres_metadata(payload)
        write_duckdb_validation(Path(args.evidence_dir))
    print(json.dumps(payload.row_counts, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
