---
title: "Architecture hygiene before phase 3"
description: "Repair structural defects and ownership ambiguity in the repo layout before the GitOps/AWS evidence platform phase starts adding a second infrastructure surface."
status: pending
priority: P1
effort: "1-1.5 focused workdays"
branch: dev
tags: [architecture, refactor, infra, phase2, pre-phase3]
blockedBy: []
blocks: [260802-1037-unified-phase2-ml-llm-gitops]
created: 2026-08-06
---

# Architecture hygiene before phase 3

## Overview

The repo currently carries two ecosystems (Python data platform + pnpm TS
monorepo) under one root. The TS half is production-shaped. The Python half has
accumulated structural defects that a folder audit surfaced on 2026-08-06:

- The Flink service **cannot run its own job**. `docker-compose.yml:170,189` uses
  stock `apache/flink:1.19-java17` (no Python, no Kafka connector) and mounts
  `./src/streaming/flink/jobs`, which contains only a `README.md`. The actual job
  is at `flink/jobs/price_event_job.py`, unmounted. The Dockerfile that would
  make it work (`infra/flink/Dockerfile`, PyFlink 1.20.3 + kafka connector jar)
  is orphaned — nothing in compose builds it. `docs/flink-stream-processing.md`
  documents the working setup that compose no longer provides.
- `src/generator/` and `src/generators/` both export `GeneratorConfig`,
  `load_generator_config`, and `StreamingConfig` — different schemas, different
  source YAML, one letter apart. Wrong-import trap with no type error.
- `init/` and `sql/` are unowned container-bootstrap roots at repo top level,
  right before phase 3 introduces formal resource-ownership rules.
- Python has no declared package boundary: `pyproject.toml` ships no packages and
  relies on `pythonpath = ["."]`. Not installable, so phases 5-6 cannot
  `pip install` this repo into a model/agent container image.
- `tests/` is 40 flat files. AGENTS.md documents a "Time-Costly" test class
  (Docker/Kafka/Flink) in prose, but nothing in the tree or in pytest encodes it.

This plan fixes exactly those five. It changes no Phase 1 pipeline semantics, no
data contract, no Phase 2 product code, and adds no new capability.

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | Flink profile can actually run its job from one unambiguous source location | P1 |
| 2 | No two importable Python modules export the same name with different meaning | P1 |
| 3 | Every top-level directory has one named owner before phase 3 defines ownership rules | P2 |
| 4 | The Python source tree is an installable package, ready to containerize in phases 5-6 | P2 |
| 5 | Test cost classes are machine-selectable, not prose in AGENTS.md | P2 |

## Phases

| # | Phase | Estimate | Status |
|---|-------|----------|--------|
| 1 | [Capture the green baseline](./phase-01-start.md) | 0.5h | Pending |
| 2 | [Unify Flink job home and repair the dead compose mount](./phase-02-unify-flink-job-home-and-repair-the-dead-compose-mount.md) | 2-3h | Pending |
| 3 | [Resolve the generator package collision](./phase-03-resolve-the-generator-package-collision.md) | 2-3h | Pending |
| 4 | [Consolidate container bootstrap under infra](./phase-04-consolidate-container-bootstrap-under-infra.md) | 1-2h | Pending |
| 5 | [Declare the Python package boundary](./phase-05-declare-the-python-package-boundary.md) | 2h | Pending |
| 6 | [Encode test cost classes as pytest markers](./phase-06-encode-test-cost-classes-as-pytest-markers.md) | 1-2h | Pending |

Phase 1 must run first so every later phase has a diff baseline. Phases 2-6 are
independent of each other and land as **one PR per phase** (validation session 1)
— five small PRs on `fix/` and `chore/` branches, each independently revertable.
This keeps the Flink repair, which cannot be fully verified without booting the
opt-in profile, isolated from the low-risk phases behind it.

## Non-Goals (deliberately rejected)

