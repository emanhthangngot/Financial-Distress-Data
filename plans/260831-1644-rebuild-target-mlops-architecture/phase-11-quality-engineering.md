---
phase: 11
title: "Phase 11: Quality engineering — coverage, EP/BVA, mutation, property-based, load"
status: pending
priority: P1
effort: "7-10 days"
dependencies: ["phase-02-data-model.md"]
softDependencies: ["phase-09-serving-edge.md"]
owns: ["tests/", "mutants/", "tests/load/", "docs/testing/", "Dockerfile*", "docker-compose*.yml"]
---

# Phase 11: Quality engineering — coverage, EP/BVA, mutation, property-based, load

## Overview

Twelve rubric rows across all three tracks are test- and packaging-engineering practices, not
architecture. They had **no owning phase** in the previous plan — grep of all ten phase files on
2026-09-01 found zero matches for `property-based`, `mutation testing`, `equivalence partitioning`
or `boundary value`, and the 2026-09-02 audit found zero AC citations for `multistage`.
This phase owns them. Source-only. **Resident cost: 0** (load testing runs inside an existing
serving window).

| Rows | Requirement | Points | Needs a cluster? |
|---|---|---|---|
| mini 2 | Docker & Docker Compose in use | 1 | no |
| mini 3 | Optimized Dockerfile (e.g. multistage build) with before/after size | 2 | no |
| ML 10; LLM 26 | Unit test coverage > 90 % with a screenshot, using fixtures | 3 | no |
| ML 11; LLM 27 | Equivalence partitioning vs boundary value analysis to parametrize test cases | 4 | no |
| ML 12; LLM 28 | Mutation testing (mutmut) to evaluate test effectiveness | 4 | no |
| ML 13; LLM 29 | Idempotency testing via property-based testing | 4 | no |
| ML 55; LLM 58 | Clean code + clean repo + demonstrable structure | 4 | no |
| ML 14; LLM 30 | Load test the data-fetch API for throughput and latency, HTML report | 4 | **yes** |
| **Total** | | **26** | 22 local / 4 cluster |

### Dependency re-baseline (2026-09-02)

The previous frontmatter required P7, P8 **and** P9 before P11 could open. That was wrong for 22 of
the 26 points: coverage, EP/BVA, mutation testing, property-based idempotency, clean-repo and the
Docker rows all run against code that exists after P2. Gating them behind the three most expensive
phases parked **22 cheap points behind ~40 days of work**, on a schedule already overcommitted
1.8-2.6×.

New rule:

- `dependencies: [P2]` — the 22 local points may start as soon as the v2 contract is frozen.
- `softDependencies: [P9]` — **only** the load test (ML 14 / LLM 30, 4 points) waits for a live
  `feature-api`. It is the last item in the phase, not the gate on the first.

Accepted cost: tests written against pre-P7/P8/P9 interfaces need touch-ups when those phases change
an API. Budgeted at 2-3 days inside the 7-10 day estimate. That is cheaper than deferring 22 points
by 40 days.

Existing surface to build on: `mutants/` with `mutmut-stats.json` and `mutmut-cicd-stats.json`,
`.hypothesis/` with a constants cache, `tests/load/`, and
`docs/evidence/docker/phase8-image-sizes.json` plus `docs/08_docker_optimization.md` for the Docker
rows (baseline numbers at tag `evidence-baseline-pre-rebuild`, P3 step 0). The LLM-track equivalents
are already `executed`; the work is largely porting the pattern to the ML track and raising rigour to
the graded threshold.

## Requirements

- Functional:
  - Coverage > 90 % on the ML-track modules, measured and captured, using pytest fixtures.
  - Test cases are **explicitly derived** from equivalence partitions and boundary values, with the
    partition table written down — the derivation is the graded artifact, not the assertion count.
  - `mutmut` runs over `src/ml/`, `src/transforms/`, `src/quality/` and reports a surviving-mutant
    count with each survivor either killed or justified.
  - Property-based idempotency tests use Hypothesis over the pipeline transforms and the prediction
    path.
  - A load test against `feature-api` produces an HTML report with throughput (req/s) and latency
    percentiles.
  - Clean-repo evidence: no dead modules, no duplicate rubric-item scripts, no orphaned `.pyc`-only
    tests, ruff and black clean.
  - Docker Compose brings the full local lakehouse up from a clean checkout; `docker compose config`
    validates.
  - Every service image uses a multistage build, with the before/after image size recorded and the
    optimization technique named.
