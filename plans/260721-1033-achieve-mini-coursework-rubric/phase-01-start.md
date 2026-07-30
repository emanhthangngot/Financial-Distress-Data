---
phase: 1
title: "Rubric Contract And Evidence Foundation"
status: completed
priority: P1
effort: "2-3 days"
dependencies: []
---

# Phase 1: Rubric Contract And Evidence Foundation

## Overview

Turn the CSV rubric into an executable submission contract before expanding the platform.

## Requirements

- One registry row for every scored rubric item, totaling 100 points.
- Each row records implementation, test, proof type, document, and status.
- Evidence package must enforce one run ID, Git SHA, config hash, and artifact hashes.

## Related Code Files

- Create: `configs/rubric-requirements.yaml`
- Create: `scripts/audit_mini_coursework_rubric.py`
- Create: `src/evidence/run_manifest.py`
- Modify: `scripts/run_stage1_real_e2e.py`
- Modify: `.gitignore`
- Create: `docs/evidence-index.md`

## Implementation Steps

1. Normalize the multiline CSV into stable rubric IDs outside runtime comments/tests.
2. Define accepted proof types: screenshot, metrics JSON, UI export, query output, code reference.
3. Implement a run manifest and reject mixed-run evidence.
4. Permit curated screenshots under a documented evidence path.
5. Add an audit command that reports verified, partial, missing, and stale points.

## Task Breakdown

| ID | Task | Validation | Evidence/output |
|---|---|---|---|
| P1-T1 | Parse CSV into 45 stable criteria and preserve original text/points | Unit test total=100 and IDs unique | `configs/rubric-requirements.yaml` |
| P1-T2 | Define evidence schema and allowed proof types | JSON-schema/contract tests | Evidence schema document |
| P1-T3 | Implement `RunManifest` with Git SHA, config hash, timestamps and artifact hashes | Hash mutation and mixed-run tests | `run-manifest.json` |
| P1-T4 | Extend evidence auditor to score rubric criteria | Golden complete/incomplete package tests | Machine-readable score report |
| P1-T5 | Create evidence index generator | Link existence test | `docs/evidence-index.md` |
| P1-T6 | Fix ignore rules and evidence directories | `git check-ignore` tests/commands | Trackable screenshot structure |

## Validation

```bash
python -m pytest -q tests/test_rubric_audit.py tests/test_run_manifest.py
python scripts/audit_mini_coursework_rubric.py --evidence-dir docs/evidence
git check-ignore -v docs/evidence/screenshots/example.png
```

The final `git check-ignore` command must report the file as not ignored.

## Success Criteria

- [x] Rubric audit totals exactly 100 points.
- [x] Missing one required artifact fails only its mapped criterion and final gate.
- [x] Mixing artifacts from two run IDs fails.
- [x] Evidence index links every submitted artifact to its scored criterion.

## Risks And Rollback

Do not encode optimistic status defaults. Keep the existing evidence audit available until the replacement covers all current checks.

## Unresolved Questions

- Exact instructor naming preference for screenshot folders.
- Whether manual reviewer confirmation may mark a row complete or every row must have a machine check.
