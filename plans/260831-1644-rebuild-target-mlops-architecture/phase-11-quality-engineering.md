---
phase: 11
title: "Phase 11: Quality, functional eval and regression gates"
status: pending
priority: P1
effort: "Re-estimate from unfinished ACs; historical baseline 7-10 days + eval-fixture authoring"
dependencies: ["phase-02-data-model.md"]
softDependencies: ["phase-04-data-plane.md", "phase-07-ml-track.md", "phase-08-llm-agent-track.md", "phase-09-serving-edge.md"]
owns: ["tests/", "tests/eval/", "mutants/", "tests/load/", "docs/testing/", "Dockerfile*", "docker-compose*.yml"]
---

# Phase 11: Quality, functional eval and regression gates

## Overview

Ten rubric rows across all three tracks are test- and packaging-engineering practices, not
architecture. They had **no owning phase** in the previous plan — grep of all ten phase files on
2026-09-01 found zero matches for `property-based`, `mutation testing`, `equivalence partitioning`
or `boundary value`, and the 2026-09-02 audit found zero AC citations for `multistage`.
This phase owns them, **plus** the session-added functional-eval and regression-gate scope from the
master plan's decision ledger and scheduling section
(`plan.md:39,100-101`): P11 co-owns the human-reviewed evaluation baseline for RAG with P8, defines
the eval fixtures and metrics P8/P9 consumer checks run against, and supplies P10 its release
subgate result — not a reciprocal whole-phase dependency in either direction. Source-only for the
quality-engineering rows. **Resident cost: 0** (load testing runs inside an existing serving window;
the human-reviewed RAG eval runs against whatever provider P0 `G5-providers` cleared, at zero spend).

### Functional eval and regression gates (session addition, 2026-09-10)

- **Eval fixtures and metrics, defined early.** P11 authors `tests/eval/` — a fixed development
  corpus, expected-citation set and scoring rubric — **before** P8's parity pilot needs it
  (`phase-02-data-model.md` dependency chain notwithstanding; this work starts once P2's contract is
  frozen, not after P8 exists). P8's pilot-vs-current-path comparison and its clean-cutover decision
  both score against this fixture, not an ad hoc one P8 invents itself.
- **Human-reviewed RAG eval, co-owned with P8.** P11 owns the scoring harness and the reviewer
  rubric (citation validity, groundedness, refusal-on-missing-context); P8 owns the RAG pipeline
  under evaluation. Neither phase substitutes an automated proxy metric for the human review the
  rubric names.
- **Regression gates for P2's M1–M11 fixes.** The AC-P2-26…AC-P2-38 regression cases P2 wrote to
  fail before its fix and pass after are wired into this phase's `pytest tests` run, so a later edit
  that reintroduces a P2 defect fails here, not silently.
- **P10 release subgate.** P11 reports pass/fail per eval fixture and per regression case to P10's
  evidence-gated release; P10 blocks the release artifact it owns on a P11 fail, but P11 does not
  block on P10 — the dependency runs one way, per `plan.md:101`.

| Rows | Requirement | Points | Needs a cluster? |
|---|---|---|---|
| mini 2 | Docker & Docker Compose in use | 1 | no |
| mini 3 | Optimized Dockerfile (e.g. multistage build) with before/after size | 2 | no |
| ML 11; LLM 27 | Equivalence partitioning vs boundary value analysis to parametrize test cases | 4 | no |
| ML 12; LLM 28 | Mutation testing (mutmut) to evaluate test effectiveness | 4 | no |
| ML 13; LLM 29 | Idempotency testing via property-based testing | 4 | no |
| ML 55; LLM 58 | Clean code + clean repo + demonstrable structure | 4 | no |
| ML 14; LLM 30 | Load test the data-fetch API for throughput and latency, HTML report | 4 | **yes** |
| **Total (in scope)** | | **23** | 19 local / 4 cluster |

### Dependency re-baseline (2026-09-02)

The previous frontmatter required P7, P8 **and** P9 before P11 could open. That was wrong for the
in-scope local quality points: EP/BVA, mutation testing, property-based idempotency, clean-repo and
the Docker rows all run against code that exists after P2. Gating them behind the three most
expensive phases parked cheap points behind ~40 days of work.

New rule:

- `dependencies: [P2]` — the 19 local quality-engineering points may start as soon as the v2
  contract is frozen; nothing in this phase blocks on P4/P7/P8/P9 existing.
