# Test Report - 2026-07-31 - Mini Coursework Evidence

## Outcome

The final evidence package is `docs/evidence/final/coursework-final-20260731T0030/`.
The complete mock rubric audit passes **45/45 criteria, 100/100 points, zero
errors**. The previous package was removed so reviewers do not select stale
evidence.

## Automated Gates

- `pytest -q`: **173 passed, 2 skipped, 0 failed**. The skips are optional
  DataHub SDK tests; live DataHub API exports and browser captures were checked
  separately.
- Ruff lint: pass.
- Ruff format: pass (133 files already formatted).
- Python compileall: pass.
- Documentation checker: pass.
- Clean-room preflight: pass; Compose configuration valid, 16 CPUs, 15,329 MiB
  RAM, and more than 9 GiB free disk.
- `git diff --check`: pass.

## Evidence Audits

- Rubric package: 51/51 artifacts, matching SHA-256 and size, integrity errors
  `[]`.
- Flink semantic audit: pass; 50,000-event contract, duplicate removal,
  checkpoint/savepoint and restart checks all true. Baseline and optimized
  screenshots show real running operator graphs.
- Spark semantic audit: pass; optimized/baseline runtime ratio 1.5595 and
  storage read ratio 2.4194, with file count reduced from 24 to 2.
- DataHub: lineage, quality assertions, contracts, owners, and dataset names
  are present in the UI export and screenshots. The onboarding modal was
  removed from the DP1 lineage capture.
- Schema and novel-idea evidence: manifest integrity, clean/tampered
  verification, and point-in-time future-event rejection all pass.

## Manual UI Verification

Playwright/Chrome captures were inspected for Airflow, DataHub, Flink, Spark,
generator, schema, and architecture evidence. The two previously detected
visual defects were corrected: DataHub DP1 lineage no longer has the overlay,
and Flink screenshots no longer show an empty dashboard shell.

## Remaining Limits

No `pytest-cov` configuration exists, so line/branch coverage was not measured;
this is not a failed mini-coursework criterion. The score is an automated
evidence/mock grade; the instructor's formal academic grade remains outside
the repository's verifiable scope.

## Runtime State

Temporary DataHub and Flink capture containers were stopped. Project Kafka,
Airflow webserver, and Airflow scheduler were started again after capture.

## Unresolved Questions

- Instructor-specific submission formatting or additional oral-demonstration
  requirements are not represented in the repository rubric and must be checked
  against the course portal before submission.
