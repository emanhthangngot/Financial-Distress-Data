"""Phase 2 DataHub lineage emitter (Flow E,
phase-04-implementation-notes.md section 2): every Phase 2 flow's run
summary emits through here to ``src.governance.datahub_emitter.
emit_governance``, using a Phase-2-only ``GovernanceModel`` loaded from
``configs/platform-governance.yaml`` — the Phase 1 governance config
(``configs/datahub/governance.yaml``) is never touched.

Mirrors ``scripts/sync_datahub_governance.py``'s split: audit locally
(``audit_governance_model``, no live server needed — this is what
``.venv``'s test suite exercises) versus emit to a real DataHub server
(lazy ``datahub`` SDK import, D4-style — DataHub isn't a `.venv`/`.venv-platform`
dependency at all, so this import must never happen at module load time).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.governance.datahub_model import (
    GovernanceModel,
    audit_governance_model,
    load_governance_model,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "configs" / "platform-governance.yaml"


def load_platform_governance_model(path: Path = DEFAULT_CONFIG_PATH) -> GovernanceModel:
    """Load and validate configs/platform-governance.yaml (or an override)."""
    return load_governance_model(path)


def audit_lineage(
    config_path: Path = DEFAULT_CONFIG_PATH, pipeline_name: str | None = None
) -> dict[str, Any]:
    """No-network audit: validates the model and summarizes coverage. Safe
    to call from tests and from a DAG task that only wants to confirm the
    lineage config is well-formed before (or instead of) an emit attempt —
    every ``run_*_task`` entrypoint in src/ml/feast, src/llm, src/ml calls
    this with its own ``pipeline_name`` so a run's lineage coverage is
    checked on every real invocation, not only in tests. ``pipeline_name``
    narrows to one pipeline's coverage when given, matching what
    ``emit_lineage`` would actually emit for that run."""
    model = load_platform_governance_model(config_path)
    if pipeline_name is not None:
        model = _model_for_pipeline(model, pipeline_name)
    return audit_governance_model(model)


def _model_for_pipeline(model: GovernanceModel, pipeline_name: str) -> GovernanceModel:
    """A copy of ``model`` containing only ``pipeline_name`` and the
    datasets it references — this is the actual narrowing
    ``emit_lineage`` needs: ``emit_governance``
    (src/governance/datahub_emitter.py) iterates *every* dataset/pipeline on
    whatever model it's given, so narrowing has to happen here, not there.
    A single DAG task run produced lineage for its own pipeline only, never
    every Phase 2 pipeline at once."""
    if pipeline_name not in model.pipelines:
        raise KeyError(
            f"unknown platform pipeline {pipeline_name!r}; known: {sorted(model.pipelines)}"
        )
    pipeline = model.pipelines[pipeline_name]
    referenced = {*pipeline.inputs, *pipeline.outputs, pipeline.contract_dataset}
    return GovernanceModel(
        schema_version=model.schema_version,
        datahub_version=model.datahub_version,
        environment=model.environment,
        platform_instance=model.platform_instance,
        owner=model.owner,
        datasets={name: model.datasets[name] for name in referenced},
        pipelines={pipeline_name: pipeline},
    )


def emit_lineage(
    run_id: str,
    pipeline_name: str,
    server: str,
    token: str | None = None,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> dict[str, Any]:
    """Emits one pipeline's lineage to a real DataHub server. ``pipeline_name``
    must be one of ``configs/platform-governance.yaml``'s declared pipelines —
    see ``_model_for_pipeline`` for how the whole-model config is narrowed
    to just this pipeline's datasets before ``emit_governance`` ever runs."""
    model = load_platform_governance_model(config_path)
    scoped_model = _model_for_pipeline(model, pipeline_name)

    from datahub.sdk import DataHubClient

    from src.governance.datahub_emitter import emit_governance

    client = DataHubClient(server=server, token=token)
    report = emit_governance(scoped_model, client, run_id)
    report["pipeline_name"] = pipeline_name
    return report


def emit_lineage_if_configured(
    run_id: str, pipeline_name: str, config_path: Path = DEFAULT_CONFIG_PATH
) -> dict[str, Any]:
    """Every real Phase 2 task entrypoint calls this (not the bare
    ``emit_lineage``) so a run always *attempts* a real DataHub emit
    when one is reachable, instead of leaving ``emit_lineage``
    defined but never invoked. No live DataHub server exists in this
    sandbox, so this mirrors the env-gated no-op pattern already used by
    ``FeastMaterializationService._write_revision_row`` and
    ``record_stream_checkpoint`` (src/ml/feast/materialization.py): unset
    ``PLATFORM_DATAHUB_SERVER`` means "no server configured", not "skip
    silently forever" — set it in the container/Airflow environment to turn
    this into a real emit with no code change. This entrypoint currently
    lives unwired into any deployment surface (no compose service, Airflow
    env, or image installs ``datahub``) — flip it on by adding
    ``PLATFORM_DATAHUB_SERVER``/``PLATFORM_DATAHUB_TOKEN`` plus the ``datahub``
    package to whichever image/Airflow environment should emit for real.

    Governance telemetry must never fail the data task that produced it —
    every caller here already committed its Kafka offset / wrote its rows
    before calling this. A ``datahub`` import error, auth failure, or
    network error is caught and reported the same way as the unconfigured
    case, never raised."""
    import os

    server = os.environ.get("PLATFORM_DATAHUB_SERVER")
    if not server:
        return {"emitted": False, "reason": "PLATFORM_DATAHUB_SERVER not set"}
    token = os.environ.get("PLATFORM_DATAHUB_TOKEN")
    try:
        report = emit_lineage(run_id, pipeline_name, server, token, config_path)
    except Exception as exc:  # noqa: BLE001 - telemetry must never fail the caller
        return {"emitted": False, "reason": f"{type(exc).__name__}: {exc}"}
    report["emitted"] = True
    return report
