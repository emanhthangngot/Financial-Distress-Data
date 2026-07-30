# Flink job artifacts (mounted into jobmanager)

This directory is bind-mounted into the `flink-jobmanager` container
at `/opt/flink/jobs` so locally-built jars can be picked up by the
jobmanager's `/jars/upload` endpoint and submitted via
`flink_client.submit_job(jar_id=...)`.

For Stage 1 we keep this empty on purpose: the burst / late-arrival /
dedup streaming logic lives in `src/streaming/kafka_to_bronze_consumer.py`
and is exercised via the default `MicroBatchConsumer` smoke path. The
Flink opt-in path (W26) is wired through `dag_04` and
`src.streaming.flink.client` for the W20 screenshot evidence and any
future jar that does need a real Flink runtime.
