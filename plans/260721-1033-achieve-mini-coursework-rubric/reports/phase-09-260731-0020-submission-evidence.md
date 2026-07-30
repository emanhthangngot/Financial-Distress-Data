# Phase 9 Submission Evidence Report

Status: **DONE**

## Delivered

- Added `scripts/verify-clean-room-setup.sh` for Docker, Compose, CPU, memory,
  disk, dependency, file, and Compose-configuration preflight checks.
- Added `scripts/run_mini_coursework_submission.py` to reject missing or
  undersized proof, run all quality gates, copy curated artifacts, create the
  rubric mapping, hash 51 artifacts, and refuse in-place package overwrite.
- Added `--require-score` and configurable index links to the rubric CLI.
- Re-captured three successful Airflow DAG pages and six DataHub lineage and
  quality pages. The DataHub captures show the real asset name, lineage nodes,
  passing volume/schema assertions, contract tab, and owner.
- Published the accepted package under
`docs/evidence/final/coursework-final-20260731T0030/`.
- Published the reviewer-facing 45-row index at `docs/evidence-index.md`.

## Correlation And Integrity

The package uses outer run ID `coursework-final-20260731T0030`. The manifest
records Git SHA `9567656b4f4f26f4277e46df2304677b9a55108f`, the combined
configuration hash, timestamps, proof types, sizes, and SHA-256 digests.
Native Spark, Flink, Airflow, generator, DataHub, and experiment identifiers
remain unchanged inside their metrics so provenance is not rewritten.

## Verification

- Clean-room preflight: pass on 16 CPUs, 15,329 MiB RAM, and 9,767 MiB free.
- Full Python suite: 173 passed, 2 skipped optional DataHub-SDK tests.
- Ruff lint: pass.
- Ruff format: 133 files checked, pass.
- Compileall, documentation links/docstrings, Compose config, and
  `git diff --check`: pass.
- Curated screenshot ignore check: pass; final PNG/JPG exceptions are explicit
  and the changes remain unstaged pending the user's commit decision.
- Manifest integrity: 51/51 artifacts present with matching hash and size.
- Rubric audit: 45/45 accepted, 100/100, zero failed criteria, zero errors.
- Runtime restored: PostgreSQL, MinIO, Kafka, Airflow webserver, and Airflow
  scheduler running after the DataHub capture window.

## Review Boundary

This is a verified automated and manual mock grade, not a guarantee of the
instructor's final academic grade. The package preserves measured results and
does not rewrite component execution identifiers.
