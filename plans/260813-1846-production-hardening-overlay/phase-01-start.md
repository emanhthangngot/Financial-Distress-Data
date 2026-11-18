---
phase: 1
title: "Repo unification, guardrails and baseline"
status: in_progress
priority: P1
effort: "3.5d"
dependencies: []
---

# Phase 1: Repo unification, guardrails and baseline

## Overview

Two jobs, in this order:

1. **Close the protection gap** — six `src/` packages hold platform .ode that no
   gate protects, including one that already-protected code depends on.
2. **Remove phase naming from code and infrastructure** so the repo reads as one
   production system, not two coursework stages.

Layout work comes first in the whole plan deliberately (user decision,
2026-08-13): doing renames after phases 3-11 build five subsystems on the old
paths would multiply the churn and guarantee path conflicts.

No cloud quota required.

## Requirements

- Functional: `PHASE1_PROTECTED` covers every package that holds Phase 1
  behaviour; the auditor reports missing `artifact_path` for all rows, not only
  at phase-08; no phase name remains in code, container or config paths.
- Non-functional: the strict `--track LLM` gate result is identical before and
  after; the platform .uality gate is unchanged; zero behaviour change anywhere.

## Evidence: package phase-ownership audit

Method — trace importers. A package imported by a protected platform .AG or by an
already-protected `src/` module holds platform .ehaviour, regardless of its name.

| Package | Owner | Evidence |
|---|---|---|
| `src/security/` | **Phase 1** | `src/transforms/spark_session.py` (**already protected**) imports `src.security.secrets`; also `src/jobs/stage1_*`, `scripts/run_stage1_real_e2e.py` |
| `src/evidence/` | **Phase 1** | `scripts/audit_mini_coursework_rubric.py` and `run_mini_coursework_submission.py` build `docs/evidence-index.md` — the scored 100/100 mini-coursework index |
| `src/lakehouse/` | **Phase 1** | W19 compaction spine; `dags/06_pyspark_silver_to_gold.py`, `dags/dp1_bronze_ingest.py`; produces R25/R26 evidence |
| `src/jobs/` | **Phase 1** | `stage1_evidence_job.py`, `stage1_spark_lakehouse_job.py`, `kafka_to_bronze_job.py`; 3 platform .AGs |
| `src/orchestration/` | **Phase 1** | `airflow_tasks.py`; 3 platform .AGs |
| `src/io/` | **Shared** | Phase 1: `dags/dp1_bronze_ingest.py`, `dags/stage1_real_e2e_pipeline.py`, `src/generator/storage.py`, `src/jobs/*`. Phase 2: 3 Feast modules |
| `src/governance/` | **Shared** | Phase 1: `datahub_emitter/graphql/model` drive `scripts/sync_datahub_governance.py` (R33-R38 lineage). Phase 2: `phase2_lineage.py` |
| `src/agents/` `src/drift/` `src/llm/` `src/ml/` `src/observability/` | platform . only platform .mporters |

`src/security/` is the sharpest case: **protected code depends on unprotected
code**, so the gate can pass while platform .ehaviour changes underneath it.

Handling the two shared packages: do **not** protect the whole package, which
would block legitimate platform .ork. Protect at file granularity via
`PHASE1_PROTECTED_EXCEPTIONS`, the mechanism already used for
`src/streaming/flink/jobs/` and `sql/init_ml.sql`:

- `src/io/` protected, except the Feast-facing helpers platform .eeds
- `src/governance/` protected, except `phase2_lineage.py`

## Evidence: where phase naming actually binds

315 tracked files carry `phaseN` in their path. Only some of it is load-bearing.
Measured against `docs/platform/rubric-matrix.csv`:

| Matrix column | Points at | Rows |
|---|---|---:|
| `evidence_path` | `docs/platform/...` | **117 / 117** |
| `test` | `tests/platform/...` | **117 / 117** |
| `validation_command` | `tests/platform/...` | **117 / 117** |
| `artifact_path` | `.github/workflows/phase2-*.yaml` | 13 |
| `artifact_path` | `tests/phase2`, `dags/phase2`, `docs/phase2` | 14 |
| — | `infra/phase2` | **0** |

Plus two hard-coded gate behaviours: the `dags/phase2/` carve-out at
`scripts/audit_phase2_evidence.py:411`, and the evidence-contract rule that an
evidence path may not leave `docs/platform/evidence/`.

