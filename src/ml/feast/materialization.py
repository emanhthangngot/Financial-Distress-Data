"""FeatureMaterializationService implementation (contract:
src.ml.contracts). Owns batch/stream materialization checkpoints, TTL, and
idempotency for the fd_structured Feast project.

Every Feast/redis/psycopg import is lazy, inside the function that needs it
— D4, phase-04-implementation-notes.md section 0. This module is safely
importable in `.venv` (the fast loop) as long as callers never invoke the
methods there; only ``FEATURE_VIEW_TTL`` (imported from
``feature_definitions``, also import-safe) is touched at module load time.
"""

from __future__ import annotations

from typing import Any

from src.ml.contracts import FeatureMaterializationService
from src.ml.feast.feature_definitions import FEATURE_VIEW_TTL


class FeastMaterializationService(FeatureMaterializationService):
    def __init__(self, repo_path: str, pg_dsn_env: str = "PHASE2_PG_DSN") -> None:
        self.repo_path = repo_path
        self.pg_dsn_env = pg_dsn_env

    def _store(self) -> Any:
        from feast import FeatureStore

        return FeatureStore(repo_path=self.repo_path)

    def materialize_offline_to_online(
        self, feature_view: str, start_ts: Any, end_ts: Any
    ) -> dict[str, Any]:
        """``feast materialize_incremental``-equivalent for one named view.
        Idempotent by construction: Feast's own materialization job tracks
        the last-materialized interval per feature view in the registry, so
        re-running an already-covered interval is a no-op.

        ``start_ts``/``end_ts`` accept either a ``datetime`` or an
        ISO-8601 string — Feast 0.65's ``FeatureStore.materialize`` requires
        a tz-aware ``datetime`` and raises ``AttributeError`` on a bare
        string (verified: ``utils.make_tzaware`` assumes ``.tzinfo``), which
        matters because Airflow's templated ``{{ data_interval_start }}``
        arrives here as a string."""
        start = _as_datetime(start_ts)
        end = _as_datetime(end_ts)
        store = self._store()
        store.materialize(start_date=start, end_date=end, feature_views=[feature_view])
        revision = self.record_registry_revision(store)
        return {
            "feature_view": feature_view,
            "start_ts": start.isoformat(),
            "end_ts": end.isoformat(),
            "registry_revision": revision,
        }

    def push_stream_features_offline(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        from src.ml.feast.offline_job import aggregate_stream_events, write_offline_rows

        rows = aggregate_stream_events(events)
        if rows:
            from src.ml.feast.offline_job import minio_client_from_env

            write_offline_rows(rows, minio_client_from_env(), _bucket())
        return {"rows": rows}

    def push_stream_features_online(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        from src.ml.feast.online_job import push_events_online

        store = self._store()
        return push_events_online(store, events)

    def ttl_policy(self) -> dict[str, str]:
        return {name: str(ttl) for name, ttl in FEATURE_VIEW_TTL.items()}

    def record_registry_revision(self, store: Any) -> str:
        """Hashes the registry proto and records a row in
        ``ml_metadata.feast_registry_revision`` (sql/init_ml_metadata.sql).
        No-ops (returns the digest without writing) when ``pg_dsn_env`` isn't
        set — unit tests exercise ``materialize_offline_to_online`` against a
        disposable local registry with no Postgres attached.

        Caveat: the registry proto embeds ``last_updated`` timestamps and
        protobuf serialization is not byte-canonical, so this digest can
        change across two applies of an *unchanged* definition set — it
        identifies "a materialize ran", not "the definitions are these
        exact bytes". A definition-content digest would need to hash the
        feature view/entity specs directly, not the whole registry proto;
        left as-is since nothing currently depends on cross-run stability
        of this value beyond it being present."""
        import hashlib

        registry_proto = store.registry.proto()
        digest = hashlib.sha256(registry_proto.SerializeToString()).hexdigest()[:16]
        self._write_revision_row(store.project, digest, len(registry_proto.feature_views))
        return digest

    def _write_revision_row(self, project: str, digest: str, feature_view_count: int) -> None:
        import os

        dsn = os.environ.get(self.pg_dsn_env)
        if not dsn:
            return
        import psycopg

        with psycopg.connect(dsn) as conn:
            conn.execute(
                "INSERT INTO ml_metadata.feast_registry_revision "
                "(revision_id, project, registry_digest, feature_view_count) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (revision_id) DO NOTHING",
                (digest, project, digest, feature_view_count),
            )
            conn.commit()


def _as_datetime(value: Any) -> Any:
    if isinstance(value, str):
        from datetime import datetime

        return datetime.fromisoformat(value)
    return value


def _bucket() -> str:
    from src.io.paths import DEFAULT_BUCKET

    return DEFAULT_BUCKET


def record_stream_checkpoint(
    job_name: str, last_offset: int, last_event_ts: str | None, pg_dsn_env: str = "PHASE2_PG_DSN"
) -> None:
    """Shared by both stream deployables (offline_job.py, online_job.py) so
    ``ml_metadata.stream_feature_checkpoint`` has one writer. No-ops when
    ``pg_dsn_env`` isn't set (unit tests never reach a real Postgres)."""
    import os

    dsn = os.environ.get(pg_dsn_env)
    if not dsn:
        return
    import psycopg

    with psycopg.connect(dsn) as conn:
        conn.execute(
            "INSERT INTO ml_metadata.stream_feature_checkpoint "
            "(job_name, last_offset, last_event_ts) VALUES (%s, %s, %s) "
            "ON CONFLICT (job_name) DO UPDATE SET "
            "last_offset = EXCLUDED.last_offset, last_event_ts = EXCLUDED.last_event_ts, "
            "updated_ts = now()",
            (job_name, last_offset, last_event_ts),
        )
        conn.commit()


def run_materialize_task() -> dict[str, Any]:
    """Airflow entrypoint, no args: reads every setting from environment
    inside this function (never at DAG-module import time —
    dags/phase2/phase2_feature_materialize.py's only job is to point a
    PythonOperator at this callable). ``PHASE2_MATERIALIZE_START_TS``/
    ``_END_TS`` default to the last 24h so a manual run has a sane window
    without requiring every env var to be set."""
    import os
    from datetime import UTC, datetime, timedelta

    repo_path = os.environ.get("PHASE2_FEAST_REPO_PATH", "feature_repo/structured")
    feature_view = os.environ.get("PHASE2_FEATURE_VIEW", "company_financial_features")
    now = datetime.now(UTC)
    start_ts = os.environ.get("PHASE2_MATERIALIZE_START_TS", (now - timedelta(days=1)).isoformat())
    end_ts = os.environ.get("PHASE2_MATERIALIZE_END_TS", now.isoformat())

    import uuid

    service = FeastMaterializationService(repo_path)
    result = service.materialize_offline_to_online(feature_view, start_ts, end_ts)

    from src.governance.phase2_lineage import (
        audit_phase2_lineage,
        emit_phase2_lineage_if_configured,
    )

    result["lineage_audit"] = audit_phase2_lineage(pipeline_name="phase2_feature_materialize")
    result["lineage_emit"] = emit_phase2_lineage_if_configured(
        run_id=uuid.uuid4().hex, pipeline_name="phase2_feature_materialize"
    )
    return result