- Non-functional: every test is deterministic and full-suite safe; no test asserts on source text or
  incidental defaults; `--strict-markers` stays on.

## Architecture

```
tests/
  unit/          per-module, fixture-driven          → coverage > 90 %
  parametrized/  EP/BVA-derived cases                → docs/testing/partitions.md
  property/      Hypothesis idempotency + invariants → transforms, prediction path
  load/          k6 or Locust against feature-api    → outputs/evidence/load/report.html
  platform/      integration + verification
mutants/         mutmut run + survivor triage        → docs/testing/mutation-report.md
```

### EP / BVA partition table (the graded artifact)

Each partition table is written to `docs/testing/partitions.md` and drives `@pytest.mark.parametrize`
directly, so the code and the document cannot drift.

| Input | Equivalence partitions | Boundary values |
|---|---|---|
| `report_period` | valid `YYYYQn`; wrong separator; quarter 0 or 5; non-numeric year | `1900Q1`, `2099Q4`, `2024Q0`, `2024Q5` |
| `total_assets` | positive; zero; negative; null | `0`, `1000`, `-1000`, `2^53`, `DECIMAL(18,0)` max |
| `known_from_ts` vs label `decision_ts` | before; equal; after; null | equal-to-the-millisecond, ±1 µs |
| `is_latest_vintage` | exactly one true per key; none true; more than one true | 1, 0, 2 |
| `company_id` on `prediction-api` | known ticker; unknown ticker; empty; oversized | 1 char, 3 chars, 4 chars, 256 chars |
| KEDA load | below threshold; at threshold; above | threshold−1, threshold, threshold+1 |

### Property-based invariants

- `bronze_to_silver` is idempotent: applying it twice equals applying it once.
- Silver dedup preserves every distinct vintage and marks exactly one `is_latest_vintage`.
- `date_key` round-trips through `calendar_date` for every date in range.
- `pit_join_features` never returns a feature whose `known_from_ts` exceeds the reference timestamp —
  the direct property form of the leakage invariant.
- `prediction-api` returns the same score for the same `(company_id, feature vintage)` pair.

## Related Code Files

- Create: `docs/testing/partitions.md`, `docs/testing/mutation-report.md`,
  `docs/testing/coverage-report.md`
- Create: `tests/property/test_transform_idempotency.py`,
  `tests/property/test_pit_invariants.py`, `tests/property/test_prediction_determinism.py`
- Create: `tests/parametrized/test_contract_boundaries.py`
- Modify: `tests/load/` — k6/Locust scenario against `feature-api`; HTML output
- Modify: `pyproject.toml` — `hypothesis`, `mutmut`, coverage thresholds, `fail_under = 90`
- Modify: `mutants/` configuration — target `src/ml/`, `src/transforms/`, `src/quality/`
- Delete: any dead module surfaced by the clean-repo audit

## Implementation Steps

1. **Coverage baseline and gap closure** (2 d) — measure current coverage per module; add
   fixture-driven unit tests until ML-track modules exceed 90 %; set `fail_under = 90` in
   `pyproject.toml` so the threshold is enforced, not merely reached once.
2. **EP/BVA derivation** (1-2 d) — write `docs/testing/partitions.md` first, then drive
   `@pytest.mark.parametrize` from it. The document is the deliverable; the tests are its consequence.
3. **Property-based tests** (1-2 d) — Hypothesis strategies for the five invariants above. The PIT
   invariant is the important one: it states the leakage property directly rather than testing one
   fixture.
4. **Mutation testing** (1 d) — run `mutmut` over the three target packages; triage every survivor;
   either add a killing test or record why the mutant is semantically equivalent. Write
   `docs/testing/mutation-report.md` with before/after survivor counts.
5. **Load test** (1 d) — run against `feature-api` inside a serving window; produce an HTML report
   with req/s and p50/p95/p99 latency; record the concurrency at which p99 crosses the ML-gate
   threshold used by the P10 AnalysisTemplate.