### Tier 1 — no gate meaning, rename freely (this phase)

`infra/phase2/` · `requirements-phase2.txt` · compose services `phase2-redis`,
`phase2-postgres`, volume `phase2-pgdata` · `configs/phase2-governance.yaml` ·
`src/governance/phase2_lineage.py` · `apps/web/scripts/phase2/` ·
`scripts/*phase2*.py` and `scripts/run_phase5_*.py`

### Tier 2 — decided 2026-08-13

**IN scope:** `.github/workflows/phase2-*.yaml` -> function names. 13
`artifact_path` rows update with it; safe because `artifact_path` is a
project-owned column, not an input to `source_digest`.

| Current | New | Note |
|---|---|---|
| `phase2-ci.yaml` | `deployable-ci.yaml` | reusable job; all 8 callers' `uses:` lines update with it |
| `phase2-agent-coordinator.yaml` | `agent-coordinator.yaml` | |
| `phase2-agent-drift.yaml` | `agent-drift.yaml` | |
| `phase2-agent-feature.yaml` | `agent-feature.yaml` | |
| `phase2-drift-mcp.yaml` | `drift-mcp.yaml` | |
| `phase2-rag-pipeline.yaml` | `rag-pipeline.yaml` | |
| `phase2-stream-feature-offline.yaml` | `stream-feature-offline.yaml` | |
| `phase2-stream-feature-online.yaml` | `stream-feature-online.yaml` | |
| `phase2-web.yaml` | `web.yaml` | |

`ci.yml` (the platform .ate) is **not** renamed — it is very likely a required
status check in branch protection, and renaming a workflow renames its check,
which silently stops blocking merges. Verify the branch-protection rule before
touching it; that check is deferred to Tier 3 regardless.

**OUT of scope, deferred to Tier 3:** `dags/phase2/` · `tests/platform/` ·
`docs/platform/`

### Tier 3 — after submission

`dags/phase2/` · `tests/platform/` · `docs/platform/` · `docs/evidence/` · `ci.yml`
(after confirming branch protection) · DAG file naming · the protected `src/`
package names

## Dependency manifests: consolidate on `pyproject.toml` (decided 2026-08-13)

The request was "merge the two requirements files". Measuring first showed the
problem is larger: **four dependency declarations exist and none agrees with the
others.**

| Declaration | Packages | Consumed by |
|---|---:|---|
| `requirements.txt` | 11 | `.github/workflows/ci.yml:24` |
| `requirements-phase2.txt` | 26 | `.github/workflows/phase2-ci.yaml:65,88` |
| `pyproject.toml` `[project.dependencies]` | **2** (`pandas`, `pyyaml`) | `ci.yml:27` (`pip install -e .`) |
| `uv.lock` | 44 | nothing in CI |

Two consequences, both real defects rather than untidiness:

1. **`pip install -e .` produces a broken install.** `ci.yml` runs it and then
   imports `src.ml.contracts` as an installability check — against package
   metadata claiming two dependencies while the project needs at least eleven.
   Anyone installing this project as a package gets the broken version.
2. **`uv.lock` pins 44 packages that match no manifest.** It is currently dead
   weight, not a reproducibility guarantee — even though the evidence contract
   demands a reproducible `command` and recorded `versions` for every artifact,
   which is exactly what a lockfile is for.

Also measured: **CI has no virtualenvs at all.** Both workflows `pip install`
straight into the runner's system Python. The `.venv` / `.venv-phase2` split is a
local development convention only; it provides no isolation in CI, so merging the
manifests cannot break an isolation that CI never had.

### Target

`pyproject.toml` becomes the single source of truth:

```toml
[project]
dependencies = [ ...the 11 real runtime deps... ]

[project.optional-dependencies]
ml  = ["feast", ...]           # + mlflow, scikit-learn, xgboost in phase 10
dev = ["pytest", "ruff", "black", "mutmut", "hypothesis", "locust", ...]
```

- both `requirements*.txt` deleted
- `uv.lock` regenerated from `pyproject.toml` — it becomes the real pin the
  evidence contract needs
- CI installs `pip install -e ".[dev,ml]"`, one step replacing two
- one virtualenv

Extras give, declared and explicit, the isolation the venv split was
approximating by accident: someone who only needs the platform .oop installs
`".[dev]"`.

