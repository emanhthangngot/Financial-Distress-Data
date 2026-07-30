# Phase 5 Completion Report

## Status

Completed on 2026-07-30. R20-R24 are implemented, runtime-verified, and covered
by a correlated evidence auditor. Final rubric acceptance remains part of
Phase 9.

## Delivered

- Pinned Flink 1.20.3 JobManager/TaskManager Compose profile and Kafka
  connector image.
- Bounded baseline and optimized PyFlink DataStream jobs.
- Shared price-event validation with invalid-record side output.
- Bounded-out-of-orderness watermarks, allowed lateness, and too-late side
  output.
- Event-time tumbling ticker windows with explicit output grain.
- Keyed `event_id` deduplication using TTL state.
- Durable FileSink outputs for windows, duplicates, too-late, and invalid
  records.
- Checkpointing plus continuous savepoint/cancel/restore probe.
- Deterministic semantic benchmark, runtime REST exports, and correlated
  evidence auditor.

## Runtime Evidence

- Correlated run: `generator-evidence-v1`.
- Baseline and optimized jobs each consumed 50,212 Kafka records.
- Baseline: parallelism 1, 43,449 ms, 34,971 ms source backpressure.
- Optimized: parallelism 4, 46,932 ms total, 22,243.75 ms source
  backpressure per subtask.
- Stateful deduplication removed 959 runtime duplicate records.
- Optimized bounded job completed five checkpoints.
- Restart probe restored one savepoint and recorded 21 completed checkpoints.
- The restored job resumed remaining Kafka offsets, reached idle checkpoints
  with zero newly processed data, then was canceled cleanly.

The optimized wall time is not claimed as faster. Checkpointing and stateful
deduplication add overhead; burst evidence is the lower normalized source
backpressure across four subtasks.

## Rubric Mapping

| ID | Implemented proof | Status |
|---|---|---|
| R20 | Finite Kafka-to-window baseline job and REST job export | Verified |
| R21 | Parallel burst configuration and normalized backpressure comparison | Verified |
| R22 | Watermark, allowed-late fixture, too-late side output, runtime sink | Verified |
| R23 | Keyed TTL dedup, 959 removed records, savepoint state restore | Verified |
| R24 | Event-time tumbling window code, boundary tests, durable results | Verified |

## Evidence Index

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
- `docs/flink-stream-processing.md`

## Verification

- Focused Stage 5 tests: 8 passed.
- Full repository suite after final validator fix: 155 passed.
- Ruff, Python compileall, Docker Compose config, and `git diff --check`: passed.
- Evidence audit: 9/9 correlated invariants passed.
- Manual code review found and fixed mismatched `event_type` validation and
  invalid timestamp/numeric routing.
- Continuous probe job was canceled after evidence capture.

## Unresolved Questions

- Confirm whether the instructor requires literal Flink UI screenshots. Direct
  REST exports contain job graph metrics and checkpoint history, but the
  available Firefox capture rendered only the dashboard shell. `agent-browser`
  was not installed, Chrome DevTools required an X server, and Node Playwright
  was unavailable.