- `softDependencies: [P4, P7, P8, P9]` — **refined 2026-09-10**, not reverted: P11 *authors*
  `tests/eval/` and the load-test harness against P2 as soon as it opens (no wait), but four
  **consumer checks** cannot execute until their producer exists — the load test (ML 14 / LLM 30)
  needs a live `feature-api` from P9; the eval-fixture score (AC-P11-11/12) needs P8's parity
  pilot to run against; the P2 regression wiring's Spark-side leg (AC-P11-13) closes once P4
  mirrors P2 (`phase-04-data-plane.md` §Session decisions, AC-P4-30); and the
  `prediction-api`-determinism property (AC-P11-4) needs a real promoted model from P7's MLflow
  registry, not a mock, to be a meaningful assertion. These four are `softDependencies`, not the
  phase's `dependencies`: each can go `blocked/unverified` independently without stalling the
  other points, the same escape hatch the original re-baseline introduced for the load test alone.

Accepted cost: tests written against pre-P4/P7/P8/P9 interfaces need touch-ups when those phases
change an API. Budgeted at 2-3 days inside the 7-10 day estimate. That is cheaper than deferring
22 points by 40 days.

Existing surface to build on: `mutants/` with `mutmut-stats.json` and `mutmut-cicd-stats.json`,
`.hypothesis/` with a constants cache, `tests/load/`, and
`docs/evidence/docker/phase8-image-sizes.json` plus `docs/08_docker_optimization.md` for the Docker
rows (baseline numbers at tag `evidence-baseline-pre-rebuild`, P3 step 0). The LLM-track equivalents
are already `executed`; the work is largely porting the pattern to the ML track and raising rigour to
the graded threshold.

## Requirements

- Functional:
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

- Create: `docs/testing/partitions.md`, `docs/testing/mutation-report.md`
- Create: `tests/property/test_transform_idempotency.py`,
  `tests/property/test_pit_invariants.py`, `tests/property/test_prediction_determinism.py`
- Create: `tests/parametrized/test_contract_boundaries.py`
- Modify: `tests/load/` — k6/Locust scenario against `feature-api`; HTML output
- Modify: `pyproject.toml` — `hypothesis`, `mutmut`
- Modify: `mutants/` configuration — target `src/ml/`, `src/transforms/`, `src/quality/`
- Delete: any dead module surfaced by the clean-repo audit

## Implementation Steps

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
- [ ] AC-P11-11 **(session addition — eval fixtures)**: P8 engineer → runs the parity pilot →
      scores against `tests/eval/`'s fixed development corpus and expected-citation set, authored
      by P11 before the pilot exists; P8 does not invent its own scoring fixture
- [ ] AC-P11-12 **(session addition — human-reviewed RAG eval)**: Reviewer → runs the P11 scoring
      harness against P8's RAG pipeline → produces a human-reviewed citation-validity and
      groundedness score, at zero spend under P0 `G5-providers`; no automated proxy metric is
      substituted for the required human review
- [ ] AC-P11-13 **(session addition — P2 regression wiring)**: Engineer → runs `pytest tests` →
      AC-P2-26…AC-P2-38's regression cases execute as part of this phase's suite; reintroducing any
      of M1–M11 fails the run here, not only in an isolated P2-only invocation
- [ ] AC-P11-14 **(session addition — P10 subgate)**: P10 release job → reads P11's per-fixture and
      per-regression-case pass/fail record → blocks the release artifact on any P11 fail; a P10
      fail never blocks P11's own suite (one-way dependency, `plan.md:101`)

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

## Rubric Citations (phase-03 R-12 closure, appended 2026-09-05)

Every rubric row this phase owns per `docs/rubric-matrix-unified.csv`'s `owning_phase` column, cited so `scripts/verify_rubric_coverage.py` can resolve ownership to an assertion (R-12). Each line names the row's real `rubric_id`, its stated requirement, and its proof artifact/deliverable — the row's own matrix columns, not invented text. Rows whose capability is not yet implemented are forward specs, matching this file's other `AC-P11-*` entries.