### Replace the implicit guarantee with an explicit one

The venv split was a blunt instrument enforcing "no heavy import at module
scope" (the D4 lazy-import rule). A test enforces it precisely and survives the
merge:

```python
def test_no_heavy_imports_at_module_scope():
    # import every src/ module; assert feast/torch/mlflow never enter sys.modules
```

Roughly fifteen lines, runs in the fast loop. **This**, not two directories, is
what protects the six-second loop.

### The merge itself is conflict-free

Verified before committing to the approach. Ten packages appear in both
requirements files, and every one has the *same lower bound*; the platform .ile
merely adds an upper bound:

**The merge is clean — measured, not assumed.** 10 packages appear in both, and
every one has the *same lower bound*; platform .erely adds an upper bound:

| Package | `requirements.txt` | `requirements-phase2.txt` |
|---|---|---|
| `black` | `>=24.0` | `>=24.0,<26` |
| `pandas` | `>=2.2` | `>=2.2,<3` |
| `pgvector` | `>=0.3` | `>=0.3,<1` |
| `psycopg[binary]` | `>=3.2` | `>=3.2,<4` |
| `pyarrow` | `>=17.0` | `>=17,<22` |
| `pytest` | `>=8.0` | `>=8,<10` |
| `pyyaml` | `>=6.0` | `>=6,<7` |
| `requests` | `>=2.31` | `>=2.31,<3` |
| `ruff` | `>=0.8` | `>=0.8,<1` |
| `tenacity` | `>=8.0` | `>=8,<10` |

Zero conflicts. The platform .ounds are strictly narrower and compatible, so the
consolidated declaration takes the bounded form throughout. `duckdb>=1.1` is the
only Phase-1-only package; the other 15 are Phase-2-only. Runtime versus dev
versus ml classification is decided while writing the `pyproject.toml` sections.

### What `.venv-phase2` actually contains — do not trust the older notes

`plans/260802-1037-unified-phase2-ml-llm-gitops/phase-04-implementation-notes.md`
lines 567 and 743 state that `sentence-transformers` plus CPU `torch` (~2 GB)
were installed into `.venv-phase2`. **Verified 2026-08-13: neither is installed.**
Both imports fail with `ModuleNotFoundError`. That note records an intention, not
the delivered state.

Measured reality:

| | `.venv` | `.venv-phase2` |
|---|---|---|
| declared | 11 packages | 26 packages |
| installed (site-packages entries) | 104 | 202 |
| size | 1022 MB | 1.2 GB |
| `feast` | absent | present (0.65) |
| `torch` / `sentence-transformers` | absent | **absent** |

The 202 entries are Feast's transitive closure — normal, not an undeclared-
dependency defect. This matters for sizing: consolidating the manifests pulls in
Feast's tree, **not** a 2 GB deep-learning stack. If phase 10 later needs
`sentence-transformers`, it is a new declared dependency in the `ml` extra, not
something already present.

### Retire `.venv-phase2` by proof, not by deletion

Do not delete it and then find out. Rebuild `.venv` from the consolidated
declaration, then demonstrate all four command groups run from that one
environment:

1. the platform .ne-shot gate (`scripts/run_stage1_quality_gates.py`)
2. the fast loop (`pytest tests -m "not slow"`) — timed against baseline
3. the platform .uditor (`scripts/audit_phase2_evidence.py`, currently documented
   in `README.md:427` as requiring `.venv-phase2` on `PATH`)
4. the `feast` CLI against `feature_repo/` — the original reason for the split

Only after all four pass does `.venv-phase2` get removed, along with the README
instructions that reference it. `scripts/smoke_embedding_endpoint.py` also names
it in its docstring and needs updating.

One environment now serves both development and evidence reproduction, so
`uv.lock` stops being decorative and starts carrying real weight — record its
hash in the evidence run manifest alongside `source_sha` and the image digest.

## The one thing that must not be done, and why

**`docs/platform/evidence/` cannot become `docs/evidence/`.** Not because of risk —
because it would collide. `docs/evidence/` already exists and holds the scored
mini-coursework evidence. `docs/platform/evidence-contract.md` states the reason
directly: *"platform .vidence lives in a separate namespace `docs/platform/evidence/{ml,llm}/`
so the two can never collide."*

