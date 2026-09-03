# the platform Evidence Contract

This document defines what counts as proof for every scored rubric row in the
ML and LLM tracks. It is enforced by `scripts/audit_phase2_evidence.py` and
`tests/platform/test_rubric_matrix.py`.

## Evidence Types

| Type | Meaning | Allowed at |
|---|---|---|
| `executed` | proof from a running system (logs, dashboards, manifests) | phase-08 |
| `design_only` | design exists, proof planned, artifact path reserved | phase-01..07 |
| `stretch` | optional non-scored work only; no scored row may remain stretch at submission | any |

## Per-Artifact Requirement

Every evidence artifact under `docs/platform/evidence/` MUST record:

1. `rubric_id` — the semantic ID it proves.
2. `execution_timestamp` — when the scenario ran.
3. `source_sha` — exact 40-hex source repository commit.
4. `gitops_sha` — exact 40-hex GitOps repository commit.
5. `versions` — image digest, model/agent/data version, embedding version.
6. `command` — exact non-interactive reproduction command; an optional
   `scenario` may explain manual setup but never replaces the command.
7. `expected_result` and `actual_result`.
8. `redaction_status` — what was redacted (tokens, emails, private data).

Screenshots supplement machine-readable outputs; they never replace logs,
reports, or manifests when those exist. Every major `docs/platform/` section
explains what its images prove. No orphan screenshot dumps.

## Status Vocabulary

- **Designed** — the design is written and accepted (phase-01).
- **Configured** — infrastructure or code exists but has not been executed for
  evidence.
- **Executed** — a run happened and produced output.
- **Passed** — an automated gate verified the output.

## Frozen the platform Base

`PHASE1_BASE_SHA=ddbcbe7bd41ae4883954b8a247efdc67c7329078`
(`fix(generators): resolve generator package collision`). This is the commit
the strict linter diffs the current source `HEAD` against to prove no the platform
protected path moved; it is frozen because it is the last commit before the platform
work started touching `src/ml/`, `src/drift/`, `src/llm/`, `src/agents/`,
`apps/`, and `dags/platform/`, and it empirically passes the protected-path diff
in every strict run recorded in `plans/260811-1627-close-llm-rubric-to-100/`.

## Linter Checks

```bash
# Phase-01: matrix completeness + no the platform mutation
python scripts/audit_phase2_evidence.py --matrix-only --strict

# Phase-08: evidence files exist, reference their rubric_id
python scripts/audit_phase2_evidence.py --require-executed --run-validations \
  --lakehouse-base "$PHASE1_BASE_SHA" --gitops-root "$GITOPS_CHECKOUT" \
  --ml 100 --llm 100
```

The strict linter fails (exit 1) when: a scored row is missing a contract
field, source row count/digest/points do not exactly match the canonical CSVs,
an acceptance ID cannot resolve, a track does not total 100 points, a rubric
ID looks like a spreadsheet line number, an evidence path leaves
`docs/platform/evidence/`, a the platform protected path is referenced, or an
evidence file is missing at phase-08.

At phase-08 the linter also fails when an executed row's `artifact_path` is
absent from disk (executed proof requires a real implementation), or when any
evidence `source_sha`/`gitops_sha` is not an existing commit or is not a
reachable ancestor of (or equal to) the current source/GitOps checkout `HEAD`
— any commit after an evidence SHA must touch only that evidence file's own
SHA lines under `docs/platform/evidence/`, or the ancestor rule fails the row —
or when the protected the platform diff cannot be verified against the frozen
40-hex `$PHASE1_BASE_SHA`, or when any
evidence metadata key is present with a blank value or a value that cannot be
real: `execution_timestamp` must parse as ISO-8601, and `source_sha` plus
`gitops_sha` must each be an exact 40-hex commit. A key line with no value is
not evidence. Both checkouts must also have clean worktrees, so the recorded
commits contain the implementation, manifests, and evidence being audited.

Each matrix row declares `artifact_repo` (`source` or `gitops`) and a concrete
file `artifact_path`, never a synthetic directory named after the rubric ID.
At Phase 8 the auditor receives a checked-out GitOps root with
`--gitops-root`; the declared artifact must be a file in the correct repo. The
matrix's `test` command checks the mapping contract, while
`validation_command` is the feature-specific behavior/evidence gate and must
collect and execute successfully before the row can be marked `executed`.
Phase 8 passes `--run-validations`; commands are parsed as argv and executed
without a shell after the strict allow-list check.

## the platform Non-Mutation

the platform evidence under `docs/evidence/` is untouched. the platform evidence lives
in a separate namespace `docs/platform/evidence/{ml,llm}/` so the two can never
collide.
