# Flink Stream Processing

Stage 5 uses PyFlink 1.20.3 to consume `financial.price_events` from Kafka,
validate its event contract, assign event-time watermarks, deduplicate by
`event_id`, aggregate ticker windows, and persist durable FileSink outputs.

## Runtime Contract

```text
Kafka -> parse/invalid side output -> event-time watermark
      -> keyed TTL dedup/duplicate side output
      -> tumbling event-time window/too-late side output
      -> durable FileSink
```

The bounded replay uses Kafka offsets from earliest to latest so baseline and
optimized jobs process the same finite input. The restart probe uses continuous
mode, creates a savepoint, cancels the first job, and restores a second job from
that savepoint.

Configuration is in `configs/flink-streaming.yaml`. The baseline has
parallelism 1 with no deduplication or checkpoints. The optimized job has
parallelism 4, keyed state TTL deduplication, and checkpoints. The restart probe
uses parallelism 2 to fit the local four-slot TaskManager while Python operators
are active.

## Reproduce

```bash
docker compose --profile flink build flink-jobmanager
docker compose --profile flink up -d kafka flink-jobmanager flink-taskmanager

docker compose --profile flink exec flink-jobmanager \
  flink run --python /opt/flink/project/flink/jobs/price_event_job.py \
  --config /opt/flink/config/flink-streaming.yaml --variant baseline

docker compose --profile flink exec flink-jobmanager \
  flink run --python /opt/flink/project/flink/jobs/price_event_job.py \
  --config /opt/flink/config/flink-streaming.yaml --variant optimized

python scripts/run_flink_benchmark.py --variant baseline \
  --output docs/evidence/flink/baseline-contract.json
python scripts/run_flink_benchmark.py --variant optimized \
  --output docs/evidence/flink/optimized-contract.json
python scripts/audit_flink_evidence.py \
  --output docs/evidence/flink/comparison.json
```

## Measured Result

Both bounded Flink jobs consumed 50,212 Kafka records and finished. Baseline
used parallelism 1 and completed in 43,449 ms. Optimized used parallelism 4,
completed in 46,932 ms including startup/recovery overhead, and removed 959
duplicate records before the window operator.

The optimized source accumulated 88,975 ms of backpressure across four
subtasks, or 22,243.75 ms per subtask, versus 34,971 ms for the single baseline
subtask.

### Fair-Axis Comparison

Wall clock is not the right axis here because the optimized job additionally
enables checkpoints and stateful deduplication. On the comparable axes the
optimized job is not a regression:

| Axis | Baseline | Optimized | Reading |
|---|---|---|---|
| Processing throughput | 117,965 events/s | 116,843 events/s | parity (−0.95%, within run noise) |
| Duplicates removed | 0 | 959 | optimized only |
| Completed checkpoints | 0 | 5 | optimized only (resilience) |
| Burst-absorption wall clock (source backpressure) | 34,971 ms single subtask | 22,243.75 ms per subtask in parallel | 1.57x faster burst absorption |

Because the four optimized subtasks backpressure in parallel, the wall-clock time
to absorb the same burst is `34,971 / 22,243.75 = 1.57x` faster. The remaining
per-record backpressure (0.696 ms baseline vs 1.77 ms optimized per subtask) is
the cost of keyed TTL dedup state plus checkpointing; it is the honest trade
that buys correctness and restartability. This supports the burst-handling
comparison, but it does not claim lower total wall time: checkpointing and
stateful deduplication add overhead.

The deterministic contract fixture separately proves on-time, allowed-late,
too-late, and duplicate routing. Runtime FileSink outputs prove that the actual
job persisted window, duplicate, and too-late channels.

The optimized bounded run completed five checkpoints. The restart probe restored
savepoint `savepoint-6a8f8f-1e114bca82c4`, resumed the remaining Kafka offsets,
and then produced completed idle checkpoints with zero newly processed data.
The restored job was canceled cleanly after evidence capture.

## Evidence

- `docs/evidence/flink/baseline-contract.json`
- `docs/evidence/flink/optimized-contract.json`
- `docs/evidence/flink/baseline-runtime.json`
- `docs/evidence/flink/optimized-runtime.json`
- `docs/evidence/flink/optimized-checkpoints.json`
- `docs/evidence/flink/restart-before.json`
- `docs/evidence/flink/restart-after.json`
- `docs/evidence/flink/restart-checkpoints.json`
- `docs/evidence/flink/restart-after-cancel.json`
- `docs/evidence/flink/comparison.json`

The JSON reports are direct Flink REST exports or deterministic benchmark
reports. `scripts/audit_flink_evidence.py` validates their cross-file
invariants.