These are the evidence sets of **two separately graded submissions**, not two
stages of one system. Merging them destroys the distinction the grader needs.

So the unification splits cleanly along a real seam:

| Concern | Phase naming is | Action |
|---|---|---|
| Source code, containers, configs, compose services, CI workflow names | genuinely harmful — production repos organise by function | **remove entirely** |
| Rubric matrix, evidence namespace, requirement tests | a *submission* boundary, not an architecture boundary | **keep until submitted**, collapse in Tier 3 |

After Tier 1 + the Tier 2 workflow renames, every path a reader of the *code*
touches is phase-free. What remains phase-scoped is the evidence tree — which is
exactly the thing that should be scoped to a submission.

## Related Code Files

- Modify: `scripts/audit_phase2_evidence.py` — `--check-artifacts`; extend `PHASE1_PROTECTED` with `src/security/`, `src/evidence/`, `src/lakehouse/`, `src/jobs/`, `src/orchestration/`, `src/io/`, `src/governance/`; add the two file-level exceptions
- Move: `infra/phase2/{rag-pipeline,stream-feature-offline,stream-feature-online}/` -> `infra/*/`
- Modify: `.github/workflows/phase2-rag-pipeline.yaml`, `phase2-stream-feature-offline.yaml`, `phase2-stream-feature-online.yaml` — `dockerfile:` paths
- Modify: `pyproject.toml` — real `[project.dependencies]` plus `ml` and `dev` extras
- Regenerate: `uv.lock` from `pyproject.toml`
- Delete: `requirements.txt`, `requirements-phase2.txt`, `.venv-phase2` (last, after proof)
- Modify: `README.md:427-428`, `scripts/smoke_embedding_endpoint.py` — drop `.venv-phase2`
- Create: `tests/test_no_heavy_imports.py`
- Rename: all 8 `.github/workflows/phase2-*.yaml` per the Tier 2 table; update every caller's `uses:` line
- Modify: `docker-compose.yml` — `phase2-redis` -> `feast-redis`, `phase2-postgres` -> `vector-postgres`, `phase2-pgdata` -> `vector-pgdata`
- Rename: `configs/phase2-governance.yaml` -> `configs/governance.yaml`; `src/governance/phase2_lineage.py` -> `src/governance/ml_lineage.py`
- Modify: `docs/project-file-map.md` — lines 562-564 and every renamed path
- Modify: `docs/platform/rubric-matrix.csv` — `platform/ml/ab-testing.yaml` -> `platform/llm/ab-testing.yaml`
- Modify: `AGENTS.md` — scope relaxation, config naming rule, phase-ownership table
- Delete: `src/generators/` (orphan, untracked, only stale `__pycache__`)
- Create: `.githooks/pre-commit`, `tests/platform/test_artifact_path_contract.py`, `baseline.md`

## Implementation Steps

Order matters — guardrails before renames, so a rename that breaks something is
caught by the tripwire rather than discovered at phase 12.

1. **Baseline.** Run the one-shot gate, `--matrix-only --strict`, and the strict
   `--track LLM` gate. Record all three outputs plus both repos' HEAD SHAs into
   `baseline.md`. Every later step compares against this.
2. **Close the protection gap.** Extend `PHASE1_PROTECTED` with the six Phase 1
   packages and add file-level exceptions for the two shared ones. This only
   tightens the gate, so it cannot cost LLM points — but re-run the gate
   immediately to confirm the current working diff is still clean. If it is not,
   stop: something already mutated platform .nnoticed, and that is a finding.
3. **Tripwire.** Add `.githooks/pre-commit` running the protected-path diff
   against `PHASE1_BASE_SHA`; document `git config core.hooksPath .githooks`.
4. **`--check-artifacts`.** Reuse the existing repo-root resolution so
   `artifact_repo` still selects between the source checkout and `--gitops-root`.
   `executed` + missing -> FAIL; `design_only` + missing -> WARN with the row.
5. **Matrix path drift.** Fix `platform/ml/` -> `platform/llm/`, then re-run
   `--matrix-only --strict` to confirm digests and row-count pins are unaffected.
6. **Artifact contract test.** `tests/platform/test_artifact_path_contract.py`:
   every `executed` row resolves on disk; the count of missing `design_only`
   artifacts matches a recorded number, so the backlog shrinking is visible.
