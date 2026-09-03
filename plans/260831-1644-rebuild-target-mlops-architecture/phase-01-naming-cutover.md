---
phase: 1
title: "Phase 1: Unified naming cutover"
status: pending
priority: P1
effort: "4-6 days"
dependencies: ["phase-00-gates.md"]
owns: ["ALL renames — runs alone, no other phase may be in flight"]
---

# Phase 1: Unified naming cutover

## Overview

Erase the platform database schema, CI
workflow name and document. Source-only and GitOps-only; no cluster workload changes. **Resident
cost: 0.**

**This phase runs alone.** It touches ~90 paths and ~300 files. Any concurrent phase would collide
on every one of them.

Renaming is not cosmetic here. The split is the thing the user is removing, and it is currently
embedded in the data layer (two Postgres schemas that are forbidden to reference each other), in the
test layer (`tests/platform/`), in orchestration (`dags/phase2/`), and in the runtime (`phase2-data`,
`phase2-llm` namespaces). Leaving it in place makes O-3 unachievable and keeps the two-schema
foreign-key gap (D-12) permanent.

## Requirements

- Functional: zero `phase1` / `phase2` / `stage1` tokens in file names, directory names, Python
  identifiers, Kubernetes namespaces, Postgres schema names, Argo `destination.namespace` fields,
  Terraform labels, or documentation prose — outside two recorded exceptions.
- Non-functional: the full test suite passes at exit with zero skips; every rename lands as one
  atomic commit per rename class so a single class can be reverted independently; no behavioral
  change of any kind is bundled into this phase.

### Recorded exceptions

| Exception | Reason | Recorded in |
|---|---|---|
| `supabase/migrations/*_phase2_*.sql` and `migrations/rollback/*` | Applied-migration filenames are keys in `supabase_migrations.schema_migrations`. Renaming re-applies or orphans migrations against the live product-plane database. | ADR-019 |
| `plans/**` | Historical planning records. Rewriting them destroys the decision trail. | ADR-019 |

`scripts/verify_naming_cutover.py` must exclude exactly these two paths and no others.

## Architecture — cutover map

| Old | New |
|---|---|
| `docs/platform/` | `docs/platform/` |
| `docs/platform/adr/` | `docs/platform/adr/` |
| `docs/phase1_architecture.md` | `docs/architecture/lakehouse.md` |
| `docs/02_schema_design.md` + `docs/schema-design.md` | merged → `docs/architecture/data-model.md` |
| `tests/platform/` | `tests/platform/` |
| `tests/test_stage1_*.py` | `tests/test_lakehouse_*.py` |
| `tests/platform/test_phase1_cluster_parity.py` | `tests/platform/test_lakehouse_cluster_parity.py` |
| `dags/phase2/phase2_*.py` | `dags/*.py` (flattened, prefix dropped) |
| `dags/stage1_local_evidence_pipeline.py` | `dags/lakehouse_local_evidence_pipeline.py` |
| `dags/stage1_real_e2e_pipeline.py` | `dags/lakehouse_real_e2e_pipeline.py` |
| `dags/_stage1_dag_utils.py`, `dags/utils/stage1_dag_utils.py` | `dags/utils/dag_utils.py` (single module) |
| `src/jobs/stage1_*.py` | `src/jobs/lakehouse_*.py` |
| `src/governance/phase2_lineage.py` | `src/governance/lineage.py` |
| `scripts/*stage1*` | `scripts/*lakehouse*` |
| `scripts/run_stage1_quality_gates.py` | `scripts/run_quality_gates.py` |
| `scripts/*phase2*` | `scripts/*platform*` |
| `scripts/phase2_ci/` | `scripts/ci/` |
| `scripts/_phase2_rubric_items.py` + `scripts/_rubric_items.py` | `scripts/_rubric_items.py` (merged in P3) |
| `configs/phase2-deployables.yaml` | `configs/platform-deployables.yaml` |
| `configs/phase2-governance.yaml` | `configs/platform-governance.yaml` |
| `requirements-phase2.txt` | `pyproject.toml` → `[project.optional-dependencies] platform` |
| `.venv-phase2` | `.venv-platform` |
| `outputs/phase2/` | `outputs/evidence/` |
| `infra/phase1-cluster/` | `infra/lakehouse-cluster/` |
| `apps/web/scripts/phase2/` | `apps/web/scripts/platform/` |
| `.github/workflows/phase2-*.yaml` | prefix dropped (directory deleted at P10) |
| ns `phase2-data` | ns `dataflow` |
| ns `phase2-llm` | dissolved into `kserve` |
| ns `monitoring` | ns `observability` |
| Postgres schema `ops` | schema `ops` |
| Postgres schema `ml` | schema `ml` |
| Terraform/GKE label `phase=phase2` | `component=unified-platform` |
| env var `PHASE2_PG_DSN` | `PLATFORM_PG_DSN` |
| env var `PHASE2_REQUIRE_PG` | `PLATFORM_REQUIRE_PG` |
| pytest marker `postgres` | unchanged |
| `docs/evidence/stage1_*.json` | **deleted**, not renamed — regenerated in P12 |

The two-venv rule is retained: `psycopg` and `pyspark` have incompatible transitive pins. Only the
directory name changes.

## Related Code Files

- Rename: all paths in the map above
- Modify: `pyproject.toml` (packages, optional-dependencies, pytest markers, coverage paths)
- Modify: `AGENTS.md` — remove the phase vocabulary; restate verify commands with new script names;
  mark the dedup rule as pending amendment in P2