6. **Clean-repo audit** (1 d) — remove dead modules; merge the duplicate rubric-item scripts; delete
   orphaned test artifacts (e.g. `.pyc` files with no `.py`); confirm ruff and black clean; confirm
   `docs/architecture/low-level-design.md` matches the shipped class structure.

## Success Criteria

- [ ] AC-P11-1 **(ML 10; LLM 26)**: Engineer → runs coverage → ML-track modules report > 90 %; the
      report is captured; `pyproject.toml` enforces `fail_under = 90`
- [ ] AC-P11-2 **(ML 11; LLM 27)**: Reviewer → opens `docs/testing/partitions.md` → finds an
      equivalence-partition and boundary-value table per input, and each row maps to a
      `@pytest.mark.parametrize` case that exists
- [ ] AC-P11-3 **(ML 12; LLM 28)**: Engineer → runs `mutmut` over `src/ml/`, `src/transforms/`,
      `src/quality/` → `docs/testing/mutation-report.md` records before/after survivor counts, and
      every survivor is either killed or justified in writing
- [ ] AC-P11-4 **(ML 13; LLM 29)**: Hypothesis → runs the idempotency suite → `bronze_to_silver`
      applied twice equals once; Silver preserves every vintage with exactly one `is_latest_vintage`;
      `prediction-api` is deterministic per `(company_id, vintage)`
- [ ] AC-P11-5: Hypothesis → runs `test_pit_invariants.py` → **no generated case** returns a feature
      whose `known_from_ts` exceeds the reference timestamp; removing the vintage filter makes the
      property fail
- [ ] AC-P11-6 **(ML 14; LLM 30)**: Engineer → load-tests `feature-api` → an HTML report records
      throughput (req/s) and p50/p95/p99 latency, and names the concurrency at which p99 crosses the
      P10 AnalysisTemplate threshold
- [ ] AC-P11-7 **(ML 55; LLM 58)**: Reviewer → audits the repository → no dead modules, one
      rubric-item module, no orphaned test artifacts, ruff and black clean, and
      `docs/architecture/low-level-design.md` matches the shipped classes
- [ ] AC-P11-8: Engineer → runs `pytest tests` → full suite passes with zero skips
- [ ] AC-P11-9 **(mini 2)**: Engineer → runs `docker compose up` from a clean checkout → the local
      lakehouse (MinIO, Postgres, Spark, Airflow) reaches healthy; `docker compose config` validates
      with no warnings
- [ ] AC-P11-10 **(mini 3)**: Engineer → builds every service image → each `Dockerfile` uses a
      multistage build, and the artifact records **image size before and after** per image plus the
      technique applied (multistage, slim base, layer ordering, `.dockerignore`); the reduction
      percentage is stated per image, not as one aggregate

## Risk Assessment

**Risk:** raising coverage produces plumbing tests that assert nothing about behaviour. Signal: 90 %
reached but mutation survivors do not drop. Mitigation: AC-P11-3 uses the mutation survivor count as
the real quality measure — coverage alone can be gamed and mutation cannot. Response: replace the
plumbing tests with behavioural ones targeting surviving mutants.

**Risk:** Hypothesis finds a genuine pre-existing bug and the phase turns into a fix cycle. Signal:
a property fails on a shrunk counterexample in P2 code. Mitigation: this is the intended value —
route the fix to the owning phase's module and record it. Response: fix the source; **never**
constrain the strategy to avoid the failing input.

**Risk:** `mutmut` runtime is prohibitive on the whole tree. Signal: the run does not finish inside
the phase. Mitigation: scope to the three packages named above, which is where the graded logic
lives; `mutants/mutmut-cicd-stats.json` shows a CI-scoped run already exists. Response: narrow to
`src/transforms/` and `src/quality/` and state the scope in the report.

**Risk:** the load test perturbs a live serving window and skews P12 baseline metrics. Signal: p99
spikes in the Grafana panels used for evidence. Mitigation: run the load test **before** the P12
capture window and record the timestamps. Response: re-capture the affected panels after the load
test completes.

**Risk:** the partition table and the parametrized cases drift after a later edit. Signal: a table
row has no corresponding test. Mitigation: AC-P11-2 asserts the mapping, so drift fails the gate.
Response: generate the parametrize arguments from the table rather than transcribing them.
