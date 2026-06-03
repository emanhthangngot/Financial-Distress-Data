from __future__ import annotations

import json
from pathlib import Path

import yaml

from src.metadata.schema_registry import InMemorySchemaRegistry
from src.transforms.silver_to_gold import build_feat_company_unified


def test_compose_defines_init_services_and_host_kafka_listener():
    compose = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert {"airflow-init", "minio-init", "kafka-init"}.issubset(services)
    assert "airflow-init" in services["airflow-webserver"]["depends_on"]
    assert "minio-init" in services["airflow-webserver"]["depends_on"]
    assert "kafka-init" in services["airflow-webserver"]["depends_on"]

    kafka_environment = services["kafka"]["environment"]
    assert "PLAINTEXT_HOST://localhost:9094" in kafka_environment["KAFKA_ADVERTISED_LISTENERS"]
    assert "PLAINTEXT_HOST:PLAINTEXT" in kafka_environment["KAFKA_LISTENER_SECURITY_PROTOCOL_MAP"]
    assert "9094:9094" in services["kafka"]["ports"]


def test_market_price_schema_seed_matches_python_contract():
    sql = Path("sql/init_project_metadata.sql").read_text(encoding="utf-8")
    contract = InMemorySchemaRegistry().get_current("market_prices_daily")

    for nullable_field in contract.nullable:
        assert nullable_field in sql


def test_unified_feature_builder_excludes_future_market_rows():
    reference = {
        "ticker": "AAA",
        "report_period": "2025Q4",
        "event_timestamp": "2025-03-28",
        "report_release_date": "2025-03-28",
        "distress_label": 0,
    }
    market_facts = [
        {
            "ticker": "AAA",
            "event_timestamp": "2025-03-01",
            "trading_date": "2025-03-01",
            "close_price": 10.0,
        },
        {
            "ticker": "AAA",
            "event_timestamp": "2025-04-01",
            "trading_date": "2025-04-01",
            "close_price": 99.0,
        },
    ]

    unified = build_feat_company_unified([reference], market_facts)

    assert unified[0]["feature_close_price"] == 10.0
    assert unified[0]["feature_trading_date"] == "2025-03-01"


def test_stage1_evidence_dry_run_reports_deterministic_counts():
    from scripts.run_stage1_evidence import build_evidence_payload

    payload = build_evidence_payload()

    assert payload.row_counts["bronze_companies"] == 2
    assert payload.row_counts["silver_companies"] == 2
    assert payload.row_counts["gold_fact_financial_statement"] == 16
    assert payload.row_counts["gold_fact_market_price"] == 12
    assert payload.row_counts["gold_obt_company_quarter_risk"] == 16
    assert payload.row_counts["gold_feat_company_unified"] == 16
    assert all(path.startswith("financial-distress-lake/") for path in payload.object_keys)
    json.dumps(payload.row_counts)


def test_evidence_runner_reads_postgres_host_port_from_env_file(tmp_path, monkeypatch):
    from scripts.run_stage1_evidence import metadata_dsn

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "POSTGRES_DB=financial_distress",
                "POSTGRES_USER=airflow",
                "POSTGRES_PASSWORD=airflow",
                "POSTGRES_HOST_PORT=55432",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("PROJECT_METADATA_DSN", raising=False)
    monkeypatch.delenv("POSTGRES_HOST_PORT", raising=False)

    assert (
        metadata_dsn(env_file) == "postgresql://airflow:airflow@localhost:55432/financial_distress"
    )


def test_project_metadata_dsn_overrides_env_file(tmp_path, monkeypatch):
    from scripts.run_stage1_evidence import metadata_dsn

    env_file = tmp_path / ".env"
    env_file.write_text("POSTGRES_HOST_PORT=55432\n", encoding="utf-8")
    monkeypatch.setenv(
        "PROJECT_METADATA_DSN",
        "postgresql://custom:custom@localhost:15432/custom",
    )

    assert metadata_dsn(env_file) == "postgresql://custom:custom@localhost:15432/custom"


def test_host_minio_endpoint_ignores_docker_network_endpoint(tmp_path, monkeypatch):
    from scripts.run_stage1_evidence import minio_host_endpoint

    env_file = tmp_path / ".env"
    env_file.write_text("MINIO_ENDPOINT=http://minio:9000\n", encoding="utf-8")
    monkeypatch.delenv("MINIO_ENDPOINT", raising=False)

    assert minio_host_endpoint(env_file) == "localhost:9000"


def test_airflow_init_user_create_command_is_single_valid_command():
    compose = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
    command = compose["services"]["airflow-init"]["command"]

    assert "airflow users create --username airflow --password airflow" in command
    assert "--firstname Stage --lastname One --role Admin --email airflow@example.local" in command
