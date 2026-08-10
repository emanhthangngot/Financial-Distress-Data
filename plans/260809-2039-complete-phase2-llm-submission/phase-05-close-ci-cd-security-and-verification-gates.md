---
phase: 5
title: "Close CI/CD, security and verification gates"
status: pending
priority: P1
effort: "1.5d"
dependencies: [3, 4]
---

# Phase 5: Close CI/CD, security and verification gates

## Overview

Turn every new deployable into a signed, GitOps-reconciled release; close the
verification-technique rows; and capture warm-up and A/B, which need the
inference platform and agents already running.

Rubric rows owned (23 points) — IDs and paths copied verbatim from the CSV:

| Points | rubric_id | artifact_path (authority) |
|---:|---|---|
| 2 | `LLM-ci-cd-ci-cd-cho-rag-data-pipeline` | source `.github/workflows/phase2-ci.yaml` |
| 2 | `LLM-ci-cd-agent-k-o-d-li-u` | source `.github/workflows/phase2-ci.yaml` |
| 2 | `LLM-ci-cd-agent-drift-detection` | source `.github/workflows/phase2-ci.yaml` |
| 2 | `LLM-ci-cd-agent-l-m-coordinator` | source `.github/workflows/phase2-ci.yaml` |
| 1 | `LLM-validation-verification-validation-verification` | source `tests/phase2/requirements/test_llm_ac_10_validation.py` |
| 2 | `LLM-validation-verification-c-s-d-ng-k-thu-t-equivalence-p` | same |
| 2 | `LLM-validation-verification-c-s-d-ng-mutation-testing-nh-g` | same |
| 2 | `LLM-validation-verification-idempotency-testing-s-d-ng-pro` | same |
| 2 | `LLM-validation-verification-load-test-the-web-api` | same |
| 2 | `LLM-repository-design-clean-code-clean-repo-demonstr` | source `src/llm/contracts.py` |
| 2 | `LLM-c-i-t-h-th-ng-ch-warm-up--c-i-t-h-th-ng-ch-warm-up-cho-a` | gitops `platform/agents/warm-pool.yaml` — placeholder today |
| 1 | `LLM-a-b-testing-perform-a-b-test-for-different` | gitops `platform/llm/ab-testing.yaml` — placeholder today |
| 1 | `LLM-a-b-testing-when-you-deploy-a-new-model` | gitops `platform/llm/ab-testing.yaml` |

Six CI/CD rows and five verification rows each resolve to a single artifact
(`phase2-ci.yaml` and `test_llm_ac_10_validation.py`) — those two files carry
12 points between them.

## Mutation score > 80% is a real gate

The unified plan recorded the threshold as "self-imposed and retired". That was
wrong. The canonical CSV prints `Mutation score > 80%.` verbatim in **both** the
`requirement` and `deliverables` columns of this 2-point row. Decision
2026-08-09: restore it as a hard gate, scope `mutmut` to a small pure-module
subset chosen so the bar is reachable, and record the real score either way.
Do not launder a miss as a retired requirement.

Coverage >90% with fixture/mock proof on the Web API tests remains the base
row's declared proof and is also a hard gate.

## Requirements

- Functional: four more caller workflows on the reusable `phase2-ci.yaml`
  template, each building, **signing**, pushing an immutable GHCR digest and
  opening a GitOps digest PR **that something actually consumes**; parametrized
  equivalence-partition and boundary-value tests; Hypothesis idempotency tests;
  `mutmut` >80% on a declared subset; a Locust HTML report; warm-up cold-vs-warm
  measurements; A/B across two model versions and two agent model configs.
- Non-functional: the CI matrix iterates a deployable list, never a hardcoded
  service set (retrofit decision 4).

## Architecture

**The digest loop is currently open.** `phase2-ci.yaml`'s `gitops-pr` job writes
`pipelines/<name>/digest.txt` — a path the workflow itself annotates as a
placeholder, which does not exist in the GitOps repo and which no Application,
chart values file or kustomization reads. Merging those PRs today changes
nothing. Phase 3 created `charts/fastapi-service/` and `apps/dev/<service>/`;
rewire `gitops-pr` to bump the real per-service image digest key there, so
"merge the PR → Argo reconciles → pods roll" is a true statement. Add a
`cosign sign` step and `id-token: write` — the success criterion says *signed*,
and nothing signs today.

Note the three real bugs phase-04 already fixed in that template (hardcoded
`--base main` when the GitOps default branch is `master`; missing
`packages: write`; startup failure) and do not reintroduce them. Phase 1 already
replaced the `eval` on the `test_selector` input and wired in the phase-2
dependency manifest — without that, these four workflows would run against an
environment that cannot import FastAPI, Feast or MCP.

**Verification.** Equivalence partitions and boundaries over input schema,
missing/unknown ticker, timestamp edges and API limits. Hypothesis for idempotent
retrieval and repeated tool invocation. `mutmut` scoped to two or three small
pure modules — `src/llm/rag/chunking.py` and `src/drift/generator.py` are good
candidates. Locust against the Web API kéo dữ liệu through the gateway with p95
latency, throughput, error rate, concurrency and test parameters in the HTML.
Reuse the GitOps `ansible/roles/benchmark-client/files/locustfile.py`.

The five verification rows all resolve to
`tests/phase2/requirements/test_llm_ac_10_validation.py`, which is
**generator-owned**. Do not hand-edit it: add each row's behavioral assertion
through the `behavioral_assertion` column phase 1 introduced, then regenerate.

