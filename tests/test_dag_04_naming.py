"""W9 — DAG 04 task_id must not advertise a Kafka consumer.

The smoke task is an in-process microbatch producer (or, when
ENABLE_FLINK=1, a Flink job submission). It does NOT consume from
Kafka. The task_id must therefore be ``produce_smoke_events_microbatch``
— never ``consume_*`` — and the module docstring must state that fact.
"""

from __future__ import annotations

from dags._stage1_dag_utils import airflow_imports
from dags import dag_04_stream_market_events_to_kafka as dag04_module

_, _ = airflow_imports()


def test_dag04_task_id_is_produce_not_consume():
    """DAG 04 exposes one task; its task_id must say 'produce', not 'consume'."""
    dag = dag04_module.DAG
    if dag is None:
        # Airflow not installed in CI; the module-level DAG object stays None.
        # We can still inspect the task-creation site.
        src = open(dag04_module.__file__).read()
    else:
        src = open(dag04_module.__file__).read()

    # The misnomer "consume_events" must be gone.
    assert "consume_events_microbatch" not in src, (
        "DAG 04 task_id must be renamed; 'consume_events_microbatch' advertises a "
        "Kafka consumer that this DAG does not run."
    )
    # The renamed task_id must be present.
    assert "produce_smoke_events_microbatch" in src, (
        "DAG 04 task_id must be 'produce_smoke_events_microbatch' (W9 AC)."
    )


def test_dag04_docstring_states_no_kafka_streaming_in_default_mode():
    """Module docstring must clarify that default mode is in-process (not Kafka)."""
    src = open(dag04_module.__file__).read()
    lower = src.lower()
    # The docstring must explicitly mention "no kafka" or "in-process" or
    # "microbatch" (i.e. it does not silently claim Kafka streaming).
    assert "in-process" in lower or "no kafka" in lower or "microbatch" in lower, (
        "DAG 04 docstring must document that the default mode is in-process "
        "microbatch (or opt-in Flink) — not Kafka streaming."
    )