7. **Delete `src/generators/`.** Untracked orphan, nothing imports it, sits one
   character from the real `src/generator/`.
8. **Flatten `infra/`.** `git mv` the three phase-2 directories up one level,
   update `configs/phase2-deployables.yaml` and `project-file-map.md`. Verify
   `docker compose config` still validates. **Done 2026-08-14.** Note:
   `infra/phase1-cluster/` is a *separate*, never-committed directory from the
   now-cancelled phase 9 (platform .n the shared cluster) — it is archived
   as-is in the ML-scaffolding commit, not flattened into this service axis,
   since integrating it would mean resuming cancelled work.
9. **Consolidate dependencies onto `pyproject.toml`.** Baseline first:
   `time .venv/bin/python -m pytest tests -m "not slow"`. Then write the real
   `[project.dependencies]` plus `ml` and `dev` extras from the two requirements
   files (bounded pins), regenerate `uv.lock`, repoint `ci.yml` and
   `deployable-ci.yaml` to `pip install -e ".[dev,ml]"`, and delete both
   `requirements*.txt`. Add `test_no_heavy_imports_at_module_scope`. Rebuild
   `.venv`, re-measure the fast loop against baseline, and run all four command
   groups. A collection-time regression means a module broke the lazy-import
   rule — fix that module, do not restore the split. Delete `.venv-phase2` and
   its references in `README.md:427-428` and
   `scripts/smoke_embedding_endpoint.py` only after all four groups pass.
10. **De-phase the remaining Tier 1 names** — compose services and volume,
    governance config and module, `apps/web/scripts/phase2/`, script filenames.
    Compose service renames touch every consumer: grep each old name before and
    after, and run the **full** suite, not a `-k` subset.
11. **Rename the 8 workflows** per the Tier 2 table. Rename `phase2-ci.yaml` to
    `deployable-ci.yaml` first and update all 8 callers' `uses:` lines in the same
    commit, otherwise every caller breaks. Then update the 13 `artifact_path`
    rows and re-run `--matrix-only --strict`. Do **not** touch `ci.yml` — verify
    the branch-protection required-check name first (Tier 3).
12. **`AGENTS.md`** — scope relaxation citing `docs/mini_coursework.md:16`
    ("unless explicitly requested"); the statement that `PHASE1_HYGIENE_OVERRIDE`
    is forbidden for this plan; the kebab-case rule for **new** config files
    (existing `configs/` names stay — bulk renaming before submission is churn);
    and the 19-package phase-ownership table pointing at
    `audit_phase2_evidence.py:58` as the authority.
13. Run the full verification set and diff every gate output against `baseline.md`.

## Verification

```bash
.venv/bin/python scripts/run_stage1_quality_gates.py
.venv/bin/python scripts/audit_phase2_evidence.py --matrix-only --strict
.venv/bin/python scripts/audit_phase2_evidence.py --check-artifacts \
  --gitops-root ~/Studying/FSDS/financial-distress-gitops
.venv/bin/python -m pytest tests
time .venv/bin/python -m pytest tests -m "not slow"   # compare against baseline
docker compose config
docker build -f infra/rag-pipeline/Dockerfile .
grep -rn 'phase2' src configs infra docker-compose.yml .github/workflows   # expect no hits
```

## Success Criteria