- AC-P11-RUBRIC-1: `LLM-repository-design-clean-code-clean-repo-demonstr` — platform_operator -> delivers "Repository Design — Clean Code + clean repo + demonstrate the use of Design Pattern" -> Capture màn hình thể hiện Design Pattern đã được sử dụng trong code (evidence: `docs/platform/evidence/llm/LLM-repository-design-clean-code-clean-repo-demonstr.md`)
- AC-P11-RUBRIC-2: `LLM-validation-verification-c-s-d-ng-k-thu-t-equivalence-p` — llm_engineer -> delivers "Có sử dụng kỹ thuật equivalence partitioning vs boundary value analysis khi thiết kế test cases để parametrize.; (Cái này chưa được dạy, như..." -> Capture màn hình để thể hiện đã sử dụng các kỹ thuật này (evidence: `docs/platform/evidence/llm/LLM-validation-verification-c-s-d-ng-k-thu-t-equivalence-p.md`)
- AC-P11-RUBRIC-3: `LLM-validation-verification-c-s-d-ng-mutation-testing-nh-g` — llm_engineer -> delivers "Có sử dụng mutation testing để đánh giá hiệu quả của các test (cái này đã dạy ở lớp rồi nha cả nhà, là cái https://mutmut.readthedocs.io/)...." -> Capture màn hình để thể hiện đã sử dụng các kỹ thuật này (evidence: `docs/platform/evidence/llm/LLM-validation-verification-c-s-d-ng-mutation-testing-nh-g.md`)
- AC-P11-RUBRIC-4: `LLM-validation-verification-idempotency-testing-s-d-ng-pro` — llm_engineer -> delivers "Idempotency testing sử dụng property-based testing (chuyên để tìm ra cái test case có thể tạo ra bug), ví dụ, để kiểm tra xem model predicti..." -> Capture màn hình để thể hiện đã sử dụng các kỹ thuật này (evidence: `docs/platform/evidence/llm/LLM-validation-verification-idempotency-testing-s-d-ng-pro.md`)
- AC-P11-RUBRIC-5: `LLM-validation-verification-load-test-the-web-api` — data_engineer -> delivers "Load test the Web API (cái Web API kéo dữ liệu) to understand throughput (req/s) and latency; (generate a html file with locust as SLA)" -> Capture màn hình HTML output (evidence: `docs/platform/evidence/llm/LLM-validation-verification-load-test-the-web-api.md`)
- AC-P11-RUBRIC-6: `LLM-validation-verification-validation-verification` — llm_engineer -> delivers "Validation & Verification" -> Capture màn hình đã chạy test với test coverage thoả mãn yêu cầu (evidence: `docs/platform/evidence/llm/LLM-validation-verification-validation-verification.md`)
- AC-P11-RUBRIC-7: `ML-repository-design-clean-code-clean-repo-demonstr` — platform_operator -> delivers "Repository Design — Clean Code + clean repo + demonstrate the use of Design Pattern" -> Capture màn hình thể hiện Design Pattern đã được sử dụng trong code (evidence: `docs/platform/evidence/ml/ML-repository-design-clean-code-clean-repo-demonstr.md`)
- AC-P11-RUBRIC-8: `ML-validation-verification-c-s-d-ng-k-thu-t-equivalence-p` — ml_engineer -> delivers "Có sử dụng kỹ thuật equivalence partitioning vs boundary value analysis khi thiết kế test cases để parametrize.; (Cái này chưa được dạy, như..." -> Capture màn hình để thể hiện đã sử dụng các kỹ thuật này (evidence: `docs/platform/evidence/ml/ML-validation-verification-c-s-d-ng-k-thu-t-equivalence-p.md`)
- AC-P11-RUBRIC-9: `ML-validation-verification-c-s-d-ng-mutation-testing-nh-g` — ml_engineer -> delivers "Có sử dụng mutation testing để đánh giá hiệu quả của các test (cái này đã dạy ở lớp rồi nha cả nhà, là cái https://mutmut.readthedocs.io/)...." -> Capture màn hình để thể hiện đã sử dụng các kỹ thuật này (evidence: `docs/platform/evidence/ml/ML-validation-verification-c-s-d-ng-mutation-testing-nh-g.md`)
- AC-P11-RUBRIC-10: `ML-validation-verification-idempotency-testing-s-d-ng-pro` — ml_engineer -> delivers "Idempotency testing sử dụng property-based testing (chuyên để tìm ra cái test case có thể tạo ra bug), ví dụ, để kiểm tra xem model predicti..." -> Capture màn hình để thể hiện đã sử dụng các kỹ thuật này (evidence: `docs/platform/evidence/ml/ML-validation-verification-idempotency-testing-s-d-ng-pro.md`)
- AC-P11-RUBRIC-11: `ML-validation-verification-load-test-the-web-api` — data_engineer -> delivers "Load test the Web API (cái Web API kéo dữ liệu) to understand throughput (req/s) and latency; (generate a html file with locust as SLA)" -> Capture màn hình HTML output (evidence: `docs/platform/evidence/ml/ML-validation-verification-load-test-the-web-api.md`)
- AC-P11-RUBRIC-12: `ML-validation-verification-validation-verification` — ml_engineer -> delivers "Validation & Verification" -> Capture màn hình đã chạy test với test coverage thoả mãn yêu cầu (evidence: `docs/platform/evidence/ml/ML-validation-verification-validation-verification.md`)
- AC-P11-RUBRIC-13: `mini-02-engineering-fundamentals-docker-docker-compose-c-s` — data_engineer -> delivers "Có sử dụng Docker & Docker Compose" -> Document Docker image đã reduce từ bao nhiêu tới bao nhiêu thông qua phương pháp optimize gì (evidence: `docs/submission/rubric-(mini-coursework)/engineering_fundamentals.md`)
- AC-P11-RUBRIC-14: `mini-03-engineering-fundamentals-docker-docker-compose-opt` — data_engineer -> delivers "Optimize Dockerfile (ví dụ multistage build)" -> Optimize Dockerfile (ví dụ multistage build) (evidence: `docs/submission/rubric-(mini-coursework)/engineering_fundamentals.md`)
