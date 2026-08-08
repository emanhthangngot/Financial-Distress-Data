"""Deployable: Kafka `financial.price_events` -> offline parquet append +
checkpoint. Runs from a container image, not the host env
(phase-04-implementation-notes.md section 9) — ``run_offline_job`` is the
entrypoint ``dags/phase2/phase2_stream_feature_offline.py`` wraps.

``aggregate_stream_events`` is pure and carries the actual logic; it is
tested directly (no Kafka needed). Kafka/minio/psycopg are lazy imports (D4).
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any


def aggregate_stream_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Groups price_update events by ticker and computes
    ``stream_market_features``: ``last_price`` (latest by event_timestamp),
    ``event_count_1h`` (count in the batch — the caller controls the window
    by how it batches ``events``), ``price_change_pct_1h`` (relative change
    from the batch's first to last price). Accepts either a raw payload dict
    (``ticker``/``price``/``event_timestamp``) or a Kafka message's
    ``.value`` (a ``StreamEvent``-shaped dict with a nested ``payload``)."""
    by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        payload = event.get("payload", event)
        by_ticker[payload["ticker"]].append(payload)

    rows: list[dict[str, Any]] = []
    for ticker, ticker_events in by_ticker.items():
        ordered = sorted(ticker_events, key=lambda item: item["event_timestamp"])
        first_price = float(ordered[0]["price"])
        last_price = float(ordered[-1]["price"])
        change_pct = None if first_price == 0 else (last_price - first_price) / first_price
        rows.append(
            {
                "ticker": ticker,
                "last_price": last_price,
                "event_count_1h": len(ordered),
                "price_change_pct_1h": change_pct,
                "event_timestamp": ordered[-1]["event_timestamp"],
            }
        )
    return rows


def write_offline_rows(rows: list[dict[str, Any]], client: Any, bucket: str) -> None:
    """Appends one new object under ``phase2/offline/stream_features/`` per
    call via the existing MinIO writer (src.io.minio_writer — reused, not
    reimplemented, per phase-04-implementation-notes.md section 3.1's "no
    new S3 client" rule). Each run gets a unique, timestamp-ordered object
    key (never the same key twice) so successive runs accumulate rather
    than each overwriting the last one — a fixed key here would silently
    destroy the previous batch, since ``write_minio_dataset`` always
    overwrites its exact key. A no-op on an empty batch — Bronze is
    append-only, but an empty write is not an event."""
    if not rows:
        return
    from src.io.minio_writer import write_minio_dataset

    object_key = f"{bucket}/phase2/offline/stream_features/{_new_object_id()}.parquet"
    write_minio_dataset(client, bucket, object_key, rows)


def _new_object_id() -> str:
    from datetime import UTC, datetime

    return f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"


def run_offline_job() -> dict[str, Any]:
    """Airflow entrypoint, no args: reads every setting from environment
    inside this function (never at DAG-module import time —
    dags/phase2/phase2_stream_feature_offline.py's only job is to point a
    PythonOperator at this callable).

    Bounded consumption: ``consumer_timeout_ms`` makes the loop terminate
    when the topic is drained instead of blocking until
    ``PHASE2_STREAM_MAX_EVENTS`` messages exist (the prior design could hang
    to the task's ``dagrun_timeout`` on a slow topic). Offsets are committed
    after a successful write so a rerun does not reprocess the same
    messages — ``enable_auto_commit=False`` on the consumer means this
    function owns commit timing, matching "at-least-once, commit after
    write" rather than Kafka's default "commit before processing"."""
    import os

    from kafka import KafkaConsumer

    bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    topic = os.environ.get("PHASE2_PRICE_EVENTS_TOPIC", "financial.price_events")
    max_events = int(os.environ.get("PHASE2_STREAM_MAX_EVENTS", "1000"))

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id="phase2-stream-feature-offline",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        consumer_timeout_ms=int(os.environ.get("PHASE2_STREAM_POLL_TIMEOUT_MS", "10000")),
    )
    events: list[dict[str, Any]] = []
    last_offset = 0
    try:
        for message in consumer:
            events.append(message.value)
            last_offset = message.offset
            if len(events) >= max_events:
                break

        rows = aggregate_stream_events(events)
        if rows:
            write_offline_rows(rows, minio_client_from_env(), _bucket())
        consumer.commit()
    finally:
        consumer.close()

    from src.governance.phase2_lineage import audit_phase2_lineage
    from src.ml.feast.materialization import record_stream_checkpoint

    last_event_ts = rows[-1]["event_timestamp"] if rows else None
    record_stream_checkpoint("phase2_stream_feature_offline", last_offset, last_event_ts)
    return {
        "events_consumed": len(events),
        "rows_written": len(rows),
        "lineage_audit": audit_phase2_lineage(pipeline_name="phase2_stream_feature_offline"),
    }


def _bucket() -> str:
    from src.io.paths import DEFAULT_BUCKET

    return DEFAULT_BUCKET


def minio_client_from_env() -> Any:
    """``MINIO_ROOT_USER``/``MINIO_ROOT_PASSWORD`` — the repo's actual
    convention (docker-compose.yml's airflow-* services export these, and
    every other in-container reader uses them: src/jobs/stage1_evidence_job.py,
    src/transforms/spark_session.py, src/catalog/duckdb_runner.py).
    ``MINIO_ACCESS_KEY``/``MINIO_SECRET_KEY`` is a host-only convention used
    by scripts/run_generator_and_profile.py, not the in-container one."""
    import os

    from minio import Minio

    endpoint = os.environ.get("MINIO_ENDPOINT", "minio:9000")
    secure = endpoint.startswith("https://")
    endpoint = endpoint.removeprefix("http://").removeprefix("https://")
    return Minio(
        endpoint,
        access_key=os.environ["MINIO_ROOT_USER"],
        secret_key=os.environ["MINIO_ROOT_PASSWORD"],
        secure=secure,
    )