- [x] `baseline.md` records three green gate outputs and both repo HEAD SHAs (records six: matrix, fast loop, compose, stage-1 evidence audit, ruff, black; both HEAD SHAs present)
- [x] `PHASE1_PROTECTED` -> extended with the six platform .ackages plus two file-level exceptions -> gate re-run, current diff still clean (`scripts/audit_phase2_evidence.py:61-103` lists all six packages plus five file-level exceptions, more than the originally scoped two — `src/lakehouse/{catalog,tables,snapshots}.py` added for the additive lakehouse contracts; strict `--track LLM` gate passes clean on the current tree)
- [x] Pre-commit hook -> given a staged edit to `src/security/` -> refuses the commit (live-tested 2026-08-14: staged edit to `src/security/secrets.py`, `bash .githooks/pre-commit` exits 1 with `staged edit touches platform protected path`; edit discarded, not committed. No automated test file covers it — hook behaviour, not Python)
- [x] `--check-artifacts` -> run against both repos -> FAILs on `executed` gaps, WARNs on `design_only`, lists exactly the missing set
- [x] `--matrix-only --strict` -> run after the path fix -> passes, digests unchanged
- [ ] `src/generators/` -> deleted -> `pytest tests` unchanged — no tracked `.py` source under `src/generators/` (was already untracked), but stale `__pycache__/*.pyc` entries still exist on disk; not confirmed as an intentional deletion action this pass
- [x] `infra/phase2/{rag-pipeline,stream-feature-offline,stream-feature-online}` -> flattened to `infra/*` -> `docker compose config` valid, `configs/phase2-deployables.yaml` dockerfile paths updated
- [ ] Tier 1 renames -> completed -> `grep -rn 'phase2' src configs infra docker-compose.yml .github/workflows` returns nothing
- [ ] `pyproject.toml` -> declares the real runtime deps plus `ml`/`dev` extras -> `pip install -e ".[dev,ml]"` in a clean environment imports `src.ml.contracts` successfully
- [ ] Both `requirements*.txt` -> deleted -> CI installs from `pyproject.toml` only
- [ ] `uv.lock` -> regenerated -> matches `pyproject.toml`, and its hash is recorded in the evidence run manifest
- [ ] All four command groups (platform .ate, fast loop, platform .uditor, `feast` CLI) -> run from a single `.venv` -> all pass; only then is `.venv-phase2` deleted
- [ ] `test_no_heavy_imports_at_module_scope` -> imports every `src/` module -> feast/torch/mlflow never enter `sys.modules`
- [ ] Fast loop -> timed before and after -> no collection-time regression (baseline: 514 tests, <6s, zero skips)
- [ ] 8 workflows -> renamed per the Tier 2 table -> every caller's `uses:` resolves, CI green, 13 `artifact_path` rows updated, `--matrix-only --strict` passes
- [ ] `ci.yml` -> untouched -> platform .equired status check still blocks merges
- [ ] `docker compose config` -> valid; full suite green after service renames
- [ ] `AGENTS.md` -> read -> states scope relaxation, config naming rule, and the 19-package ownership table
- [x] Strict `--track LLM` gate -> run at phase end -> identical PASS 100/100 to `baseline.md`

## ML rubric rows closed

None directly. This is the enabler: it produces the authoritative missing-artifact
backlog that phases 6-11 consume, the tripwire that keeps plan goal 1 true, and
the path layout that phases 3 and 8 build on.

It also lands a real part of **Repository Design** (2 pts, claimed in phase 12) —
clean repo structure is literally what that row scores.

## Risk Assessment

- **Compose service renames have the widest blast radius in this phase.**
  `phase2-postgres` and `phase2-redis` appear in code, tests, DAGs and docs.
  Grep each name exhaustively before and after; run the full suite, not `-k`.
- **Extending `PHASE1_PROTECTED` could fail immediately** if the working tree
  already touches one of the six packages. That is a genuine finding, not a
  blocker to work around — investigate before proceeding.
- **Editing the matrix could disturb the canonical CSV digest pins.** Mitigated by
  the immediate `--matrix-only --strict` re-run; `artifact_path` is not an input
  to `source_digest`.
- **Renaming `phase2-ci.yaml` breaks all 8 callers** if the `uses:` lines are not
  updated in the same commit. Rename it first, atomically, before the leaf
  workflows.
- **Renaming a workflow renames its GitHub status check.** If a renamed workflow
  is a required check in branch protection, the requirement silently stops
  applying. This is why `ci.yml` is explicitly out of scope until the protection
  rule is read.
- **Merging the manifests puts Feast in the fast-loop environment.** The
  lazy-import discipline should absorb it, but step 9 measures rather than
  assumes, and a regression blocks the step.

## Decisions taken (user, 2026-08-13)

1. **Tier 2 workflow renames — YES.** All 8 `phase2-*.yaml` renamed to function
   names; 13 `artifact_path` rows updated. `ci.yml` excluded pending a
   branch-protection check.
2. **`dags/phase2/`, `tests/platform/`, `docs/platform/` — NO.** Deferred to Tier 3,
   after submission. `docs/platform/evidence/` cannot merge into `docs/evidence/`
   at all while both submissions are graded separately.
3. **Requirements — MERGE, not rename.** One `requirements.txt`. Verified
   conflict-free before committing to it.
