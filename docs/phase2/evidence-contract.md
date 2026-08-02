# Phase 2 Evidence Contract

This document defines what counts as proof for every scored rubric row in the
ML and LLM tracks. It is enforced by `scripts/audit_phase2_evidence.py` and
`tests/phase2/test_rubric_matrix.py`.

## Evidence Types

| Type | Meaning | Allowed at |
|---|---|---|
| `executed` | proof from a running system (logs, dashboards, manifests) | phase-08 |
| `design_only` | design exists, proof planned, artifact path reserved | phase-01..07 |
| `stretch` | optional stretch goal, not required for 100/100 | any |

## Per-Artifact Requirement

Every evidence artifact under `docs/phase2/evidence/` MUST record:

1. `rubric_id` — the semantic ID it proves.
2. `execution_timestamp` — when the scenario ran.
3. `source_sha` — source repository commit.
4. `gitops_sha` — GitOps repository commit (evidence plane only).
5. `versions` — image digest, model/agent/data version, embedding version.
6. `command` or `scenario` — exactly how to reproduce.
7. `expected_result` and `actual_result`.
8. `redaction_status` — what was redacted (tokens, emails, private data).

Screenshots supplement machine-readable outputs; they never replace logs,
reports, or manifests when those exist. Every major `docs/phase2/` section
explains what its images prove. No orphan screenshot dumps.

## Status Vocabulary

- **Designed** — the design is written and accepted (phase-01).
- **Configured** — infrastructure or code exists but has not been executed for
  evidence.
- **Executed** — a run happened and produced output.
- **Passed** — an automated gate verified the output.

## Linter Checks

```bash
# Phase-01: matrix completeness + no Phase 1 mutation
python scripts/audit_phase2_evidence.py --matrix-only --strict

# Phase-08: evidence files exist, reference their rubric_id
python scripts/audit_phase2_evidence.py --require-executed --ml 100 --llm 100
```

The strict linter fails (exit 1) when: a scored row is missing a contract
field, a track does not total 100 points, a rubric ID looks like a spreadsheet
line number, an evidence path leaves `docs/phase2/evidence/`, a Phase 1
protected path is referenced, or an evidence file is missing at phase-08.

At phase-08 the linter also fails when an executed row's `artifact_path` is
absent from disk (executed proof requires a real implementation), or when any
evidence metadata key is present with a blank value or a value that cannot be
real: `execution_timestamp` must parse as ISO-8601, and `source_sha`/`gitops_sha`
must be a git SHA (40-hex, or a short SHA) or a plausible ref. A key line with
no value is not evidence.

## Phase 1 Non-Mutation

Phase 1 evidence under `docs/evidence/` is untouched. Phase 2 evidence lives
in a separate namespace `docs/phase2/evidence/{ml,llm}/` so the two can never
collide.