| Rejected | Why |
|---|---|
| Renaming `docs/phase2/`, `tests/phase2/`, `dags/phase2/` to domain names | Phase numbers in those paths encode the AGENTS.md Phase-1-don't-touch boundary and gate CI/rubric checks. Renaming churns hundreds of refs to buy naming purity. Revisit after coursework ends, never mid-plan. |
| Moving `images/` to `docs/assets/` | 4 files, ~10 doc references, plus `scripts/_rubric_items.py` evidence-path assertions and generated `docs/evidence/rubric_coverage.json`. Zero functional gain, non-zero chance of breaking a rubric evidence check. |
| Consolidating the 8 `apps/web/playwright.*.config.ts` files | Each is wired to a named CI command in `.github/workflows/ci.yml` and package scripts. Cosmetic gain, real risk in the one part of the repo that is already clean. |
| Splitting `tests/` into `unit/`/`integration/`/`e2e/` directories | Markers give the same selection power (phase 6) with zero import-path churn. Directory moves would break `testpaths` and every relative fixture path. |
| Moving Python planes into `services/<name>/` | Real production shape, but a whole-repo import rewrite. Phase 5 gets the installability benefit for ~10% of the cost. |
| Adding `terraform/`, `charts/`, `argocd/` here | AGENTS.md: that platform lives in the separate `financial-distress-gitops` control repo. |

## Constraints

- Phase 1 pipeline behavior, DAG IDs, task IDs, Gold contracts, and DQ semantics
  must not change. AGENTS.md "Don't Touch" applies in full.
- Never edit a test's expected value to make it pass. If a move breaks a test,
  the move is wrong.
- Do not hand-edit `warehouse.db`, `outputs/**`, or `docs/evidence/**` —
  regenerate via the producing script.
- Flink stays opt-in (`flink` compose profile + `ENABLE_FLINK=1`); nothing in
  this plan makes it start on plain `docker compose up`.
- Definition of done for every phase:
  `.venv/bin/python scripts/run_stage1_quality_gates.py` passes.

## Success Criteria

- [ ] Maintainer -> greps for `price_event_job.py` -> finds exactly one source
      location, and the compose mount that delivers it to the container.
- [ ] Operator -> runs the `flink` profile per `docs/flink-stream-processing.md`
      -> the documented command path exists inside the container and PyFlink +
      the Kafka connector are present.
- [ ] Developer -> imports `GeneratorConfig` -> gets exactly one class, or an
      unambiguously named alternative; no two modules one letter apart export it.
- [ ] Maintainer -> lists tracked top-level directories -> every one maps to a
      named owner in `docs/architecture/` or the root README.
- [ ] CI -> runs `pip install -e .` then `python -c "import src.ml.contracts"`
      from a directory other than the repo root -> succeeds.
- [ ] Developer -> runs `pytest -m "not slow"` -> gets only tests that need no
      Docker stack, and the run completes without a live container.
- [ ] Maintainer -> runs `scripts/run_stage1_quality_gates.py` after every phase
      -> identical pass result to the phase-1 baseline.

## Risks and Rollback

- Risk: a file move silently breaks a rubric evidence path check.
  Mitigation: phase 1 captures `scripts/run_stage1_quality_gates.py` and rubric
  audit output as the baseline; every phase diffs against it.
- Risk: the Flink repair cannot be fully verified without booting the profile
  (time-costly per AGENTS.md). Mitigation: `docker compose config` proves the
  wiring statically; a live run is an explicit opt-in step the operator
  authorizes, and phase 2 is not marked done on a live-run claim that was
  never executed.
- Rollback: every phase is a self-contained commit on a `chore/` or `fix/`
  branch. `git revert` restores prior layout; no migration, no persisted state,
  no external system touched.

## Open Questions

None. The Flink version question was resolved in validation session 1.

## Validation Log

### Session 1 — 2026-08-06

**Trigger:** `/ak:plan validate` before implementation.

#### Verification Results

- **Tier:** Full (6 phases -> all 4 roles)
- **Claims checked:** 41
- **Verified:** 37 | **Failed:** 4 | **Unverified:** 0

Failures, all surfaced as interview questions and now resolved:

