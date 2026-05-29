from __future__ import annotations

from dags._stage1_dag_utils import DEFAULT_ARGS, airflow_imports
from src.streaming.events import StreamEvent
from src.streaming.kafka_to_bronze_consumer import MicroBatchConsumer

DAG, PythonOperator = airflow_imports()


def _stream_smoke() -> list[dict]:
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
        tags=["financial-distress", "stage-1"],
    ) as dag:
        PythonOperator(task_id="consume_events_microbatch", python_callable=_stream_smoke)