- Modify: `CLAUDE.md`, `README.md`, `docs/project-file-map.md`
- Modify: `.github/workflows/*.yaml`, `.githooks/pre-commit`, `docker-compose.yml`, `.dockerignore`
- Modify: `financial-distress-gitops` Argo `destination.namespace` fields and Terraform labels
- Create: `scripts/verify_naming_cutover.py`
- Delete: `docs/evidence/stage1_*` (13 files), `docs/phase1/`, `docs/platform/evidence-tree/`

## Implementation Steps

1. **Author the verifier first** (0.5 d) — `scripts/verify_naming_cutover.py` scans the tree for
   `phase1|phase2|stage1|Phase 1|Phase 2` (case-insensitive) in path names and file contents,
   excluding `supabase/migrations/`, `plans/`, `.git/`, `__pycache__/`, `.venv*`, `node_modules/`,
   `mutants/`. Run it now and record the baseline count. It must exit non-zero today.
2. **Rename class A — Python modules and packages** (1 d) — `src/`, `dags/`, `scripts/`, `tests/`.
   Use `git mv`, then a single project-wide identifier update. Run `pytest tests -m "not slow"`.
   Commit atomically.
3. **Rename class B — configs, venv, requirements** (0.5 d) — `configs/`, `requirements-phase2.txt`
   folded into `pyproject.toml`, `.venv-phase2` → `.venv-platform`, env-var names. Update
   `docker-compose.yml` and `.githooks/pre-commit`. Recreate the platform venv from
   `pyproject.toml`. Commit atomically.
4. **Rename class C — SQL schemas** (1 d) — `ops` → `ops`, `ml` → `ml` in
   `sql/init_*.sql` (renamed to `sql/init_ops.sql`, `sql/init_ml.sql`) and in every Python caller.
   Write a forward migration using `ALTER SCHEMA ... RENAME TO ...`. **The physical merge into one
   database, the timestamp conversion, and the foreign keys are P2 work — not here.** Commit atomically.
5. **Rename class D — docs** (1 d) — move `docs/platform/` → `docs/platform/`,
   `docs/phase1_architecture.md` → `docs/architecture/lakehouse.md`; merge the two contradicting
   schema documents into `docs/architecture/data-model.md`, keeping only what the code actually does
   (`02_schema_design.md:205` is the correct one; `schema-design.md:11-14` is not). Delete
   `docs/evidence/stage1_*`, `docs/phase1/`, `docs/platform/evidence-tree/`. Update all cross-links.
   Commit atomically.
6. **Rename class E — GitOps and runtime** (1 d) — in `financial-distress-gitops`: namespace
   renames, Argo `destination.namespace`, Terraform labels, workflow names. `make validate` must
   pass. Commit atomically in that repository.
7. **Rewrite `AGENTS.md`** (0.5 d) — remove the phase split; new verify commands; new directory map;
   record that the dedup rule is amended by P2 and the cross-write ban is revoked.
8. **Exit gate** (0.5 d) — `scripts/verify_naming_cutover.py` exits 0; `pytest tests` passes with
   zero skips; `make validate` passes in GitOps; `docker compose config` validates.

## Success Criteria

- [ ] AC-P1-1: Engineer → runs `scripts/verify_naming_cutover.py` → exits 0; zero matches for
      `phase1|phase2|stage1` in paths or contents outside `supabase/migrations/` and `plans/`
- [ ] AC-P1-2: Engineer → runs `pytest tests` after the cutover → full suite passes with zero skips
- [ ] AC-P1-3: Engineer → runs `scripts/run_quality_gates.py` (renamed) → passes; ruff and black
      clean on `src dags tests scripts`
- [ ] AC-P1-4: GitOps operator → runs `make validate` in `financial-distress-gitops` → passes; no
      Argo Application targets a `phase2-*` namespace
- [ ] AC-P1-5: DBA → connects to Postgres → schemas `ops` and `ml` exist; `ops` and
      `ml` do not; every Python caller resolves against the new names
- [ ] AC-P1-6: Reader → opens `docs/architecture/data-model.md` → finds exactly one statement about
      whether facts carry `company_version_key`, and it matches `src/transforms/gold/`
- [ ] AC-P1-7: Engineer → greps `supabase/migrations/` → filenames unchanged; ADR-019 records the
      exception and its reason
- [ ] AC-P1-8: Reader → opens `AGENTS.md` → finds no platform . platform .ocabulary and correct
      verify commands

## Risk Assessment

**Risk:** a rename breaks an import that only a slow or Docker-gated test exercises. Signal: full
suite green but a runtime job fails in P4. Mitigation: run `pytest tests` (not `-m "not slow"`) as
the exit gate; grep for dynamic imports and string-built module paths before renaming. Response:
revert the single rename-class commit; fix; re-apply.

**Risk:** the Postgres schema rename breaks the live product plane. Signal: web app 500s on
`ops`/`ml` lookups. Mitigation: `ALTER SCHEMA ... RENAME TO ...` is transactional; deploy the code
change and the migration in the same window. Response: rename back — the operation is symmetric.

**Risk:** renaming Supabase migrations corrupts migration tracking. Signal: `supabase db push`
re-applies an already-applied migration. Mitigation: the verifier excludes that directory by path,
and ADR-019 states why. Response: restore filenames from git; never rename applied migrations.

**Risk:** the docs merge silently discards a rubric-cited path. Signal: a rubric row's
`evidence_path` 404s at P3. Mitigation: before deleting, grep `docs/platform/rubric-matrix.csv` for
every path under the directories being moved and record redirects. Response: restore the redirect
table into the merged document.
