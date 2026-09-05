---
phase: 10
title: "Phase 10: Jenkins, Argo Rollouts, secrets cutover, GitOps"
status: pending
priority: P1
effort: "10-14 days"
dependencies: ["phase-06-platform.md", "phase-07-ml-track.md", "phase-08-llm-agent-track.md", "phase-09-serving-edge.md"]
owns: ["Jenkinsfile*", "platform/ci/", "platform/rollouts/", ".github/workflows/"]
---

# Phase 10: Jenkins, Argo Rollouts, secrets cutover, GitOps

## Overview

Deploy Jenkins; author the two pipelines; convert Deployment-backed workloads to Argo Rollouts
canary; prove digest equivalence with GitHub Actions; then perform the atomic flip — delete
`.github/workflows/` and switch sealed-secrets → ESO/Vault. **Resident cost: 1-2 vCPU during CI
windows.**

The rubric grades **CI/CD per artifact**, never the CI tool. Sixteen rows, 27 points:

| Rows | Artifact | Points |
|---|---|---|
| ML 27 | Materialize pipeline | 2 |
| ML 28 | Training pipeline | 2 |
| ML 29-31 | DP 1 / DP 2 / DP 3 (mini-coursework data pipelines) | 6 |
| ML 32 | Web API | 2 |
| ML 33 | Inference engine (KServe) | 1 |
| ML 34 | Real-time drift API (KNative Eventing + KServe) | 1 |
| ML 35-36 | Job: stream feature → OFFLINE / ONLINE | 2 |
| LLM 34 | RAG data pipeline | 2 |
| LLM 35-37 | Agent: data-fetch / drift / coordinator | 6 |
| LLM 38-39 | Job: stream feature → OFFLINE / ONLINE | 4 |

Each row needs a pipeline that tests, builds and deploys **that** artifact. Twelve distinct
pipelines, not one monolith. This is the phase's real cost — Jenkins itself is the cheap part.

## Requirements

- Functional:
  - Jenkins produces the same image digest as GitHub Actions for the same commit.
  - `bump-gitops` commits only `@sha256` digest values.
  - `model-promote` commits only the `triton-isvc.yaml` and `llm-isvc-b.yaml` digests on gate pass,
    and nothing at all on gate fail.
  - Twelve per-artifact lanes exist, each running test → build → push-by-digest → deploy.
  - Argo Rollouts `AnalysisTemplate` queries p99 latency, error rate and drift, and aborts on breach.
  - Zero sealed-secrets remain; every Secret in a managed namespace is ESO-sourced from Vault.
  - `.github/workflows/` contains zero files; `AGENTS.md` names Jenkins as CI.
- Non-functional: Rollouts govern Deployment-backed workloads **only** — no `InferenceService` or
  `LLMInferenceService` under Rollouts control.

## Architecture

```
Developer → git push → GitHub (SCM) → webhook → Jenkins

app-ci lane (per artifact, ×12)
  lint → test → build → scan → push-by-digest → bump-gitops (digest-only commit)
       → Argo CD reconciles → Argo Rollouts canary → AnalysisTemplate

model-promote lane (triggered by the holdout gate)
  fetch-run → promotion_gate.py → smoke-test → scan artifact → sign
            → bump-gitops (triton-isvc.yaml + llm-isvc-b.yaml digests only)

ns: rollouts
  Deployment-backed canary → AnalysisTemplate (p99, error rate, drift) → abort on breach
```

## Related Code Files

- Restore from archive: `platform/rollouts/`, `platform/ml/ab-testing.yaml` (AnalysisTemplates)
- Create: `platform/ci/jenkins-controller.yaml`, `platform/ci/jenkins-agent-podtemplate.yaml`
- Create: `Jenkinsfile` (shared library entry), `Jenkinsfile.promote`
- Create: `ci/lanes/*.groovy` — twelve per-artifact lane definitions sharing one library
- Modify: `api-serving`, `agents`, `web` Deployments → `Rollout` kind
- Modify: `AGENTS.md` — CI definition becomes Jenkins
- Delete: `.github/workflows/` (entire directory — atomic flip)

## Implementation Steps

1. **Deploy `platform-ci`** (2 d) — Jenkins controller plus ephemeral agent pod templates via Argo CD.
2. **Shared library + first lane** (2 d) — one Groovy shared library implementing
   lint → test → build → scan → push-by-digest → bump-gitops; instantiate it for the Web API lane
   first and prove digest equivalence with the existing GitHub Actions run on the same commit.
3. **Remaining eleven lanes** (3-4 d) — materialize pipeline, training pipeline, DP1, DP2, DP3,
   inference engine, drift API, two stream-feature jobs, RAG pipeline, three agents. Each lane is a
   thin instantiation of the shared library; the per-lane work is the test command and the deploy target.
4. **`Jenkinsfile.promote`** (1-2 d) — fetch-run → `src/ml/promotion_gate.py` → smoke-test → scan →
   sign → `bump-gitops` with digests only; verify **nothing** is committed on gate failure.
