# Configurable Problem Generator

## Purpose

`src/generator/` produces deterministic batch source files and Kafka-ready price events with the data characteristics required by rubric rows R04-R13. It supplements the small `VnstockFixtureAdapter`; it does not replace live-source adapter boundaries.

## Run

CI profile:

```bash
python scripts/run_generator_and_profile.py \
  --config configs/generator-config.yaml \
  --profile ci
```

Evidence profile:

```bash
python scripts/run_generator_and_profile.py \
  --config configs/generator-config.yaml \
  --profile evidence
```

Add `--publish-minio` and `--publish-kafka` in an environment with runtime dependencies and reachable services. From the host Compose network, override Kafka with `--kafka-bootstrap-servers localhost:9094` and set `MINIO_ENDPOINT=localhost:9000`.

## Configuration

The typed YAML contract controls:

- seed and correlated `run_id`
- companies, quarters, and independently measured high-cardinality IDs
- dominant sector and exchange rates
- offline duplicate rate and schema change quarter
- event volume, window size, baseline rate, burst window, and multiplier
- late, out-of-order, and streaming duplicate rates
- maximum event-time offsets and output locations

Unknown, missing, invalid-rate, invalid-volume, and impossible burst settings fail before generation.

## Offline Contracts

The generator writes `companies`, `financial_statements`, and `market_prices_daily`. All generated rows pass `configs/schema-contracts.yaml`; measurement-only columns are ignored when the typed Bronze contract is materialized.

- Skew is deterministic by company index, not statistical luck.
- `high_cardinality_id` has the exact configured cardinality.
- Financial schema v1 has null `operating_cash_flow`, `retained_earnings`, and `statement_type`; v2 populates them.
- Company duplicate rows retain the same business key and source ID but have a later `created_ts`, allowing Silver latest-row deduplication to be measured.
- Local output uses replayable JSONL. Runtime MinIO output uses Parquet under `source/generator/run_id=<run_id>/offline/`.

## Streaming Contracts

Events use topic `financial.price_events` and the existing event fields. The finite replay schedule is ordered by `ingest_timestamp` and contains:

- one configured burst window
- configured event-time lateness
- configured out-of-order events
- duplicates with the same deterministic `event_id`

Flags such as `is_late` and `is_injected_duplicate` are generator truth labels used to evaluate later Flink processing. They are not inferred processing results.

## Evidence Run

Run `generator-evidence-v1`, seed `42`, produced:

| Characteristic | Measured result |
|---|---:|
| Base companies | 10,000 |
| Financial statements | 80,000 |
| Market prices | 10,000 |
| Stream events | 50,000 |
| Dominant sector | 60.00% |
| Dominant exchange | 70.00% |
| Exact high-cardinality IDs | 10,000 |
| Schema v1 / v2 rows | 40,000 / 40,000 |
| Offline duplicates | 1.9992% |
| Burst peak / baseline | 10.05x |
| Late events | 5.002% |
| Out-of-order events | 3.994% |
| Stream duplicates | 1.500% |

Artifacts:

- [effective config](evidence/generator/effective-config.json)
- [profile JSON](evidence/generator/profile.json)
- [profile HTML](evidence/generator/profile.html)
- [source manifest](evidence/generator/source-manifest.json)
- [runtime validation](evidence/generator/runtime-validation.json)
- [profile screenshot](evidence/screenshots/generator-profile.png)

## Deterministic Replay

The same typed config and seed reproduce identical logical JSON serialization hashes. Storage encodings may differ across library versions, so correctness uses row counts and logical hashes rather than raw Parquet byte hashes.