**Warm-up.** Minimum warm capacity during the evidence window, scaled down
outside it. `platform/agents/warm-pool.yaml` is an empty placeholder, so this is
authoring. Measure cold vs warm startup and TTFT, record the cost difference and
the replica spread, reusing `src/llm/benchmark.py` from phase 2.

**A/B on Knative traffic split.** llm-d was dropped in phase 2, so the split is
Knative revision traffic percentages, which work on the pinned KServe v0.14.1.
Two model revisions live simultaneously with a controlled split plus two agent
model configs, and a dashboard comparing TTFT, latency, tokens, failures and
cost. The second A/B row is literally "don't replace the old model directly" —
the evidence must show both revisions serving at once.

**Repository design** resolves to `src/llm/contracts.py`: the implemented
classes matching their documented contracts and design patterns
(`docs/phase2/low-level-design.md`), plus the two-repo separation.

## Related Code Files

- Create: `.github/workflows/phase2-agent-feature.yaml`,
  `phase2-agent-drift.yaml`, `phase2-agent-coordinator.yaml`
  (`phase2-rag-pipeline.yaml` already exists — wire its evidence)
- Modify: `.github/workflows/phase2-ci.yaml` (deployable-list matrix, real
  digest key, `cosign sign`, `id-token: write`)
- Create: `tests/phase2/verification/` — equivalence/boundary, Hypothesis
  idempotency, fixture/mock-based Web API unit tests
- Create: `tests/load/locustfile.py` (or reuse the GitOps one) + the generated
  HTML under `docs/phase2/evidence/llm/`
- Modify: `src/llm/contracts.py` and its implementing classes
- Modify (GitOps): `platform/agents/warm-pool.yaml`, `platform/llm/ab-testing.yaml`
  — **placeholders today**; `apps/dev/<service>/` digest keys
- Create: 13 evidence files under `docs/phase2/evidence/llm/`
- Regenerate (never hand-edit): `tests/phase2/requirements/test_llm_ac_09_warmup.py`,
  `test_llm_ac_10_validation.py`, `test_llm_ac_12_cicd.py`,
  `test_llm_ac_16_ab.py`, `test_llm_ac_18_repository.py`

## Implementation Steps

1. (Cluster down) Write the equivalence/boundary, Hypothesis and fixture/mock
   Web API tests. Reach >90% coverage on the Phase 2 LLM code; capture the
   report showing both the figure and the fixture/mock usage.
2. (Cluster down) Run `mutmut` on the declared subset. **Drive it to >80%** —
   this is scored text. Record the real score and the surviving-mutant list.
3. Rewire `gitops-pr` to the real per-service digest key and add image signing.
   Prove one end-to-end: push → digest → PR → merge → Argo reconciles → pod
   image changes.
4. Add the four caller workflows, driven by the deployable list. Push and watch
   each run to green, capturing run IDs, digests and PR numbers as the phase-04
   evidence files do.
5. `make gcp-up`. Merge the digest PRs and confirm Argo actually rolls each
   service.
6. Run Locust against the Web API kéo dữ liệu through the gateway; generate the
   HTML and record the SLA fields and test parameters.
7. Author the warm-pool; measure cold vs warm startup and TTFT; record the cost
   difference and replica spread.
8. Deploy the second model revision and second agent model config; run the
   Knative traffic-split A/B; capture the comparison dashboard with both
   revisions live.
9. Write the 13 evidence files, flip these 13 rows to `executed`, regenerate the
   CSV and requirement tests, re-run the audit. `make gcp-down`; record the delta.

## Success Criteria

- [ ] Developer -> merges source code for any of the four new deployables -> obtains one **signed** immutable digest and one GitOps PR whose merge visibly changes the running pod's image.
- [ ] Maintainer -> adds a hypothetical new deployable -> edits one list entry, not the workflow body.
- [ ] Test runner -> runs the Phase 2 LLM suite -> reports >90% coverage with visible fixture and mock usage on the Web API tests, plus passing equivalence/boundary and Hypothesis idempotency tests.
- [ ] Test runner -> runs `mutmut` on the declared subset -> reports a score **above 80%**, with the surviving-mutant list recorded.
- [ ] Load tester -> runs Locust against the Web API kéo dữ liệu through the gateway -> receives an HTML report with p95 latency, throughput, error rate, concurrency and test parameters.
- [ ] Operator -> compares cold and warm agent modes -> sees improved startup and TTFT with a documented cost difference and replica spread.
- [ ] Reviewer -> inspects the A/B configuration -> sees two Knative revisions serving simultaneously with a controlled split and a comparison dashboard, not a replacement.

## Risk Assessment

- **`mutmut` >80% is now a hard gate on a 2-point row**, and `mutmut` 3.x's CLI
  and cache format differ from the 2.x docs. Mitigation: pick the smallest pure
  modules with the tightest tests, timebox the tooling shakeout on cluster-down
  time (step 2), and if the bar proves unreachable, record the real score
  honestly rather than restating the threshold as retired.
- **Coverage >90% on brand-new Phase 2 code.** Mitigation: step 1 runs with the
  cluster down, before the capture rush; mock the model and cluster boundaries.
- **Rewiring the digest key touches the one CI path that already works.**
  Mitigation: prove the loop on a single service before adding the four callers;
  the existing `LLM-ci-cd-job-1`/`job-2` evidence is the regression baseline.
- **Warm-up and A/B are cut-ladder entries 1 and 2** (2 points each, decide by
  the end of this phase's day 1). Cutting them requires naming the rows in
  `--accept-design-only` and in `docs/submission/README.md`.