5. **`platform-rollouts`** (1 d) — Argo Rollouts plus the restored AnalysisTemplates.
6. **Convert Deployments** (2 d) — `api-serving`, `agents`, `web` to `Rollout` with canary and the
   ML-gate AnalysisTemplate; calibrate thresholds against the P12 baseline metrics before enabling abort.
7. **Atomic CI flip** (1 d) — delete `.github/workflows/`; update `AGENTS.md`; verify zero workflow
   files remain and every lane still passes from Jenkins.
8. **Secrets flip** (1 d) — verify every ESO `ExternalSecret` is reconciled from Vault; delete
   sealed-secrets; confirm none remains in any managed namespace.
9. **Scope check** (0.5 d) — list all `Rollout` objects and confirm no `InferenceService` or
   `LLMInferenceService` appears.

## Success Criteria

- [ ] AC-P10-1: Jenkins `app-ci` → builds the same source commit as GitHub Actions → produces an
      identical image digest
- [ ] AC-P10-2 **(ML 27-36; LLM 34-39)**: Operator → lists Jenkins jobs → **twelve** per-artifact
      lanes exist; each runs test → build → deploy for its own artifact and is triggered by a change
      to that artifact's path
- [ ] AC-P10-3: Jenkins `bump-gitops` → promotes a build → the GitOps commit changes only `@sha256`
      digest values; no other manifest content changes
- [ ] AC-P10-4: Jenkins `model-promote` → passes the holdout gate → commits the `triton-isvc.yaml`
      and `llm-isvc-b.yaml` digest bumps and nothing else; on gate failure commits nothing
- [ ] AC-P10-5: Argo Rollouts → runs a canary on `api-serving` → the AnalysisTemplate queries p99
      latency, error rate and drift, and aborts the rollout on a threshold breach
- [ ] AC-P10-6: Platform operator → lists `.github/workflows/` after the flip → zero workflow files;
      `AGENTS.md` names Jenkins as CI
- [ ] AC-P10-7: Platform operator → searches the cluster for sealed-secrets → finds none; every
      Secret in a managed namespace is ESO-sourced from Vault
- [ ] AC-P10-8: Argo Rollouts → inspected for CRD scope → governs only Deployment-backed workloads;
      zero `InferenceService` or `LLMInferenceService` under Rollouts control

## Risk Assessment

**Risk:** twelve lanes are collapsed into one parameterised job to save time. Signal: AC-P10-2 finds
one job with a matrix. Mitigation: the rubric scores sixteen distinct CI/CD rows, each naming its
artifact; a matrix job does not produce per-artifact evidence. Response: instantiate the shared
library twelve times — the library keeps the duplication to configuration only.

**Risk:** Jenkins digests differ from GitHub Actions because of builder environment drift. Signal:
AC-P10-1 mismatch. Mitigation: identical base image and pinned builder tool versions. Response:
diff with `docker history`; pin the missing tool.

**Risk:** a canary abort blocks a valid deployment. Signal: rollouts abort on normal traffic.
Mitigation: calibrate thresholds against P12 baseline metrics **before** enabling abort. Response:
pause, widen temporarily, investigate the root cause.

**Risk:** the atomic CI flip happens before all twelve lanes are green, leaving no working CI.
Signal: a lane fails after `.github/workflows/` is deleted. Mitigation: step 7 runs only after step 3
is complete and every lane has passed once from Jenkins. Response: `git revert` the deletion —
the workflows return intact.

**Risk:** the secrets flip orphans a Secret. Signal: a pod fails to mount after sealed-secrets are
removed. Mitigation: list every Secret before and after; confirm the ESO-managed annotation on each
one in a managed namespace. Response: create the missing `ExternalSecret` and re-reconcile.

**Risk:** cutting Jenkins later (plan §Schedule Reality item 1) would strand the twelve lanes.
Signal: the cut decision arrives after step 3. Mitigation: **the twelve lanes carry the 27 rubric
points, not Jenkins.** Author them as a shared library that GitHub Actions can also instantiate, so a
Jenkins cut costs the controller work only, not the lanes. Response: re-target the lanes at GitHub
Actions reusable workflows; the per-artifact structure and its evidence survive.

## Rubric Citations (phase-03 R-12 closure, appended 2026-09-05)

Every rubric row this phase owns per `docs/rubric-matrix-unified.csv`'s `owning_phase` column, cited so `scripts/verify_rubric_coverage.py` can resolve ownership to an assertion (R-12). Each line names the row's real `rubric_id`, its stated requirement, and its proof artifact/deliverable — the row's own matrix columns, not invented text. Rows whose capability is not yet implemented are forward specs, matching this file's other `AC-P10-*` entries.

