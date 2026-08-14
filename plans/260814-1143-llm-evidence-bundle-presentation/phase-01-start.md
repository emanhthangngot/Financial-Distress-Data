---
phase: 1
title: "Build the LLM validation-verification bundle"
status: completed
priority: P2
effort: "0.5d"
dependencies: []
---

# Phase 1: Build the LLM validation-verification bundle

## Overview

Package the 5 already-captured LLM validation-verification evidence rows into
one RecSys-shaped bundle (`docs/phase2/evidence/llm/validation-verification/`)
and append a "Current Production Sources" table to the existing evidence
README. No new commands run — every number below was already captured and
evidence-stamped on 2026-08-10; this phase only re-presents it.

## Requirements

- Functional: bundle README matches RecSys's section order (Coverage,
  Required Proof, Screenshot Checklist, Mutation Summary, Locust Summary);
  standalone `mutation-summary.md`/`locust-sla-summary.md` match RecSys's
  exact field list; `docs/phase2/evidence/README.md`'s existing prose is
  untouched, only appended to.
- Non-functional: zero new `artifact_path`/`evidence_path` entries added to
  `docs/phase2/rubric-matrix.csv` (these are presentation files, not new
  rubric evidence — adding them as row artifacts would require touching the
  frozen matrix digest for no rubric benefit); strict `--track LLM` gate
  identical before/after.

## Source data (already captured, read this session — do not re-run)

| Metric | Value | Source |
|---|---|---|
| Line coverage | 96.17% (352/366) | `docs/phase2/evidence/llm/LLM-validation-verification-validation-verification.md` |
| Branch coverage | 93.48% (43/46) | same file |
| Mutation score | 86.11% (62 killed / 9 survived / 1 timeout / 72 total), scope `llm.rag.chunking.*` | `docs/phase2/evidence/llm/LLM-validation-verification-c-s-d-ng-mutation-testing-nh-g.md`, `plans/260809-2039-complete-phase2-llm-submission/reports/phase05-mutation-summary.json` |
| Idempotency | 2 passed, Hypothesis-generated cases, 0 flaky | `docs/phase2/evidence/llm/LLM-validation-verification-idempotency-testing-s-d-ng-pro.md` |
| Equivalence/boundary | 19 passed (combined suite) | `docs/phase2/evidence/llm/LLM-validation-verification-c-s-d-ng-k-thu-t-equivalence-p.md` |
| Locust load test | 1352 requests, 0 failures, median 51ms, p95 140ms, p99 330ms, throughput 15.06 req/s, 20 concurrent users, against live `feature-mcp` via `https://distresslens.duckdns.org` | `docs/phase2/evidence/llm/LLM-validation-verification-load-test-the-web-api.md`, raw artifacts `docs/phase2/evidence/llm/locust-report.html` + `locust_stats.csv` |
| 5 real bugs found and fixed during the live load-test run | gateway route mismatch, Locust `with`-block bug, wrong Feast feature-view name, orphaned `hello-web` Ingress, missing basic-auth secret/TLS cert | same load-test evidence file, "Real bugs found and fixed" section |

## RecSys reference format (fetched verbatim from pinned commit `e99df9d1`, not recalled)

`docs/submission/rubic-final-coursework-(final-ml)/validation-verification/README.md`:

```markdown
# Validation & Verification Evidence

## Coverage

| Component | Line coverage |
| --- | ---: |
| api | 95.44% |
...

## Required Proof

- Web API unit tests use `TestClient`, pytest fixtures, and mocked ... services ([file (line N)](path#LN), ...).
- ...
- Mutation score: 90.74%.
- Locust HTML SLA report: archived `locust-api.html`.

## Screenshot Checklist

- `screenshots/coverage-api.png`: terminal coverage output showing `>90%`.
- ...

## Mutation Summary

# Mutation Testing
- Mutation score: 90.74%
- Gate: > 80.00%
- Killed: 49
- Survived: 5
- Timeout: 0
- Suspicious: 0
- No tests: 0
- Targets: <files>
- Mutant filters: <filters>

## Locust Summary

# Locust Web API SLA
- Host: Aggregated
- Requests: 729
- Failures: 0
- Failure rate: 0.00%
- Throughput: 38.33 req/s
- p95 latency: 39.00 ms
- SLA: failure rate 0%, p95 < 1000 ms, throughput >= 5 req/s
- Result: PASS
```

Standalone `mutation-summary.md` / `locust-sla-summary.md` repeat the same
field list as their own top-level `.md` file (no `## Mutation Summary` /
`## Locust Summary` heading wrapper — that wrapper only exists inside the
bundled README).

## Improvements over the RecSys reference (deliberate, not a copy)

1. **Required Proof links to reproducible evidence, not just test source
   lines.** RecSys links to `test_file.py#L18`. Ours links to both the test
   source *and* the canonical `LLM-validation-verification-*.md` evidence
   file carrying the `command`, `expected_result`, `actual_result`, and a
   real command-output transcript — a second, independently reproducible
   trail RecSys's bundle does not have.
2. **Keep the "Real bugs found and fixed" log.** RecSys's Locust section is
   numbers only. Ours keeps the 5-bug list from the real run (gateway route,
   Locust `with`-block, wrong Feast view, orphaned Ingress, missing
   secret/cert) — this is the difference between "we ran a load test" and
   "we ran it against the live gateway and it initially didn't work."
