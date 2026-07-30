---
phase: 3
title: "Build Configurable Problem Generator"
status: completed
priority: P1
effort: "1 week"
dependencies: [1, 2]
---

# Phase 3: Build Configurable Problem Generator

## Overview

Implement the rubric's complete offline and streaming problem generator with deterministic replay.

## Requirements

- Offline: skew, high cardinality, schema evolution, configured duplicates, stored source data.
- Streaming: burst, late/out-of-order, configured duplicates.
- Config controls scale, rates, distribution, seed, schema versions, and output paths.

## Related Code Files

- Create: `src/generator/`
- Create: `configs/generator-config.yaml`
- Create: `tests/test_generator.py`
- Create: `scripts/run_generator_and_profile.py`
- Create: `docs/data-generator.md`

## Implementation Steps

1. Define deterministic entities/events and source-area storage contracts.
2. Generate measurable sector/exchange skew and high-cardinality IDs.
3. Write old/new schema partitions with controlled null evolution.
4. Inject duplicate rates before Silver dedup.
5. Generate event-time bursts, late/out-of-order events, and streaming duplicates.
6. Write offline source data to MinIO/PostgreSQL and stream events to Kafka.
7. Produce profile metrics: distribution, approximate cardinality, null evolution, duplicate before/after, burst/late/duplicate rates, volume and format.

## Proposed Configuration Contract

```yaml
seed: 42
offline:
  companies: 100000
  quarters: 12
  dominant_sector_rate: 0.60
  high_cardinality_ids: 100000
  duplicate_rate: 0.02
  schema_change_date: 2024-01-01
streaming:
  events: 500000
  burst_multiplier: 10
  late_rate: 0.05
  duplicate_rate: 0.015
  max_out_of_order_seconds: 120
```

Final sizes must be benchmarked against local resources; values remain configurable.

## Task Breakdown

| ID | Task | Test oracle | Rubric points |
|---|---|---|---:|
| P3-T1 | Define typed config, seed and CLI | Same seed yields same hashes | 2+2 config |
| P3-T2 | Generate skewed companies/categories | Distribution within tolerance | 2 |
| P3-T3 | Generate high-cardinality identifiers | Exact/approx distinct report | 2 |
| P3-T4 | Generate old/new schema partitions | Old nulls and new populated fields | 2 |
| P3-T5 | Inject offline duplicates | Before rate and after dedup proof | 2 |
| P3-T6 | Persist generated offline source data | Read-back row/hash validation | 2 |
| P3-T7 | Generate timed burst schedule | Per-window throughput spike | 2 |
| P3-T8 | Generate late/out-of-order events | Event vs ingest-time metric | 2 |
| P3-T9 | Inject stream duplicates | Duplicate ID rate proof | 2 |
| P3-T10 | Profile and publish data characteristics | Complete metrics + screenshots | Proof for all 20 |

## Validation

```bash
python -m pytest -q tests/test_generator.py
python scripts/run_generator_and_profile.py --config configs/generator-config.yaml --profile ci
python scripts/run_generator_and_profile.py --config configs/generator-config.yaml --profile evidence
```

## Evidence Outputs

- Configuration snapshot and seed.
- Dataset volume and format report.
- Skew distribution chart/table.
- Approximate and exact cardinality.
- Schema-evolution null analysis.
- Offline duplicate before/after.
- Streaming burst, lateness and duplicate rates.
- Completion report: [Phase 3 generator](./reports/phase-03-260722-1635-generator.md).

## Success Criteria

- [x] Same seed/config produces identical logical records and metrics.
- [x] Every configured rate is within documented tolerance.
- [x] Stored output passes the existing typed Bronze input contracts without fixture-specific parsing; the DP1 DAG itself remains Phase 6 scope.
- [x] Profile JSON, runtime read-back, documentation, and screenshot cover all 20 generator points.

## Risks And Rollback

Keep scale configurable; CI uses small data while benchmark evidence uses a rubric-significant dataset.

## Unresolved Questions

- Minimum evidence volume expected by the instructor; rubric specifies characteristics, not a fixed row count.