- AC-P10-RUBRIC-1: `LLM-ci-cd-agent-drift-detection` — llm_engineer -> delivers "Agent drift detection" -> Capture màn hình từng CI/CD pipeline đã run thành công (evidence: `docs/platform/evidence/llm/LLM-ci-cd-agent-drift-detection.md`)
- AC-P10-RUBRIC-2: `LLM-ci-cd-agent-k-o-d-li-u` — llm_engineer -> delivers "Agent kéo dữ liệu" -> Capture màn hình từng CI/CD pipeline đã run thành công (evidence: `docs/platform/evidence/llm/LLM-ci-cd-agent-k-o-d-li-u.md`)
- AC-P10-RUBRIC-3: `LLM-ci-cd-agent-l-m-coordinator` — llm_engineer -> delivers "Agent để làm coordinator" -> Capture màn hình từng CI/CD pipeline đã run thành công (evidence: `docs/platform/evidence/llm/LLM-ci-cd-agent-l-m-coordinator.md`)
- AC-P10-RUBRIC-4: `LLM-ci-cd-ci-cd-cho-rag-data-pipeline` — data_engineer -> delivers "CI/CD; (CI/CD = test + build + auto-deploy); (all secrets should be saved in Jenkins or similar tools instead of putting it inside your code..." -> Capture màn hình từng CI/CD pipeline đã run thành công (evidence: `docs/platform/evidence/llm/LLM-ci-cd-ci-cd-cho-rag-data-pipeline.md`)
- AC-P10-RUBRIC-5: `LLM-ci-cd-job-1` — data_engineer -> delivers "Job 1: Push stream feature to OFFLINE store" -> Capture màn hình từng CI/CD pipeline đã run thành công (evidence: `docs/platform/evidence/llm/LLM-ci-cd-job-1.md`)
- AC-P10-RUBRIC-6: `LLM-ci-cd-job-2` — data_engineer -> delivers "Job 2: Push stream feature to ONLINE store" -> Capture màn hình từng CI/CD pipeline đã run thành công (evidence: `docs/platform/evidence/llm/LLM-ci-cd-job-2.md`)
- AC-P10-RUBRIC-7: `ML-ci-cd-ci-cd-cho-pipelines` — data_engineer -> delivers "CI/CD; (CI/CD = test + build + auto-deploy); (all secrets should be saved in Jenkins or similar tools instead of putting it inside your code..." -> Capture màn hình từng CI/CD pipeline đã run thành công (evidence: `docs/platform/evidence/ml/ML-ci-cd-ci-cd-cho-pipelines.md`)
- AC-P10-RUBRIC-8: `ML-ci-cd-dp-1` — platform_operator -> delivers "DP 1 (xem ở sheet mini-coursework)" -> Capture màn hình từng CI/CD pipeline đã run thành công (evidence: `docs/platform/evidence/ml/ML-ci-cd-dp-1.md`)
- AC-P10-RUBRIC-9: `ML-ci-cd-dp-2` — platform_operator -> delivers "DP 2 (xem ở sheet mini-coursework)" -> Capture màn hình từng CI/CD pipeline đã run thành công (evidence: `docs/platform/evidence/ml/ML-ci-cd-dp-2.md`)
- AC-P10-RUBRIC-10: `ML-ci-cd-dp-3` — platform_operator -> delivers "DP 3 (xem ở sheet mini-coursework)" -> Capture màn hình từng CI/CD pipeline đã run thành công (evidence: `docs/platform/evidence/ml/ML-ci-cd-dp-3.md`)
- AC-P10-RUBRIC-11: `ML-ci-cd-inference-engine` — platform_operator -> delivers "Inference Engine (ví dụ KServe)" -> Capture màn hình từng CI/CD pipeline đã run thành công (evidence: `docs/platform/evidence/ml/ML-ci-cd-inference-engine.md`)
- AC-P10-RUBRIC-12: `ML-ci-cd-job-1` — data_engineer -> delivers "Job 1: Push stream feature to OFFLINE store" -> Capture màn hình từng CI/CD pipeline đã run thành công (evidence: `docs/platform/evidence/ml/ML-ci-cd-job-1.md`)
- AC-P10-RUBRIC-13: `ML-ci-cd-job-2` — data_engineer -> delivers "Job 2: Push stream feature to ONLINE store" -> Capture màn hình từng CI/CD pipeline đã run thành công (evidence: `docs/platform/evidence/ml/ML-ci-cd-job-2.md`)
- AC-P10-RUBRIC-14: `ML-ci-cd-training-pipeline` — ml_engineer -> delivers "Training Pipeline" -> Capture màn hình từng CI/CD pipeline đã run thành công (evidence: `docs/platform/evidence/ml/ML-ci-cd-training-pipeline.md`)
- AC-P10-RUBRIC-15: `ML-ci-cd-web-api` — platform_operator -> delivers "Web API (với FastAPI)" -> Capture màn hình từng CI/CD pipeline đã run thành công (evidence: `docs/platform/evidence/ml/ML-ci-cd-web-api.md`)
