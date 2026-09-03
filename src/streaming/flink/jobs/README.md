# Flink job home (mounted into jobmanager)

This directory is bind-mounted read-only into the `flink-jobmanager` and
`flink-taskmanager` containers at `/opt/flink/jobs`. It holds the PyFlink job
source, `price_event_job.py`, run via:

```bash
flink run --python /opt/flink/jobs/price_event_job.py \
  --config /opt/flink/config/flink-streaming.yaml --variant baseline
```

See `docs/flink-stream-processing.md` for the full reproduce steps. The
`flink-jobmanager`/`flink-taskmanager` images are built from
`infra/flink/Dockerfile` (PyFlink 1.20.3 + the Kafka connector jar), not the
stock `apache/flink` image, so `import pyflink` and the connector are both
available inside the container.

For platform the default streaming path does not require this job: the
burst / late-arrival / dedup logic lives in
`src/streaming/kafka_to_bronze_consumer.py` and is exercised via the default
`MicroBatchConsumer` smoke path. The Flink opt-in path (W26) is wired through
`dag_04` and `src.streaming.flink.client` for the W20 screenshot evidence and
any future job that needs a real Flink runtime.
