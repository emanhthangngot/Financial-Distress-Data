from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_cluster_pipeline


def test_gold_event_timestamp_is_written_as_timezone_aware_parquet_type() -> None:
    import pyarrow.parquet as pq

    import src.io.minio_writer as minio_writer

    table = pq.read_table(
        __import__("io").BytesIO(
            minio_writer.rows_to_parquet_bytes(
                [{"ticker": "NVL", "event_timestamp": "2026-01-01T00:00:00+00:00"}]
            )
        )
    )

    assert str(table.schema.field("event_timestamp").type) == "timestamp[us, tz=UTC]"


def test_produce_gold_uses_configured_phase1_adapter_and_canonical_writer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    written: dict[str, object] = {}
    monkeypatch.setenv("PHASE1_CLUSTER_CONFIG", "configs/cluster-collector-config.yaml")
    monkeypatch.setattr(
        run_cluster_pipeline,
        "write_minio_outputs",
        lambda payload, bucket: written.update(payload=payload, bucket=bucket),
    )

    result = run_cluster_pipeline.produce_gold()

    assert result["risk_tickers"] == ["HPG", "NVL"]
    assert result["risk_rows"] == 16
    assert written["bucket"] == "financial-distress-lake"
    assert written["payload"].datasets["gold_obt_company_quarter_risk"]
    latest_nvl = [
        row
        for row in written["payload"].datasets["gold_obt_company_quarter_risk"]
        if row["ticker"] == "NVL"
    ][-1]
    assert latest_nvl["distress_label"] == 1
    assert latest_nvl["z_score"] is not None


def test_configure_s3_environment_maps_minio_without_logging_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MINIO_ENDPOINT", "minio.internal:9000")
    monkeypatch.setenv("MINIO_ROOT_USER", "access")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "secret")
    for name in (
        "AWS_ENDPOINT_URL",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_DEFAULT_REGION",
        "FEAST_REDIS_HOST",
        "FEAST_REGISTRY_PATH",
    ):
        monkeypatch.delenv(name, raising=False)

    run_cluster_pipeline.configure_s3_environment()

    assert os.environ["AWS_ENDPOINT_URL"] == "http://minio.internal:9000"
    assert os.environ["AWS_ACCESS_KEY_ID"] == "access"
    assert os.environ["AWS_SECRET_ACCESS_KEY"] == "secret"
    assert os.environ["FEAST_REDIS_HOST"] == "phase2-redis"
    assert os.environ["FEAST_REGISTRY_PATH"].startswith("s3://financial-distress-lake/")


def test_materialize_risk_features_applies_repo_materializes_and_verifies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    applied: list[object] = []
    store = SimpleNamespace(
        apply=lambda objects: applied.extend(objects),
        get_online_features=lambda **kwargs: SimpleNamespace(
            to_dict=lambda: {name: [1] for name in run_cluster_pipeline.RISK_FEATURES}
        ),
    )
    service = SimpleNamespace(
        _store=lambda: store,
        materialize_offline_to_online=lambda view, start, end: {"feature_view": view},
    )
    monkeypatch.setattr(run_cluster_pipeline, "configure_s3_environment", lambda: None)
    monkeypatch.setattr(
        "src.ml.feast.feature_definitions.build_feature_objects", lambda: {"ticker": object()}
    )
    monkeypatch.setattr(
        "src.ml.feast.materialization.FeastMaterializationService", lambda repo: service
    )

    result = run_cluster_pipeline.materialize_risk_features()

    assert len(applied) == 1
    assert result["feature_view"] == "company_risk_features"
    assert result["verified_entity"] == "NVL"


def test_cluster_image_exposes_both_runtime_commands() -> None:
    dockerfile = Path("infra/phase1-cluster/Dockerfile.pipeline").read_text(encoding="utf-8")

    assert 'ENTRYPOINT ["python", "-m", "scripts.run_cluster_pipeline"]' in dockerfile
    assert 'CMD ["produce-gold"]' in dockerfile
    assert "COPY feature_repo ./feature_repo" in dockerfile
    assert "USER 65532:65532" in dockerfile
    assert '"feast[aws,redis]==0.65.0"' in dockerfile


def test_combined_command_materializes_only_after_gold_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        run_cluster_pipeline,
        "produce_gold",
        lambda: calls.append("gold") or {"risk_rows": 16},
    )
    monkeypatch.setattr(
        run_cluster_pipeline,
        "materialize_risk_features",
        lambda: calls.append("materialize") or {"verified_entity": "NVL"},
    )

    result = run_cluster_pipeline.produce_and_materialize()

    assert calls == ["gold", "materialize"]
    assert result == {
        "gold": {"risk_rows": 16},
        "materialization": {"verified_entity": "NVL"},
    }
