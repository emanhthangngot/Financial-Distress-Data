---
phase: 5
title: "Implement Flink Streaming Processing"
status: completed
priority: P1
effort: "1-2 weeks"
dependencies: [3]
---

# Phase 5: Implement Flink Streaming Processing

## Overview

Add the missing Flink pipeline for event-time stream processing and all 10 streaming-job points.

## Requirements

- Kafka source and durable sink.
- Baseline plus optimized execution.
- Burst handling, event-time watermarks, allowed lateness/late side output, duplicate handling, and windows.

## Related Code Files

- Create: `flink/` using the instructor-approved Java or PyFlink stack
- Modify: `docker-compose.yml`
- Create: `scripts/run_flink_benchmark.py`
- Create: `tests/` integration fixtures for Flink output
- Create: `docs/flink-stream-processing.md`

## Implementation Steps

1. Lock language/API and pinned Flink version from official documentation.
2. Consume keyed Kafka events and validate schema.
3. Assign bounded-out-of-orderness watermarks.
4. Implement dedup state with TTL and deterministic event IDs.
5. Add event-time tumbling/sliding windows and explicit output grain.
6. Configure allowed lateness and side output for too-late events.
7. Benchmark burst/backpressure baseline and optimized parallelism/checkpoint settings.
8. Persist main, updated late firing, and rejected/late outputs idempotently.

## Stream Contract

```text
Kafka price/news/alert topics
  -> parse + contract validation
  -> assign event timestamps + bounded watermark
  -> key by ticker/event type
  -> dedup state with TTL
  -> event-time window aggregation
  -> main result sink
  -> late side-output sink
  -> invalid-record sink
```

## Task Breakdown

| ID | Task | Required proof | Rubric points |
|---|---|---|---:|
| P5-T1 | Add pinned Flink jobmanager/taskmanager Compose profile and Kafka connector | Healthy UI/job deployment | - |
| P5-T2 | Implement baseline pass-through/window job | Baseline UI + metrics | 2 |
| P5-T3 | Handle burst/backpressure | Throughput/backpressure before/after | 2 |
| P5-T4 | Assign watermarks and handle late data | On-time/allowed-late/too-late outputs | 2 |
| P5-T5 | Handle duplicate events with keyed state TTL | Duplicate before/after | 2 |
| P5-T6 | Implement event-time window aggregation | Code capture + output validation | 2 |
| P5-T7 | Add checkpoints/restart idempotency | Restart test and checkpoint UI | Quality gate |
| P5-T8 | Create benchmark runner and document results | Repeated-run metrics | Proof |

## Validation

```bash
docker compose --profile flink config
docker compose --profile flink up -d flink-jobmanager flink-taskmanager kafka
python -m pytest -q tests/integration/test_flink_outputs.py
python scripts/run_flink_benchmark.py --scenario baseline
python scripts/run_flink_benchmark.py --scenario optimized
```

## Evidence Outputs

- Flink job graph and operator code reference.
- Watermark metric and late side-output proof.
- Burst/backpressure comparison.
- Duplicate-rate comparison.
- Window result query output and checkpoint/restart evidence.

## Success Criteria

- [x] Deterministic fixture proves on-time, allowed-late, too-late, duplicate, and burst behavior.
- [x] Flink REST evidence records job graph, throughput/backpressure, and checkpoints.
- [x] Window code is directly referenced by rubric evidence.
- [x] Savepoint restore resumes Kafka offsets with restored dedup state and reaches idle checkpoints.

## Risks And Rollback

Avoid hand-rolled streaming semantics. Follow official Flink window/watermark APIs and keep the existing Python micro-batcher only as a legacy comparison until migration passes.

## Resolution

PyFlink 1.20.3 was selected to match the repository's Python-first stack. The
job uses DataStream watermark, state TTL, window, Kafka source, and FileSink
APIs rather than reproducing those runtime semantics locally.
