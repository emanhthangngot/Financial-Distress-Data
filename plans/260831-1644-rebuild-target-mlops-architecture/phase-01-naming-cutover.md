---
phase: 1
title: "Phase 1: Unified naming cutover"
status: pending
priority: P1
effort: "4-6 days"
dependencies: ["phase-00-gates.md"]
owns: ["ALL renames — runs alone, no other phase may be in flight", "scripts/verify_naming_cutover.py"]
---

# Phase 1: Remaining naming cutover

## Overview

Audit residual names before renaming anything. Prior maps contain no-ops (`ops` -> `ops`,
`docs/platform` -> itself) and stale paths; those are not migrations. Preserve behavior, existing
Supabase auth and working CI. Physical schema changes and v2 temporal behavior belong to P2.
Run this phase alone during cross-file renames. Local P0 inventory suffices; cloud may remain blocked.

## Requirements

Remove residual phase/stage product vocabulary from active source paths, identifiers, deployment
labels and current docs only where a real legacy name remains. Do not remove the description of
v1/v2 migration state from AGENTS until code has actually cut over. Keep applied migration filenames,
historical plans, immutable evidence and dependency/cache/generated trees outside this cleanup.
Do not rename `ops` or `ml`; both schemas remain and P2 unifies their database and constraints.
Retain `.venv` and existing gate entry point unless an actual conflict justifies changing them.

## Related files

Inventory `src/`, `dags/`, scripts, configs, tests, current docs and GitOps references. Preserve
`supabase/migrations/` applied names and historical `plans/`. The naming verifier owns the documented
active-scope exclusions; exclusions are not permission to preserve active duplicate implementations.

## Implementation steps

1. Inventory actual legacy names and imported/string-based consumers, producing old/new/reason and
   owner columns. Already-correct paths are marked unchanged, not renamed to themselves.
2. Resolve symbol references with LSP; rename one class of paths atomically, update dynamic imports,
   test/coverage settings and packaging in the same change; no compatibility aliases.
3. Update deployment labels/names only with a P6-reviewed migration and resource impact plan.
4. Reconcile current docs, links and verify commands after source renames. No broad deletion of
   evidence: baseline tag must resolve and replacements must be attributable before removal.
5. Run naming verification, targeted affected tests, full one-shot quality gate and GitOps validation
   if its files changed. Explain environment-dependent skips rather than promising zero skips on
   a machine that lacks required services; graded runtime tests require a capable execution window.

## Success criteria

- [ ] AC-P1-1: Naming verifier -> scans active project surfaces with explicit exclusions -> no unintended phase/stage names or duplicate legacy path remains.
- [ ] AC-P1-2: Engineer -> runs affected regressions and full quality gate -> behavior unchanged and failures resolved; required runtime checks not bypassed by skips.
- [ ] AC-P1-3: Engineer -> runs `.venv/bin/python scripts/run_lakehouse_quality_gates.py` -> current documented entry point passes; any necessary rename migrates every caller first.
- [ ] AC-P1-4: GitOps operator -> validates changed manifests -> namespaces resolve and no destructive resource recreation is hidden in a naming change.
- [ ] AC-P1-5: DBA -> inspects schema inventory -> `ops` and `ml` retained; no no-op ALTER SCHEMA and no v2 behavior bundled into renames.
- [ ] AC-P1-6: Reader -> follows current architecture/schema links -> source-consistent description, v1/v2 migration boundary explicit.
- [ ] AC-P1-7: Engineer -> compares applied migration inventory -> filenames unchanged and exceptions documented in ADR-019.
- [ ] AC-P1-8: Reader -> follows AGENTS verify commands -> commands resolve and rules describe actual current phase, not prematurely completed migration.

## Risks

Dynamic imports evade simple text renames; resolve imports and exercise real affected entry points.
Namespace renames recreate resources; preserve volumes, secret references and rollback ownership.
Historical evidence is immutable provenance, not trash. No CI/auth replacement is authorized here.

