# Phase 3 Completion Report

Date: 2026-07-22
Status: Completed

## Delivered

- Typed YAML config with CI/evidence profiles, seed, scale, rate, timing, schema, and output controls.
- Deterministic offline datasets for company, financial statement, and market price Bronze contracts.
- Measurable sector/exchange skew, exact high-cardinality IDs, schema v1/v2 evolution, and duplicate injection.
- Kafka-ready deterministic price events with burst, late, out-of-order, and duplicate truth labels.
- Logical hashing, metrics profile, HTML evidence page, local JSONL writer, MinIO Parquet writer, and Kafka publisher.
- Local CLI plus config/profile/manifest/runtime-validation/screenshot evidence package.

## Evidence Metrics

| Metric | Result |
|---|---:|
| Base companies | 10,000 |
| Financial statements | 80,000 |
| Market prices | 10,000 |
| Stream events | 50,000 |
| Sector / exchange skew | 60% / 70% |
| Exact high-cardinality IDs | 10,000 |
| Schema v1 / v2 | 40,000 / 40,000 |
| Offline duplicates | 1.9992% |
| Burst ratio | 10.05x |
| Late / out-of-order | 5.002% / 3.994% |
| Streaming duplicates | 1.500% |

Final logical digest: `fcc33aa5b9855609807efef4f2387c004242725301e8a571d408b03e01396293`.

## Runtime Proof

- MinIO prefix: `source/generator/run_id=generator-evidence-v1/`.
- Six source/config/profile objects, 4,594,263 bytes.
- PyArrow read-back: companies 10,204, statements 80,000, prices 10,000.
- Kafka published 50,000 evidence events; independent partition offsets totaled 50,212 including 212 pre-existing/CI probe events.
- All generated batch rows pass `configs/schema-contracts.yaml`.
- Screenshot: `docs/evidence/screenshots/generator-profile.png`.

## Verification

| Gate | Result |
|---|---|
| Generator tests | 7 passed |
| Full test suite | 138 passed |
| Ruff | Passed |
| Python compileall | Passed |
| Docker Compose validation | Passed |
| Whitespace validation | Passed |
| Black | 102 files unchanged; process required timeout after successful result due known exit hang |
| CI generator CLI | Passed |
| Evidence generator CLI | Passed |
| MinIO/Kafka runtime publication | Passed |
| MinIO row-count and manifest read-back | Passed |

## Review Result

No Critical or Important findings. Existing collector APIs and typed Bronze schemas remain unchanged. Generator metadata is additive and ignored during typed Bronze materialization.

R04-R13 are implemented and runtime-verified. They are not yet marked globally accepted because Phase 9 must rebuild one clean correlated manifest for the entire 100-point submission.

## Unresolved Questions

- Instructor minimum evidence volume is unspecified. Current evidence uses 10,000 companies and 50,000 stream events; scale remains configurable.
