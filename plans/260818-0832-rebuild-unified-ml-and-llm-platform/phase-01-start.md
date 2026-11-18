---
title: "Phase 1: Lock The Unified Contract And Purge Evidence"
status: todo
priority: P1
effort: "1 week"
dependencies: []
---

# Phase 1: Lock The Unified Contract And Purge Evidence

## Overview

Rebuild the rubric contract before rebuilding anything it governs: one 161-row
matrix covering mini-coursework + ML + LLM, one phase-free evidence tree, one
auditor. Delete every existing evidence artifact so no stale proof can be mistaken
for a regenerated one. Submit the GCP quota increase on day 1 because approval
latency (1-3 days) sits on the critical path for phase 4.

## Requirements

Functional:
- [ ] A single `docs/rubric-matrix.csv` generated from all three rubric CSVs, totalling 161 rows / 300 points
- [ ] Every row carries `rubric_id`, `track`, `section`, `points`, `requirement`, `proof`, `validation_command`, `evidence_path`, `artifact_repo`, `artifact_path`, `acceptance_id`
- [ ] `scripts/audit_rubric_evidence.py` replaces `audit_phase2_evidence.py` and `audit_mini_coursework_rubric.py`
- [ ] All evidence under `docs/evidence/` and `docs/platform/evidence/` deleted; new empty tree keyed by rubric section
- [ ] GCP quota increase request for `CPUS_ALL_REGIONS` submitted and tracked (target 48)
- [ ] Domain registered, nameservers pointed at Cloudflare, zone resolving, scoped API token created and stored in the secret path Vault will serve

Non-functional:
- [ ] The auditor runs in under 30 s in matrix-only mode so it is usable as a pre-commit gate
- [ ] No path in the repository contains a `phase1`, `phase2`, `stage1` or `mini_coursework` evidence prefix

## Architecture

The old contract encoded the phase split in three places: two auditors, two
evidence roots, and the `--track` filter that existed only to let one track be
submitted without the other. All three disappear. `--track` survives as a
reporting convenience, not as a gate that lets a track go unscored.

Evidence path shape:

```
docs/evidence/
  engineering-fundamentals/<rubric_id>.md
  data-generator/<rubric_id>.md
  processing-jobs/<rubric_id>.md
  data-storage/<rubric_id>.md
  feature-store/<rubric_id>.md
  ml/<rubric_id>.md
  ml-pipelines/<rubric_id>.md
  versioning/<rubric_id>.md
  rag/<rubric_id>.md
  agents/<rubric_id>.md
  ci-cd/<rubric_id>.md
  routing-gateway/<rubric_id>.md
  iac/<rubric_id>.md
  observability/<rubric_id>.md
  ab-testing/<rubric_id>.md
  security/<rubric_id>.md
  repository-design/<rubric_id>.md
  documentation/<rubric_id>.md
  novel-ideas/<rubric_id>.md
```

Section slugs derive from the rubric CSVs' own section column, so the tree is
regenerable rather than hand-curated.

## Related Code Files

- Create: `scripts/generate_rubric_matrix.py`, `scripts/_rubric_rows.py`, `scripts/audit_rubric_evidence.py`, `docs/rubric-matrix.csv`, `docs/rubric-matrix.md`, `docs/evidence-contract.md`
- Modify: `AGENTS.md` (drop the phase-scope section, replace read order), `CLAUDE.md`
- Delete: `scripts/audit_phase2_evidence.py`, `scripts/audit_mini_coursework_rubric.py`, `scripts/_phase2_rubric_items.py`, `scripts/_rubric_items.py`, `scripts/generate_phase2_matrix.py`, `docs/platform/rubric-matrix.{csv,md}`, `docs/evidence/**`, `docs/platform/evidence/**`, `docs/submission/**`

## Implementation Steps

1. Submit the GCP `CPUS_ALL_REGIONS` quota increase (target **48**) before any other work. Record the case ID in `docs/evidence-contract.md`.
2. **Register the domain and point its nameservers at Cloudflare on day 1**, alongside the quota request — both have lead times measured in hours to days and both block phase 4. Create a Cloudflare API token scoped to DNS edit for that zone only. Verify the zone resolves before phase 4 starts; do not discover a propagation problem while provisioning.
3. Write `scripts/_rubric_rows.py` parsing all three rubric CSVs into one row list, deriving stable `rubric_id` values as `<track>-<section-slug>-<row-slug>` and a `source_digest` per row so rubric drift is detectable.
4. Write `scripts/generate_rubric_matrix.py` emitting `docs/rubric-matrix.csv` + a human-readable `docs/rubric-matrix.md`. Assert the totals: 161 rows — mini 44 / 100 pts, ML 57 / 100 pts, LLM 60 / 100 pts. The three rubrics are separate 100-point scales; do not fold mini rows into the ML or LLM sections, and do not sum the three into a single percentage.
5. Write `scripts/audit_rubric_evidence.py` with modes `--matrix-only`, `--check-artifacts`, `--require-executed`, `--run-validations`, `--strict`, `--gitops-root`. Port the artifact-existence and clean-worktree checks from the old auditor; drop the phase-base-SHA machinery and the design-only allowance entirely.
6. Delete the old auditors, matrix generators, both evidence roots and `docs/submission/`. Commit the deletion as its own commit so the purge is auditable.
7. Regenerate the empty section tree with a `.gitkeep` per section directory.
8. Rewrite `AGENTS.md`: remove `## Phase Scope`, rewrite `## Read Order` to point at `docs/rubric-matrix.md` + `docs/evidence-contract.md`, keep the data-contract and verify-command sections.
9. Wire the matrix-only audit into `scripts/run_stage1_quality_gates.py` (rename to `scripts/run_quality_gates.py`) so a drifted matrix fails the standard gate.

## Success Criteria

- [ ] `python scripts/generate_rubric_matrix.py` produces 161 rows; re-running is a no-op (deterministic output)
- [ ] `python scripts/audit_rubric_evidence.py --matrix-only --strict` exits 0
- [ ] `python scripts/audit_rubric_evidence.py --require-executed --strict` exits non-zero listing all 161 rows as unexecuted (proves the purge and the gate both work)
- [ ] `grep -rIl "phase2/evidence\|docs/evidence/stage1\|mini_coursework" --exclude-dir=.git .` returns nothing outside the rubric CSVs themselves
- [ ] GCP quota case ID recorded with its submission date
- [ ] `dig <domain> NS` returns Cloudflare nameservers
- [ ] `python scripts/run_quality_gates.py` passes

## Risk Assessment

- **The quota increase is denied.** Free-trial accounts are frequently capped. Mitigation: submit day 1; if denied by end of week 1, fall back to the time-slicing strategy (label-driven Argo ApplicationSet with `track=ml`/`track=llm` and scale-to-zero for the idle track) and add ~1.5 weeks to the schedule. This fallback must be decided before phase 4 starts, not during it.
- **Deleting evidence is irreversible.** Mitigation: tag the current HEAD as `pre-rebuild-evidence-snapshot` and push the tag before the purge commit. The tag is a rollback path, not a submission path.
- **Domain or DNS lead time blocks phase 4.** Registration, nameserver delegation and propagation are hours-to-days and cannot be compressed. Mitigation: day 1, same as the quota request. `distresslens.duckdns.org` stays live as a fallback until the new zone issues a wildcard certificate successfully.
- **Rubric ID churn breaks later phases.** Mitigation: freeze `rubric_id` derivation in step 2 and cover it with a fixture test before any evidence is written against those IDs.
