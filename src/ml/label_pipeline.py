"""Phase 2 label table build.

Wraps ``src.transforms.compute_distress_labels.compute_labels`` (Phase 1,
read-only import — AGENTS.md forbids editing Phase 1) and reshapes its
output to the ``ml_metadata.label_table`` contract. Registered as offline
parquet + a Postgres row, never as a Feast FeatureView — see
``plans/260802-1037-unified-phase2-ml-llm-gitops/phase-04-implementation-notes.md``,
section 5, for why: a training-time label must never be reachable through
the online feature-serving path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.transforms.compute_distress_labels import RULE_VERSION, compute_labels

LABEL_VERSION = f"altman-z-{RULE_VERSION}"
LABEL_SOURCE = "proxy_not_ground_truth"
PROXY_LABEL_NOTICE = (
    "label is a rule-based Altman Z''-Score proxy, not a ground-truth "
    "financial-distress outcome. Never present it to an end user as verified."
)


def build_labels(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute distress labels and project them to the label_table schema
    (ticker, event_timestamp, label, label_version, created_ts,
    training_eligible, label_source). Deterministic: identical input yields
    identical output on every call."""
    computed = compute_labels(rows)
    return [
        {
            "ticker": row["ticker"],
            "event_timestamp": row["event_timestamp"],
            "label": row["distress_label"],
            "label_version": LABEL_VERSION,
            "created_ts": row["created_ts"],
            "training_eligible": row["training_eligible"],
            "label_source": LABEL_SOURCE,
        }
        for row in computed
    ]


def write_labels_postgres(rows: list[dict[str, Any]], conn: Any) -> int:
    """Upsert into ``ml_metadata.label_table``, keeping the latest
    ``created_ts`` per (ticker, event_timestamp, label_version) — AGENTS.md
    dedupe-by-latest-created_ts rule. Lazy psycopg import per the two-venv
    rule (D4, phase-04-implementation-notes.md section 0) is the caller's
    job: ``conn`` is injected, this function never imports psycopg."""
    if not rows:
        return 0
    with conn.cursor() as cur:
        for row in rows:
            cur.execute(
                """
                INSERT INTO ml_metadata.label_table
                    (ticker, event_timestamp, label, label_version, created_ts,
                     training_eligible, label_source)
                VALUES (%(ticker)s, %(event_timestamp)s, %(label)s, %(label_version)s,
                        %(created_ts)s, %(training_eligible)s, %(label_source)s)
                ON CONFLICT (ticker, event_timestamp, label_version) DO UPDATE SET
                    label = EXCLUDED.label,
                    created_ts = EXCLUDED.created_ts,
                    training_eligible = EXCLUDED.training_eligible,
                    label_source = EXCLUDED.label_source
                WHERE EXCLUDED.created_ts >= ml_metadata.label_table.created_ts
                """,
                row,
            )
        conn.commit()
    return len(rows)


def run_label_build(
    generator_config_path: str | Path, profile: str = "ci", pg_dsn_env: str = "PLATFORM_PG_DSN"
) -> dict[str, Any]:
    """Generate offline financial-statement rows, build labels, and persist
    to Postgres when ``pg_dsn_env`` is set (no-op write otherwise — unit
    tests never reach a real Postgres). This is the single callable
    ``dags/label_drift_build.py``'s label step wraps."""
    from src.generator.config import load_generator_config
    from src.generator.offline import generate_offline_data

    generator_config = load_generator_config(Path(generator_config_path), profile=profile)
    offline_data = generate_offline_data(generator_config)
    rows = build_labels(offline_data.financial_statements)

    import os

    dsn = os.environ.get(pg_dsn_env)
    written = 0
    if dsn:
        import psycopg

        with psycopg.connect(dsn) as conn:
            written = write_labels_postgres(rows, conn)

    return {"labels_built": len(rows), "labels_written": written}


def _fail(message: str) -> None:
    """Raise AirflowFailException when Airflow is present, else RuntimeError
    — mirrors dags/05_transform_bronze_to_silver.py's ``_airflow_fail``. The
    module must stay importable without Airflow, but the task itself must
    always fail loudly."""
    try:
        from airflow.exceptions import AirflowFailException

        raise AirflowFailException(message)
    except ImportError:
        raise RuntimeError(message) from None


def run_label_drift_build_task() -> dict[str, Any]:
    """Airflow entrypoint, no args: reads every setting from environment
    inside this function (never at DAG-module import time —
    dags/label_drift_build.py's only job is to point a
    PythonOperator at this callable).

    Runs both drift-report generation (the evidence for the two
    "data-generator drift/config" LLM rows) and the label build in one task.
    Labels are built from the **real, undrifted** generator output — drift
    is a separate, seeded post-transform applied only to the copy of the
    rows the report compares (src.drift.generator.apply_drift never mutates
    its input), so the label table is never trained on synthetically
    corrupted figures. Raises (fails the task) when the drift assertion
    itself fails — AGENTS.md's critical-failure-halts-downstream rule,
    matching scripts/run_platform_drift_report.py's CLI exit-1 behaviour so
    the two entrypoints agree.

    ``PLATFORM_DRIFT_OUTPUT_ROOT`` is read but **not yet mounted** into the
    Airflow containers (docker-compose.yml's airflow-* services mount
    ``dags``/``src``/``configs``/``sql``/``docs``, not ``outputs``) — a
    report written here from inside a container does not survive a
    container restart. Wiring that mount, or writing the report to MinIO
    instead, is deferred to slice 4D (evidence capture)."""
    import os

    from src.drift.generator import run_scenario_against_generator

    scenario_name = os.environ.get("PLATFORM_DRIFT_SCENARIO", "financial_deterioration")
    generator_config_path = os.environ.get(
        "PLATFORM_GENERATOR_CONFIG", "configs/generator-config.yaml"
    )
    drift_config_path = os.environ.get("PLATFORM_DRIFT_CONFIG", "configs/drift-config.yaml")
    profile = os.environ.get("PLATFORM_GENERATOR_PROFILE", "ci")
    output_root_env = os.environ.get("PLATFORM_DRIFT_OUTPUT_ROOT")
    kwargs: dict[str, Any] = {}
    if output_root_env:
        kwargs["output_root"] = Path(output_root_env)

    drift_directory, drift_report = run_scenario_against_generator(
        scenario_name,
        Path(drift_config_path),
        Path(generator_config_path),
        profile=profile,
        **kwargs,
    )
    if not drift_report["passed"]:
        _fail(
            f"drift assertion failed for scenario {scenario_name!r}: "
            f"observed_direction={drift_report['observed_direction']!r} "
            f"relative_change={drift_report['relative_change']:.4f} "
            f"threshold={drift_report['threshold']}"
        )

    label_result = run_label_build(generator_config_path, profile=profile)

    import uuid

    from src.governance.lineage import (
        audit_lineage,
        emit_lineage_if_configured,
    )

    return {
        "drift_report_path": str(drift_directory),
        "drift_passed": drift_report["passed"],
        "lineage_audit": audit_lineage(pipeline_name="platform_label_drift_build"),
        "lineage_emit": emit_lineage_if_configured(
            run_id=uuid.uuid4().hex, pipeline_name="platform_label_drift_build"
        ),
        **label_result,
    }
