# ADR-019: Naming cutover and its two exceptions

## Status

Accepted — 2026-09-03 (`plans/260831-1644-rebuild-target-mlops-architecture/phase-01-naming-cutover.md`).
Implemented — merged to `dev` via PR #91, 2026-09-05.

## Context

The two-plane split this rebuild erases (Phase 1 `ops`/`ops` vs. Phase 2
`ml`/platform) was embedded in the data layer (two Postgres schemas
forbidden to reference each other), the test layer (`tests/platform/`), DAG
orchestration (`dags/phase2/`), and Kubernetes namespaces (`phase2-data`,
`phase2-llm`). O-3 ("no `phase1`/`phase2`/`stage1` vocabulary in any path,
identifier, namespace, or schema name") is unachievable while any of that
remains, and it keeps the two-schema foreign-key gap (D-12) permanent.

## Decision

Every `phase1`/`phase2`/`stage1` token is removed from paths, directory
names, Python identifiers, Kubernetes namespaces, Postgres schema names,
Argo `destination.namespace` fields, Terraform labels, and documentation
prose — with exactly two recorded exceptions, enforced by
`scripts/verify_naming_cutover.py`:

| Exception | Reason |
|---|---|
| `supabase/migrations/*_phase2_*.sql` and `migrations/rollback/*` | Applied-migration filenames are keys in `supabase_migrations.schema_migrations`. Renaming re-applies or orphans migrations against the live product-plane database. |
| `plans/**` | Historical planning records. Rewriting them destroys the decision trail this ADR itself depends on. |

A third, narrower exception exists in practice but is not a rule exception:
**`.github/workflows/*.yaml`** still carry pre-cutover paths and prefixes.
This is not a design choice — the token used for this rebuild lacks the
`workflow` OAuth scope required to push changes to `.github/workflows/`
(verified: every attempted push to a modified workflow file is rejected by
GitHub). `scripts/verify_naming_cutover.py` counts these separately
("deferred (workflows): N (P10 scope / token lacks workflow scope)") rather
than silently excluding them, so the gap stays visible instead of
disappearing into a passing exit code. Phase 10 (`.github/workflows/`
deletion, Jenkins cutover) is the first phase with the access this requires.

## Consequences

- `scripts/verify_naming_cutover.py` exits 0 against the source tree today
  (0 path-name matches, 0 content matches, 90 deferred workflow hits
  recorded separately) — verified 2026-09-05.
- GitOps namespace renames (`phase2-data` → `dataflow`, `phase2-llm`
  dissolved into `kserve`, `monitoring` → `observability`) live in the
  separate `financial-distress-gitops` repository, not checked out in this
  workspace — confirmed still outstanding: the live cluster
  (`fsds-evidence`, `asia-southeast1-b`) still runs a `phase2-data`
  namespace as of 2026-09-05.
- Every rename landed as one atomic commit per class (A: Python
  modules/packages; B: configs/venv/requirements/env-vars/docker-compose; C:
  SQL schemas; D: docs; E: GitOps/runtime — blocked, see above) so any single
  class is independently revertible.

## Alternatives Considered

- **Rename applied Supabase migration filenames** (rejected — `supabase db
  push` would re-apply or orphan them against the live product-plane
  database; the risk is not proportional to a cosmetic rename).
- **Rewrite `plans/**` to remove historical `phase1`/`phase2` mentions**
  (rejected — the plans are the record of *why* decisions were made; erasing
  the vocabulary they were made against erases the reasoning, not just the
  spelling).
- **Grant the token `workflow` scope now** (not this session's decision to
  make — flagged for the user/operator; until granted, workflow renames
  wait for Phase 10, consistent with the phase's own `owns:`
  `.github/workflows/` scope).