3. **No invented screenshots.** RecSys's checklist names 6 PNGs. We do not
   have PNGs for this row set (HTML/CSV/JSON artifacts instead) — the
   checklist below names the real artifacts we have rather than listing
   screenshots that were never captured.

## Related Code Files

- Create: `docs/phase2/evidence/llm/validation-verification/README.md`
- Create: `docs/phase2/evidence/llm/validation-verification/mutation-summary.md`
- Create: `docs/phase2/evidence/llm/validation-verification/locust-sla-summary.md`
- Modify: `docs/phase2/evidence/README.md` — append "Current Production Sources" table only; existing content byte-identical above it

## Current Production Sources table (content for the README append)

| Concern | Authoritative source |
|---|---|
| Rubric matrix (source of truth for all 60 LLM rows) | `docs/phase2/rubric-matrix.csv` |
| Evidence contract + strict gate logic | `scripts/audit_phase2_evidence.py` |
| Evidence capture checklist (commands + claims) | `configs/evidence-checklist.yaml` |
| Deployable image catalog (build source of truth) | `configs/phase2-deployables.yaml` |
| Shared build/sign CI workflow | `.github/workflows/phase2-ci.yaml` |
| GitOps offline validation gate | `financial-distress-gitops/scripts/validate-gitops.sh` |
| GitOps control-repo rules | `financial-distress-gitops/AGENTS.md` |
| Feature-pull / drift-detection Web APIs | `apps/feature-mcp/`, `apps/drift-mcp/` |
| RAG ingest / stream-feature jobs | `infra/rag-pipeline/`, `infra/stream-feature-offline/`, `infra/stream-feature-online/` |
| Public gateway routes | `financial-distress-gitops/platform/ingress/routes-ui.yaml` |
| Validation & verification evidence bundle | `docs/phase2/evidence/llm/validation-verification/README.md` |

## Implementation Steps

1. Create `docs/phase2/evidence/llm/validation-verification/mutation-summary.md`
   with RecSys's exact field list, populated from the mutation source-data row
   above.
2. Create `docs/phase2/evidence/llm/validation-verification/locust-sla-summary.md`
   with RecSys's exact field list. Compute `Failure rate` (0/1352 = 0.00%),
   pick an explicit SLA statement consistent with the actually-measured
   numbers (p95 140ms comfortably under a 1000ms bar; throughput 15.06 req/s
   over a >=5 req/s bar) — do not silently adopt RecSys's numeric SLA
   thresholds without checking they make sense against real numbers.
3. Create `docs/phase2/evidence/llm/validation-verification/README.md`:
   Coverage table (single LLM Web API row, not per-microservice — we have one
   deployable family here, not RecSys's 11 components), Required Proof
   (5 bullets, each linking test source *and* the canonical evidence file),
   artifact checklist (real HTML/CSV/JSON files, not invented screenshots),
   embedded Mutation Summary + Locust Summary sections copying the two
   standalone files' content, and the "Real bugs found and fixed" list.
4. Append the Current Production Sources table (content above) to
   `docs/phase2/evidence/README.md`. Read the file first, append only —
   verify with `git diff` that every line above the new section is unchanged.
5. Verify no rubric row was touched: `git diff docs/phase2/rubric-matrix.csv`
   must be empty.
6. Run the strict LLM gate and both test suites; confirm unchanged.

## Success Criteria

- [x] `validation-verification/README.md`, `mutation-summary.md`,
      `locust-sla-summary.md` created, RecSys section/field shape verified
      side-by-side against the fetched reference above
- [x] `docs/phase2/evidence/README.md` diff shows only an appended section —
      `git diff` confirms zero changes above the append point
- [x] `git diff docs/phase2/rubric-matrix.csv` empty
- [x] `scripts/audit_phase2_evidence.py --require-executed --run-validations --track LLM --phase1-base ddbcbe7bd41ae4883954b8a247efdc67c7329078 --gitops-root ../financial-distress-gitops --ml 100 --llm 100` -> PASS 100/100 (after commit + re-stamp)
- [x] `.venv/bin/python -m pytest tests` (311 passed) and `.venv-phase2/bin/python -m pytest tests/phase2` (549 passed, 35 skipped) -> pass counts unchanged

## Risk Assessment

- **Adding files under `docs/phase2/evidence/llm/` could be mistaken for new
  rubric evidence** if a future row's `artifact_path` accidentally points
  here. Mitigation: these files are clearly presentation, not stamped with
  the evidence-contract fields (`rubric_id`, `source_sha`, etc.); step 5
  confirms the matrix itself never changed.
- **Numbers could drift from the canonical evidence files if copied by
  hand.** Mitigation: every number in this phase file was read directly from
  the canonical `.md` files this session, not recalled — copy from here, and
  diff the bundle against the canonical files before considering this phase
  done.
- **RecSys's numeric SLA thresholds (p95 < 1000ms, throughput >= 5 req/s)
  may not be an appropriate bar for our system** — copying them verbatim
  without checking could understate or overstate what "PASS" means. Step 2
  explicitly requires checking, not copying blind.
