---
phase: 6
title: "Encode test cost classes as pytest markers"
status: pending
priority: P2
effort: "1-2h"
dependencies: [1]
---

# Phase 6: Encode test cost classes as pytest markers

## Overview

AGENTS.md documents a "Time-Costly" test class in prose. No marker encodes it, so
the only selection tool is `-k` plus tribal knowledge. Turn the prose into
markers, assigned from measured durations rather than from the prose itself.

## Requirements

- Functional: `pytest -m "not slow"` runs only tests that need no external
  service and completes without a Docker stack or a Postgres binary.
- Functional: markers are registered in `pyproject.toml`, so `--strict-markers`
  catches a typo instead of silently selecting nothing.
- Non-functional: no test is moved, renamed, skipped, or has an expected value
  changed. Markers add selection, never change outcomes.
- Non-functional: the default `pytest tests` invocation still runs everything —
  AGENTS.md's definition of done is unchanged.

## Architecture

**Do not split `tests/` into directories.** Markers give the same selection power
with zero import-path or `testpaths` churn. Directory moves would also break the
relative-path assertions in `tests/test_naming_convention.py`,
`tests/test_sql_contract_runner.py`, and the `REPO_ROOT = parents[1]` idiom used
across the suite.

Proposed taxonomy — three markers, everything unmarked is fast-by-default:

| Marker | Means | Known members |
|---|---|---|
| `services` | needs the running `docker compose` stack (Kafka/MinIO/Postgres/Airflow) | `tests/test_real_e2e_contracts.py` |
| `postgres` | needs local `initdb`/`pg_ctl` binaries; spins an ephemeral cluster per session | `tests/platform/product/*` (see `tests/platform/product/conftest.py`) |
| `slow` | >2s wall clock, no external dependency | assigned from measurement, step 2 |

`services` and `postgres` also imply `slow`, so `-m "not slow"` is the single
"give me the fast loop" selector. Apply both markers explicitly rather than
inventing marker inheritance.

**One availability gate already exists; markers do not replace it.**
`tests/platform/product/conftest.py:56-58` skips that suite when `initdb`/`pg_ctl`
are absent, unless `PHASE2_REQUIRE_PG=1` — which `.github/workflows/ci.yml` sets
in the `test` job specifically so a missing Postgres fails CI instead of silently
skipping the authorization rules. Validation session 1 decided to keep both, as
separate mechanisms with separate jobs:

| Mechanism | Answers | Owner |
|---|---|---|
| the `PHASE2_REQUIRE_PG` skip | "can this machine run it at all?" | availability |
| the `postgres` marker | "do I want to run it right now?" | selection |

Do not delete the skip, and do not make the marker conditional on the env var.
A developer on a machine without `initdb` must keep getting skips from plain
`pytest`, and CI must keep getting a hard failure.

**A prose claim to verify, not inherit.** AGENTS.md lists
`tests/test_flink_integration.py` as time-costly requiring `ENABLE_FLINK=1` and
the flink compose profile. The file's own code contradicts that: it uses
`monkeypatch.setenv("ENABLE_FLINK", "1")` and patches `urllib` responses
(`_fake_urlopen_response`), and its docstring says it deliberately avoids
`requests` so no live service is needed. Step 2 measures it. If it is fast and
hermetic, it gets no marker and AGENTS.md's time-costly list is corrected — the
prose was wrong, and a marker that repeats a wrong claim is worse than no marker.

## Related Code Files

- Modify: `pyproject.toml` (`[tool.pytest.ini_options]`: `markers`, `addopts`)
- Modify: `tests/test_real_e2e_contracts.py` (module-level `pytestmark`)
- Modify: `tests/platform/product/conftest.py` (apply markers to that package)
- Modify: `AGENTS.md` "Time-Costly" section (replace `-k <name>` guidance with
  marker selectors; correct the Flink claim if step 2 disproves it)
- Modify: `README.md` test-command section, if it documents pytest invocations

## Implementation Steps

