"""Deployable: Kafka `financial.price_events` -> Feast online store (Redis
push) + checkpoint. Runs from a container image, not the host env
(phase-04-implementation-notes.md section 9) — ``run_online_job`` is the
entrypoint ``dags/stream_feature_online.py`` wraps.

Reuses ``src.ml.feast.offline_job.aggregate_stream_events`` for the actual
aggregation (DRY — the online and offline deployables compute the same
``stream_market_features`` rows, they only differ in where the rows land).
Feast/Kafka are lazy imports (D4).
"""

from __future__ import annotations

from typing import Any

from src.ml.feast.offline_job import aggregate_stream_events

STREAM_FEATURE_VIEW = "stream_market_features"


def push_rows_online(store: Any, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Pushes already-aggregated rows via ``store.push(..., to=PushMode.
    ONLINE)`` — offline is untouched (that is ``offline_job.py``'s job),
    matching the PushSource split declared in
    ``feature_definitions.build_feature_objects``."""
    if not rows:
        return {"rows_pushed": 0}

    import pandas as pd

    from feast.data_source import PushMode

    frame = pd.DataFrame(rows)
    store.push(f"{STREAM_FEATURE_VIEW}_push_source", frame, to=PushMode.ONLINE)
    return {"rows_pushed": len(rows)}


def push_events_online(store: Any, events: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregates ``events`` then pushes — see ``push_rows_online``."""
    return push_rows_online(store, aggregate_stream_events(events))


def run_online_job() -> dict[str, Any]:
    """Airflow entrypoint, no args: reads every setting from environment
    inside this function (never at DAG-module import time —
    dags/stream_feature_online.py's only job is to point a
    PythonOperator at this callable). Same bounded-consumption and
    commit-after-write reasoning as ``offline_job.run_offline_job`` — see
    its docstring."""
    import os

    from kafka import KafkaConsumer

    from feast import FeatureStore

    bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    topic = os.environ.get("PLATFORM_PRICE_EVENTS_TOPIC", "financial.price_events")
    max_events = int(os.environ.get("PLATFORM_STREAM_MAX_EVENTS", "1000"))
    repo_path = os.environ.get("PLATFORM_FEAST_REPO_PATH", "feature_repo/structured")

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id="platform-stream-feature-online",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        consumer_timeout_ms=int(os.environ.get("PLATFORM_STREAM_POLL_TIMEOUT_MS", "10000")),
    )
    events: list[dict[str, Any]] = []
    last_offset = 0
    try:
        for message in consumer:
            events.append(message.value)
            last_offset = message.offset
            if len(events) >= max_events:
                break

        store = FeatureStore(repo_path=repo_path)
        rows = aggregate_stream_events(events)
        result = push_rows_online(store, rows)
        consumer.commit()
    finally:
        consumer.close()

    import uuid

    from src.governance.lineage import (
        audit_lineage,
        emit_lineage_if_configured,
    )
    from src.ml.feast.materialization import record_stream_checkpoint

    last_event_ts = rows[-1]["event_timestamp"] if rows else None
    record_stream_checkpoint("platform_stream_feature_online", last_offset, last_event_ts)
    return {
        "events_consumed": len(events),
        "lineage_audit": audit_lineage(pipeline_name="platform_stream_feature_online"),
        "lineage_emit": emit_lineage_if_configured(
            run_id=uuid.uuid4().hex, pipeline_name="platform_stream_feature_online"
        ),
        **result,
    }
