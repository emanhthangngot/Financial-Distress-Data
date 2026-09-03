"""Pins src/governance/lineage.py: configs/platform-governance.yaml
loads and validates, audit works with no live DataHub server, and
emit_lineage rejects an unknown pipeline name before ever attempting
the lazy `datahub` import (module is not a `.venv`/`.venv-platform` dependency
at all)."""

from __future__ import annotations

import sys

import pytest

from src.governance.lineage import (
    audit_lineage,
    emit_lineage,
    emit_lineage_if_configured,
    load_platform_governance_model,
)


def test_config_loads_and_validates() -> None:
    model = load_platform_governance_model()
    model.validate()
    assert set(model.pipelines) == {
        "phase2_rag_ingest",
        "phase2_label_drift_build",
        "phase2_feature_materialize",
        "phase2_stream_feature_offline",
        "phase2_stream_feature_online",
    }


def test_audit_does_not_import_datahub(monkeypatch: pytest.MonkeyPatch) -> None:
    """A phantom-proof version of "doesn't import datahub": makes importing
    it raise, so the assertion only passes if audit_lineage's call
    path genuinely never reaches an ``import datahub`` — not just because
    the package happens to be absent from this venv."""
    import builtins

    real_import = builtins.__import__

    def _blocking_import(name, *args, **kwargs):
        if name == "datahub" or name.startswith("datahub."):
            raise AssertionError("audit_lineage must never import datahub")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocking_import)
    report = audit_lineage()
    assert report["status"] == "pass"


def test_audit_reports_every_pipeline_as_a_contract() -> None:
    report = audit_lineage()
    assert set(report["contracts"]) == {
        "phase2_rag_ingest",
        "phase2_label_drift_build",
        "phase2_feature_materialize",
        "phase2_stream_feature_offline",
        "phase2_stream_feature_online",
    }


def test_rag_ingest_contract_dataset_is_rag_chunk() -> None:
    report = audit_lineage()
    assert report["contracts"]["phase2_rag_ingest"]["dataset"] == "ml.rag_chunk"


def test_emit_rejects_unknown_pipeline_before_importing_datahub() -> None:
    with pytest.raises(KeyError, match="unknown platform pipeline"):
        emit_lineage("run-1", "not_a_real_pipeline", server="http://localhost:8080")
    assert "datahub" not in sys.modules


def test_audit_narrowed_to_one_pipeline_reports_only_that_pipeline() -> None:
    report = audit_lineage(pipeline_name="phase2_rag_ingest")
    assert set(report["contracts"]) == {"phase2_rag_ingest"}


def test_audit_narrowed_pipeline_only_carries_its_own_datasets() -> None:
    model = load_platform_governance_model()
    full_dataset_count = len(model.datasets)
    report = audit_lineage(pipeline_name="phase2_rag_ingest")
    # phase2_rag_ingest touches 4 datasets (1 input + 3 outputs); the full
    # registry has more than that — narrowing must have actually happened,
    # not just filtered the report's pipeline list.
    assert report["dataset_count"] < full_dataset_count
    assert report["dataset_count"] == 4


def test_audit_rejects_unknown_pipeline_name() -> None:
    with pytest.raises(KeyError, match="unknown platform pipeline"):
        audit_lineage(pipeline_name="not_a_real_pipeline")


# --- emit_lineage_if_configured (wired into every real task entrypoint) -


def test_emit_if_configured_is_a_true_no_op_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default state in every environment today (no compose service,
    Airflow env, or image installs `datahub`) — must never import datahub
    or raise, only report why it skipped."""
    monkeypatch.delenv("PHASE2_DATAHUB_SERVER", raising=False)
    import builtins

    real_import = builtins.__import__

    def _blocking_import(name, *args, **kwargs):
        if name == "datahub" or name.startswith("datahub."):
            raise AssertionError("must never import datahub when unconfigured")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocking_import)
    report = emit_lineage_if_configured("run-1", "phase2_rag_ingest")
    assert report == {"emitted": False, "reason": "PHASE2_DATAHUB_SERVER not set"}


def test_emit_if_configured_catches_emit_failure_instead_of_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Governance telemetry must never fail the data task that already
    committed its work — a bad/unreachable server (or a missing `datahub`
    package) reports {"emitted": False, ...} instead of raising."""
    monkeypatch.setenv("PHASE2_DATAHUB_SERVER", "http://unreachable.invalid:9999")
    report = emit_lineage_if_configured("run-1", "phase2_rag_ingest")
    assert report["emitted"] is False
    assert "reason" in report