1. Register the markers so `--strict-markers` is usable:
   ```toml
   [tool.pytest.ini_options]
   pythonpath = ["."]
   testpaths = ["tests"]
   addopts = "--strict-markers"
   markers = [
     "slow: takes more than ~2s; excluded by the fast loop",
     "services: requires the docker compose stack to be running",
     "postgres: requires local initdb/pg_ctl binaries",
   ]
   ```
2. **Measure before marking.** Get real durations for the whole suite:
   ```bash
   .venv/bin/python -m pytest tests --durations=0 -q > /tmp/durations.txt
   ```
   Everything above ~2s is a `slow` candidate. Record the measured list in the
   PR description — the marker assignment must be traceable to this run, not to
   AGENTS.md's prose.
3. Mark the service-dependent modules at module level:
   ```python
   pytestmark = [pytest.mark.services, pytest.mark.slow]
   ```
   in `tests/test_real_e2e_contracts.py`.
4. Mark the Postgres-cluster package. Add a `pytest_collection_modifyitems`
   hook to the existing `tests/platform/product/conftest.py` that stamps
   `pytest.mark.postgres` and `pytest.mark.slow` on every item in that package —
   one place, no per-file churn, cannot drift as files are added. Leave the
   `PHASE2_REQUIRE_PG` skip at lines 56-58 of that same file untouched; the two
   mechanisms are independent (see Architecture).
5. Apply `slow` to any remaining module the step-2 measurement flagged. Do not
   mark a test slow because it looks slow.
6. Correct AGENTS.md's "Time-Costly" section to name the selectors instead of
   file lists:
   ```bash
   .venv/bin/python -m pytest tests -m "not slow"   # fast loop while iterating
   .venv/bin/python -m pytest tests                 # full suite, definition of done
   ```
   Keep the existing warning that `--include-services` and the real-e2e runners
   need `docker compose up` first. If step 2 disproved the Flink claim, remove
   `tests/test_flink_integration.py` from the time-costly list and say why in the
   commit body.
7. Verify:
   ```bash
   .venv/bin/python -m pytest tests -m "not slow" -q       # no container, no initdb
   .venv/bin/python -m pytest tests -m "postgres" -q       # only the RLS suite
   .venv/bin/python -m pytest tests -q                     # unchanged total
   .venv/bin/python scripts/run_stage1_quality_gates.py
   ```
   The counts from run 1 and run 2 must sum to run 1's total plus run 2's total
   without overlap; a test in both selections means a marker was applied twice.

## Success Criteria

- [ ] Developer -> runs `pytest tests -m "not slow"` -> gets a fast loop that
      needs no Docker stack and no Postgres binaries, and it passes.
- [ ] Developer -> mistypes a marker (`-m "not sloow"`) -> `--strict-markers`
      surfaces it instead of silently running nothing.
- [ ] `pytest tests` -> same collected count and same pass result as the phase-1
      baseline. Markers select; they never skip.
- [ ] Reader -> opens AGENTS.md "Time-Costly" -> finds runnable selectors, and
      every file still listed there was confirmed costly by the step-2
      measurement.
- [ ] Developer without `initdb` on PATH -> runs plain `pytest tests` -> still
      gets skips from the `PHASE2_REQUIRE_PG` gate, not errors; CI with
      `PHASE2_REQUIRE_PG=1` still fails hard on a missing Postgres.
- [ ] `scripts/run_stage1_quality_gates.py` -> same result as the phase-1 baseline.

## Risk Assessment

- Risk: `--strict-markers` in `addopts` breaks an existing unregistered marker.
  Mitigation: the current suite uses only `pytest.mark.parametrize` (built in);
  step 7's full run confirms.
- Risk: the collection hook in `tests/platform/product/conftest.py` also stamps
  items from sibling packages. Mitigation: the hook only receives items from its
  own directory subtree; assert that with the step-7 `-m "postgres"` count
  matching the file count in that package.
- Risk: markers become a way to hide a failing test. Mitigation: the default
  invocation is unchanged and remains the definition of done; `-m "not slow"` is
  an iteration convenience only, never a gate.
- Rollback: `git revert`; markers are additive metadata with no behavioral effect
  when unused.