1. **[Contract Verifier] phase 3 missed a caller.** `scripts/_rubric_items.py:132`
   cites `src/generators/config_loader.py` as the evidence path for scored rubric
   row 7 ("Generator is driven by configuration", 2 pts), and its `_exists_any`
   fallback `src/generator/config.yaml` does not exist. The move would have
   silently dropped 2 rubric points. Found by path-string grep; an import-only
   `src\.generators` grep misses it.
2. **[Fact Checker] phase 5 named a nonexistent CI job.** The plan said "the
   stage-1 job of `.github/workflows/ci.yml`". The workflow is *named*
   "Stage 1 CI"; the job id is `test`. A second job `contracts` covers the pnpm
   workspace.
3. **[Scope Auditor] phase 6 understated existing state.** The plan said nothing
   in pytest encodes the time-cost class. `tests/phase2/product/conftest.py:56-58`
   already gates that suite on `initdb` availability, with
   `PHASE2_REQUIRE_PG=1` set in CI to convert a skip into a failure.
4. **[Fact Checker] phase 5 gitignore claim was half right.** `.gitignore:12`
   already ignores `*.egg-info/`; `build/` is not ignored.

Resolved by direct evidence rather than interview: `docs/evidence/flink/`'s 10
committed JSONs record no Flink version string, so no captured artifact
contradicts the 1.20.3 decision. This closed the plan's only open question.

#### Questions & Answers

1. **[Rubric check]** How to repoint `scripts/_rubric_items.py:130-133` when
   `config_loader.py` moves?
   - **Answer:** Point at both real files —
     `_exists_any("src/collectors/fixture_config.py", "configs/generator-config.yaml")`.
   - **Rationale:** Fixes the dead second path in the same edit; both are genuine
     evidence that generation is config-driven.

2. **[Flink version]** 1.20.3 or 1.19?
   - **Answer:** 1.20.3 everywhere.
   - **Rationale:** Dockerfile + both config files already say it, the connector
     jar is pinned to `3.3.0-1.20`, and no committed evidence artifact records a
     version at all.

3. **[Postgres gating]** How do the new `postgres` marker and the existing
   `PHASE2_REQUIRE_PG` skip interact?
   - **Answer:** Keep both, different jobs — skip answers "can this machine run
     it", marker answers "do I want to run it now".
   - **Rationale:** Deleting the skip would turn a clean skip into errors for a
     developer without `initdb`, and CI's hard-failure guarantee must survive.

4. **[PR granularity]** How should phases 2-6 land?
   - **Answer:** One PR per phase.
   - **Rationale:** Each is independently revertable, and the Flink repair — the
     only phase that cannot be fully verified without booting the opt-in
     profile — does not block the low-risk phases.

#### Phase Propagation

- `phase-02`: version decision recorded as settled with the evidence-JSON check;
  matching risk entry downgraded from open to cleared.
- `phase-03`: `scripts/_rubric_items.py` added to Related Code Files, new
  implementation step 7 (repoint in the same commit), verification grep widened
  to the path form, new success criterion for rubric row 7, risk restated as
  confirmed.
- `phase-05`: CI target corrected to job id `test`; gitignore step corrected to
  add only `build/`; success criterion renamed.
- `phase-06`: `PHASE2_REQUIRE_PG` mechanism documented as coexisting with the
  markers; step 4 told to leave it untouched; new success criterion for both
  the developer-without-initdb and the CI paths.
- `plan.md`: PR granularity recorded; open questions closed.

### Whole-Plan Consistency Sweep

- Files reread: `plan.md`, `phase-01-start.md`, `phase-02-…`, `phase-03-…`,
  `phase-04-…`, `phase-05-…`, `phase-06-…`
- Decision deltas checked: 4
- Reconciled stale references: 6
- Unresolved contradictions: 0

Specifically checked and reconciled: no phase still describes the Flink version
as undecided; no phase still refers to a "stage-1 job"; phase 4's "not moved:
`sql/`" rationale does not contradict phase 3's move of a different file out of
`src/`; phase 6's marker taxonomy does not contradict phase 4's decision to leave
`tests/` in place; the `-m "not slow"` fast loop is described identically in
phase 6 and in the plan's success criteria.

<!-- slug: architecture-hygiene-before-phase-3 -->
