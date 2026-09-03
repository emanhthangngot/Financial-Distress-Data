---
phase: 4
title: "Consolidate container bootstrap under infra"
status: pending
priority: P2
effort: "1-2h"
dependencies: [1]
---

# Phase 4: Consolidate container bootstrap under infra

## Overview

Give every tracked top-level directory a named owner before phase 3 introduces
formal ownership rules. Move the one bootstrap root that is cheap to move
(`init/`), and record ownership for the rest instead of churning them.

## Requirements

- Functional: `init/` no longer exists as a top-level root; its script lives with
  the other container build/bootstrap assets under `infra/`.
- Functional: a committed repository map names the owner and plane of every
  tracked top-level directory.
- Non-functional: no platform .ource file, test assertion, or spec document is
  edited to accommodate a move.

## Architecture

**Moved: `init/` -> `infra/kafka/`.** One tracked file
(`init/kafka_init_topics.sh`), five references, none of them in platform .src/`
code or in a test assertion:

| Reference | Kind |
|---|---|
| `docker-compose.yml:40,59` | bind mount `./init:/opt/financial-distress-init:ro` |
| `docker-compose.yml:60` | `command: bash /opt/financial-distress-init/kafka_init_topics.sh` |
| `README.md:297`, `docs/evidence/README.md:31`, `docs/ui-screenshot-runbook.md:39` | documented `docker compose exec` command |
| `scripts/capture_ui_screenshots.py:24` | the same command inside a docstring |

The in-container path `/opt/financial-distress-init` stays exactly as it is —
only the host-side source directory moves. That keeps all five documented
`docker compose exec` commands correct without touching them.

**Not moved: `sql/`.** The audit that opened this plan proposed moving it; the
evidence rejects it. `sql/` is a hardcoded runtime default in platform .roduction
code and an asserted constant in seven test files:

```
src/catalog/duckdb_runner.py:38,66,73,74     default arg "sql/duckdb_create_views.sql"
src/quality/sql_contract_runner.py:120,129   repo_root / "sql" / ...
tests/test_naming_convention.py:19           REPO_ROOT / "sql" / ...
tests/test_runtime_adapters.py:243           Path("sql/init_ops.sql")
tests/test_runtime_evidence.py:28,36
tests/test_sql_contract_runner.py:21
tests/test_stage1_jobs.py:109
tests/test_secrets_no_defaults.py:19         SCAN_DIRS includes "sql"
tests/platform/test_rubric_matrix.py:33        allowlist entry "sql/"
scripts/audit_phase2_evidence.py:61          allowlist entry "sql/"
```

plus ~10 references in `docs/mini_coursework.md`, `docs/02_schema_design.md` and
`docs/01_data_generator.md` — and `docs/mini_coursework.md` is the platform .pec,
which per AGENTS.md wins over any layout preference. Moving `sql/` means editing
platform .ode paths and the spec to accommodate cosmetics. Rejected: `sql/` at a
data project's root is a defensible convention, and it gets an explicit owner in
the repository map instead.

**Not moved: `configs/`, `images/`, `scripts/`.** Same reasoning at lower
intensity — each is referenced by rubric evidence paths in
`scripts/_rubric_items.py`. They get map entries, not moves.

**New: `docs/architecture/repository-map.md`.** One table, every tracked
top-level directory, its owner, its plane (platform .ocal lakehouse / Phase 2
product / platform .vidence / shared tooling / documentation), and whether it is
generated. This is the source-repo counterpart to the `resource-ownership.yaml`
that phase 3 introduces in the GitOps repo, and it is what makes "unowned
directory" a detectable condition rather than a vibe.

## Related Code Files

- Create: `infra/kafka/kafka_init_topics.sh` (moved from `init/kafka_init_topics.sh`)
- Create: `docs/architecture/repository-map.md`
- Modify: `docker-compose.yml:40,59` (mount source path only)
- Modify: `README.md` project-tree block (~lines 150-172)
- Delete: `init/`

## Implementation Steps

1. `git mv init/kafka_init_topics.sh infra/kafka/kafka_init_topics.sh`; remove
   the emptied `init/`. Keep the filename — five documented commands reference
   it by name inside the container.
2. In `docker-compose.yml`, change both mount sources from `./init` to
   `./infra/kafka`. Leave the container path `/opt/financial-distress-init` and
   the `command:` line untouched.
3. Confirm the script's exec bit survived the move (`git ls-files -s` shows
   mode `100755`); if it did not, `chmod +x` and re-add.
4. Update the README project-tree block: drop the `init/` line, add
   `infra/` with its three subdirectories (`airflow/`, `flink/`, `kafka/`).
   If phase 2 already landed, `infra/flink/` is a live build context — say so.
5. Write `docs/architecture/repository-map.md`. One row per entry in
   `git ls-files | awk -F/ '{print $1}' | sort -u`. Columns: path, owner
   (role, per AGENTS.md's role-based convention: `data_engineer`,
   `ml_engineer`, `llm_engineer`, `platform_operator`, `product_engineer`),
   plane, generated?, and a one-line "what lives here". Mark `docs/evidence/**`
   and `warehouse.db` as generated-do-not-hand-edit, matching AGENTS.md.
6. Link the map from the README documentation section and from
   `docs/architecture/` alongside `deployment.mmd`.
7. Verify:
   ```bash
   docker compose config >/dev/null
   git grep -n "\./init\b" -- ':!plans' ':!docs/evidence'   # must return nothing
   git ls-files | awk -F/ '{print $1}' | sort -u            # cross-check every row exists in the map
   .venv/bin/python scripts/run_stage1_quality_gates.py
   ```

## Success Criteria

- [ ] Maintainer -> lists tracked top-level entries -> every one has a row in
      `docs/architecture/repository-map.md` with a named owner role.
- [ ] `docker compose config` -> exits 0 with the kafka-init mount resolving to
      `./infra/kafka`.
- [ ] Operator -> runs the documented
      `docker compose exec kafka bash /opt/financial-distress-init/kafka_init_topics.sh`
      -> unchanged, because only the host path moved.
- [ ] `git grep "./init"` -> zero hits outside `plans/` and `docs/evidence/`.
- [ ] `scripts/run_stage1_quality_gates.py` -> same result as the phase-1 baseline.

## Risk Assessment

- Risk: the executable bit is lost in the move and the kafka-init container fails
  at `bash <script>`. Mitigation: step 3; and the `command:` invokes `bash <path>`
  explicitly, so the mode is belt-and-braces rather than load-bearing.
- Risk: `docs/evidence/final/**/compose.yaml` snapshots still say `./init`.
  Mitigation: leave them alone — they are frozen generated evidence of a past
  run (AGENTS.md: do not hand-edit `docs/evidence/**`). The verify grep excludes
  that tree deliberately.
- Risk: the repository map rots. Mitigation: it is one table with a one-command
  cross-check (step 7); phase 6 is the natural place to add a test asserting
  every top-level dir has a row, if it proves worth automating.
- Rollback: `git revert`; single commit, no runtime state involved.
