# Financial Distress Data — Agent Rules

Process memory only. WHY/architecture live in `docs/`; this file is HOW-TO-BEHAVE.

## Read Order (source of truth)

1. `AGENTS.md` (this file) — non-negotiable.
2. `docs/mini_coursework.md` — Phase 1 spec (active scope, see below).
3. `plans/260802-1037-unified-phase2-ml-llm-gitops/plan.md` — Phase 2 ground truth, read only when a task explicitly targets Phase 2. It links onward to `docs/coursework.md`, `docs/phase2/*` (rubric matrix, ADRs, low-level design), and phase files `phase-01..08`.

Conflict between docs: Phase 1 local-first decisions in this file and `docs/mini_coursework.md` win.

## Phase Scope

- Phase 1 = `docs/01_data_generator.md` + `docs/02_schema_design.md`. Default active phase unless the task says Phase 2.
- Phase 2 code is additive-only under `src/ml/`, `src/drift/`, `src/llm/`, `src/agents/`, `apps/`, and thin wrappers in `dags/phase2/`.
- `dags/phase2/` wrappers must have zero import-time side effects and must not rename/remove any existing Phase 1 DAG ID or task.
- Never edit a Phase 1 DAG (`dags/*.py` outside `dags/phase2/`) or Phase 1 pipeline behavior for a Phase 2 task unless the task explicitly asks for it.

## Don't Touch

- Phase 1 (this repo, `src/collectors`/`generator`/`streaming`/`transforms`/`quality`/`catalog`/`metadata`, `dags/*.py` outside `phase2/`): no AWS RDS/S3/Glue/Athena/EMR/MSK/Redshift/SageMaker, no Kubernetes, no `boto3` for Athena/Glue — local-first stack only (MinIO + DuckDB `httpfs`, not cloud equivalents).
- Phase 2's AWS/EKS/GitOps platform (EKS, S3, ECR, RDS, ElastiCache, Argo CD, etc. — see `plans/260802-1037-unified-phase2-ml-llm-gitops/phase-03-bootstrap-gitops-and-aws-evidence-platform.md`) lives in a **separate** `financial-distress-gitops` control repo, not in this repo. If a Phase 2 task needs that infra and the gitops repo isn't checked out locally, say so instead of adding AWS/K8s code here.
- Don't change an existing test's expected value to make it pass. If a test fails, re-check the test and code against the spec (`docs/mini_coursework.md` for Phase 1, `plans/260802-1037-unified-phase2-ml-llm-gitops/plan.md` for Phase 2); if the spec is right, fix the code.
- Don't hand-edit `warehouse.db`, `outputs/**`, or anything under `docs/evidence/` — these are generated artifacts, regenerate via the producing script instead.
- Don't run Flink locally by default — it's opt-in via the `flink` Docker Compose profile and `ENABLE_FLINK=1`; not started by plain `docker compose up`.

## Data Contract Rules (non-obvious, wrong-by-default otherwise)

- Bronze: append-only.
- Silver/Gold: idempotent writes, `overwrite` mode on affected partitions only (not full-table overwrite).
- Dedupe by business key + latest `created_ts`.
- DQ results go to `project_metadata.data_quality_result`; critical failures halt downstream tasks; warning-level failures route rows to `project_metadata.failed_records` and may continue.
- PostgreSQL schema split: `project_metadata` (Phase 1) vs `ml_metadata` (Phase 2) — don't cross-write.

## Verify Commands

```bash
.venv/bin/python -m pytest tests            # full suite
.venv/bin/python -m pytest tests -k <name>  # single test, use while iterating
.venv/bin/ruff check src dags tests scripts
.venv/bin/black --check src dags tests scripts
docker compose config                        # validates compose file without starting anything
.venv/bin/python scripts/run_stage1_quality_gates.py   # one-shot: runs all four above
```

Definition of done for any code change: the one-shot gate above passes. CI (`.github/workflows/ci.yml`) runs the same gate on push/PR to `main`/`dev`.

## Git Conventions

