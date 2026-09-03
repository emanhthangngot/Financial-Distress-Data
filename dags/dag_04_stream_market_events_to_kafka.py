"""DAG 04 — Stream market events to Kafka (Flink-opt-in).

This DAG is the Stage 1 streaming entry point. It has two execution
modes, picked at task-call time via the ``ENABLE_FLINK`` env var:

* **Default (opt-out)** — ``ENABLE_FLINK`` unset. Use the original
  in-process ``MicroBatchConsumer`` to flush a tiny batch of fixture
  events through the existing pipeline. Smoke-test friendly, no
  extra infra required.
* **Opt-in** — ``ENABLE_FLINK=1``. Submit a real Flink job to the
  local jobmanager (``FLINK_JOBMANAGER_URL``) that consumes the
  same Kafka topics and writes Bronze Parquet objects. Used for
  the W17 streaming problem generator and the rubric idx 27-31
  Flink evidence.

The smoke mode keeps the DAG runnable on any developer machine; the
Flink mode is for the W20 screenshot evidence and CI integration
when a Flink service is part of the compose profile.
"""

from __future__ import annotations

from dags.utils.dag_utils import DEFAULT_ARGS, airflow_imports
from src.streaming.events import StreamEvent
from src.streaming.flink import client as flink_client
from src.streaming.kafka_to_bronze_consumer import MicroBatchConsumer

DAG, PythonOperator = airflow_imports()

FLINK_JAR_ID = "lakehouse-burst-handler"


def _stream_smoke():
    """Task callable. Dispatches to Flink or MicroBatch based on env."""
    if flink_client.is_enabled():
        job_id = flink_client.submit_job(
            jar_id=FLINK_JAR_ID,
            program_args=[
                "--bootstrap",
                "kafka:9092",
                "--bucket",
                "financial-distress-lake",
            ],
        )
        return {"flink_job_id": job_id, "mode": "flink"}

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


if DAG is not None:
    with DAG(
        dag_id="04_stream_market_events_to_kafka",
        default_args=DEFAULT_ARGS,
        schedule=None,
        catchup=False,
        tags=["financial-distress", "stage-1", "flink-opt-in"],
    ) as dag:
        PythonOperator(task_id="produce_smoke_events_microbatch", python_callable=_stream_smoke)
