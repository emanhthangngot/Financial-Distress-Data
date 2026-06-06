# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.catalog.duckdb_runner import run_duckdb_validation


def run(command: list[str], timeout: int = 120) -> str:
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.stdout.strip()


def kafka_offsets() -> dict[str, list[str]]:
    topics = ["financial.price_events", "financial.news_events", "financial.alert_events"]
    output: dict[str, list[str]] = {}
    for topic in topics:
        text = run(
            [
                "docker",
                "exec",
                "financial-distress-data-kafka-1",
                "/opt/kafka/bin/kafka-get-offsets.sh",
                "--bootstrap-server",
                "kafka:9092",
                "--topic",
                topic,
            ]
        )
        output[topic] = [line for line in text.splitlines() if line]
    return output


def minio_objects() -> list[dict[str, int | str]]:
    from minio import Minio

    client = Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False,
    )
    return [
        {"object_name": item.object_name, "size": item.size or 0}
        for item in client.list_objects("financial-distress-lake", recursive=True)
    ]


def postgres_summary() -> dict[str, str]:
    queries = {
        "pipeline_run_log": (
            "SELECT dag_id, task_id, dataset_name, status, count(*) "
            "FROM project_metadata.pipeline_run_log GROUP BY 1,2,3,4 ORDER BY 1,2;"
        ),
        "data_quality_result": (
            "SELECT dataset_name, check_name, status, severity, count(*) "
            "FROM project_metadata.data_quality_result GROUP BY 1,2,3,4 ORDER BY 1,2;"
        ),
        "dataset_freshness": (
            "SELECT dataset_name, status, freshness_lag_minutes, sla_minutes "
            "FROM project_metadata.dataset_freshness ORDER BY dataset_name;"
        ),
        "failed_records": (
            "SELECT dataset_name, failure_reason, count(*) "
            "FROM project_metadata.failed_records GROUP BY 1,2 ORDER BY 1,2;"
        ),
        "backfill_request": (
            "SELECT dataset_name, start_date, end_date, status, requested_by, count(*) "
            "FROM project_metadata.backfill_request GROUP BY 1,2,3,4,5 ORDER BY 1,2,3,4,5;"
        ),
        "source_request_log": (
            "SELECT source_system, source_endpoint, request_status, count(*) "
            "FROM project_metadata.source_request_log GROUP BY 1,2,3 ORDER BY 1,2,3;"
        ),
        "collector_checkpoint": (
            "SELECT collector_name, source_system, checkpoint_key, count(*) "
            "FROM project_metadata.collector_checkpoint GROUP BY 1,2,3 ORDER BY 1,2,3;"
        ),
    }
    return {
        name: run(
            [
                "docker",
                "exec",
                "financial-distress-data-postgres-1",
                "psql",
                "-U",
                "airflow",
                "-d",
                "financial_distress",
                "-c",
                query,
            ]
        )
        for name, query in queries.items()
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run and verify the Stage 1 real local E2E DAG.")
    parser.add_argument(
        "--start", action="store_true", help="Build and start docker compose first."
    )
    parser.add_argument("--execution-date", default="2026-06-06T03:00:00+00:00")
    parser.add_argument("--export-evidence", default="docs/evidence")
    args = parser.parse_args()

    if args.start:
        run(["docker", "compose", "up", "-d", "--build"], timeout=600)

    dag_output = run(
        [
            "docker",
            "exec",
            "financial-distress-data-airflow-webserver-1",
            "airflow",
            "dags",
            "test",
            "stage1_real_e2e_pipeline",
            args.execution_date,
        ],
        timeout=900,
    )
    evidence_dir = PROJECT_ROOT / args.export_evidence
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "stage1_real_airflow_dag_test.txt").write_text(dag_output, encoding="utf-8")
    write_json(evidence_dir / "stage1_real_kafka_offsets.json", kafka_offsets())
    write_json(evidence_dir / "stage1_real_minio_objects.json", minio_objects())
    write_json(evidence_dir / "stage1_real_postgres_summary.json", postgres_summary())
    write_json(
        evidence_dir / "stage1_real_duckdb_validation.json", run_duckdb_validation(evidence_dir)
    )
    print(f"Exported Stage 1 real E2E evidence to {evidence_dir}")


if __name__ == "__main__":
    main()