- Commit subject: Conventional Commits, `type(scope): summary` (e.g. `feat(phase2): lock spec`, `fix: stabilize stage 1 e2e runtime`, `docs(agents): trim rules`). Types in use: `feat`, `fix`, `docs`, `chore`, `test`, `style`, `ci`.
- Never add a co-author trailer (no `Co-Authored-By`) or any AI-attribution line to commit messages.
- Branch name: `type/kebab-slug` matching the commit type (e.g. `feat/w25-rubric-coverage-audit`, `fix/review-highlights-stage1`, `docs/stage-1-contracts`, `chore/stage-1-local-infra`).
- Merge to `main`/`dev` through a PR; don't push directly to `main`.

## Time-Costly — avoid unless the task needs it

- `scripts/run_stage1_quality_gates.py --include-services` and `scripts/stage1_readiness_report.py --include-services` need the Docker stack (`docker compose up`) already running — don't start the stack just to run these.
- `scripts/run_stage1_real_e2e.py` hits live Kafka/MinIO/Postgres/Airflow containers — full stack boot, not a quick check. `tests/test_real_e2e_contracts.py` only pins that script's contracts (evidence-audit logic, DAG task-chain shape, serializer behavior) against fixtures/`tmp_path`; it needs no live service and runs in the fast loop (measured: 514-test suite in <6s, zero skips without Docker up).
- `scripts/run_flink_benchmark.py` requires `ENABLE_FLINK=1` and the `flink` compose profile — skip unless the task is Flink/W17/W20 streaming evidence. `tests/test_flink_integration.py` pins the Flink client + DAG 04 opt-in behavior with `urllib` fakes and `monkeypatch`, by design (see its docstring); it needs no live Flink and runs in the fast loop.
- `pytest tests -m "not slow"` runs the fast loop only — no Docker stack, no Postgres binaries. `pytest tests` (no `-m`) is the full suite and the definition of done; markers select, they never skip. `-m "postgres"` selects `tests/phase2/product/*`, which spins an ephemeral Postgres cluster per session via local `initdb`/`pg_ctl` (skips without them, unless `PHASE2_REQUIRE_PG=1`, which CI sets). Note `--strict-markers` only catches an unregistered marker used via `@pytest.mark.foo`, not a typo in an `-m` selection expression — `-m "not sloow"` silently matches zero tests rather than erroring.
- Don't run the full `pytest tests` suite for a one-file change — target it with `-k` first, run the full suite before declaring done.

## Acceptance Criteria Format

Write every acceptance criterion as `WHO -> ACTION -> RESULT` (e.g. "PySpark `silver_to_gold` job -> computes `debt_to_asset` -> `total_liabilities / total_assets`, float, 4dp"). Reject vague AC ("system should calculate correctly") before implementing against it — go back to the spec instead.

## Task Start Checklist

State before editing code or pipeline configs:

- Active phase (Phase 1 default, or explicit Phase 2).
- Spec file(s) read for this task.
- Acceptance criteria in `WHO -> ACTION -> RESULT` form.
- Verify command(s) you'll run before calling it done.

## Codex-Specific Tooling

Codex sessions and Claude Code sessions use the installed `ak:*` skill catalog instead — see `CLAUDE.md`.

## Mandatory Skill Activation

Before acting, classify the request using the installed skill catalog and the local routing rules in this file.

- User names a skill -> use that skill.
- Codebase discovery or structure questions -> use `ak:scout`.
- Bug investigation -> use `ak:debug`; bug implementation -> use `ak:fix`.
- Feature or configuration implementation -> use `ak:plan` for multi-step work, then `ak:cook`; execute an existing plan directly when one is provided.
- Test strategy or test execution -> use `ak:test`; code review -> use `ak:code-review`.
- Documentation changes -> use `ak:docs`; frontend, backend, database, infrastructure, security, AI, media, or office-file work -> use the matching domain skill.
- Direct explanations and simple read-only answers -> no skill is required; state that decision when it is not obvious.

When a skill is selected:

1. Read its complete `SKILL.md` before taking task actions.
2. Announce the selected skill and its purpose in the session progress update (`commentary` when available).
3. Follow its workflow, including required verification and review gates.
4. If multiple skills apply, use the smallest ordered set that covers the request.

Do not invoke skills merely for ceremony. Do not skip a clearly matching skill because the task appears small; use its lightweight path when available.
