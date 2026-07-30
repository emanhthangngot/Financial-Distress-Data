---
phase: 9
title: "Run Submission Evidence And Mock Grading"
status: completed
priority: P1
effort: "3-5 days"
dependencies: [1, 2, 3, 4, 5, 6, 7, 8]
---

# Phase 9: Run Submission Evidence And Mock Grading

## Overview

Run the complete system from a clean state and verify every rubric point without relying on historical artifacts.

## Requirements

- Clean-room setup on documented prerequisites.
- One correlated run ID and immutable evidence package.
- Automated gates plus manual UI proof checklist.
- Independent mock grading totals 100/100 before submission claim.

## Related Code Files

- Create: `scripts/run_mini_coursework_submission.py`
- Create: `scripts/verify-clean-room-setup.sh`
- Update: `docs/evidence-index.md`
- Store curated proof under the approved evidence structure

## Implementation Steps

1. Reset only disposable coursework state using documented commands.
2. Build images and record sizes/digests.
3. Run generator, DP1, DP2, DP3, Spark benchmark, Flink benchmark, DQ failure cases, and DataHub ingestion.
4. Export metrics, manifests, SQL results, logs, and screenshots.
5. Run unit, integration, branch coverage, lint, formatting, Compose, service, and evidence gates.
6. Execute rubric audit and inspect every linked artifact manually.
7. Perform a second clean setup rehearsal or independent reviewer walkthrough.

## Submission Runbook

| Step | Command family | Required artifact |
|---|---|---|
| 1 | Clean checkout/config validation | Environment manifest |
| 2 | Build Compose profiles/images | Image digests and sizes |
| 3 | Generate offline/stream problems | Generator metrics/config |
| 4 | Execute DP1/DP2/DP3 | Airflow logs/screenshots |
| 5 | Execute Spark/Flink benchmarks | UI captures + metric JSON |
| 6 | Ingest/verify DataHub metadata | Lineage/contracts/assertions |
| 7 | Execute DQ and negative probes | Failure evidence |
| 8 | Build schema evidence | `warehouse.db` + DBeaver captures |
| 9 | Generate evidence index and score | 100/100 audit report |

## Task Breakdown

| ID | Task | Exit condition |
|---|---|---|
| P9-T1 | Add preflight for CPU/RAM/disk/ports/dependencies | Clear actionable pass/fail |
| P9-T2 | Run clean evidence profile with new run ID | All services and pipelines pass |
| P9-T3 | Capture UI evidence using fixed checklist | No missing/ambiguous screenshots |
| P9-T4 | Verify hashes/run correlation and repository tracking | No stale/ignored/untracked proof |
| P9-T5 | Run full automated gates and coverage | Zero failures; coverage claim accurate |
| P9-T6 | Run rubric scorer | 100/100, zero partial rows |
| P9-T7 | Perform independent/manual mock review | Every artifact opens and supports claim |
| P9-T8 | Freeze final manifest and evidence index | Immutable submission package |

## Validation

```bash
bash scripts/verify-clean-room-setup.sh
python scripts/run_mini_coursework_submission.py --profile evidence --run-id <new-id>
python scripts/audit_mini_coursework_rubric.py \
  --evidence-dir docs/evidence/final/coursework-final-20260731T0030 \
  --require-score 100
python scripts/stage1_readiness_report.py --include-services --include-quality-gates
git status --short
```

## Failure Policy

- Any failed automated check blocks the score claim.
- Any manual-only row remains partial until reviewed and linked.
- Never patch evidence JSON by hand.
- Rerun with a new run ID after code/config changes; do not mix packages.

## Success Criteria

- [x] All automated gates pass after clean-room prerequisite validation.
- [x] Every screenshot includes enough application and entity context for review.
- [x] Every accepted artifact is tracked, hash-verified, and bound to the submission run.
- [x] Rubric audit reports 100/100 with no partial rows or package errors.
- [x] README setup and evidence commands reproduce and validate the package.

## Risks And Rollback

Do not overwrite the final evidence package in place. Publish by run ID, validate, then promote the accepted package to the submission index.

## Completion

Completed on 2026-07-31 ICT. Automated mock grading and an artifact-by-artifact
manual walkthrough passed. Formal grading remains the instructor's decision.
