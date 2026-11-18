---
phase: 10
title: "Phase 10: Per-artifact CI/CD and evidence-gated release"
status: pending
priority: P1
effort: "10-14 days"
dependencies: ["phase-06-platform.md", "phase-07-ml-track.md", "phase-08-llm-agent-track.md", "phase-09-serving-edge.md"]
owns: ["Jenkinsfile*", "platform/ci/", "platform/rollouts/", ".github/workflows/", "scripts/verify_supply_chain.py"]
---

# Phase 10: Per-artifact CI/CD and evidence-gated release

## Overview

Retain working GitHub Actions unless an actual requirement justifies another runner. Jenkins is
not mandated by the rubric; do not delete `.github/workflows/` to match an image. All rubric CI/CD
artifacts still need real test -> build -> auto-deploy evidence, with secrets outside source.
Reusable workflows or a matrix are acceptable only when each artifact has its own attributable
trigger, checks, deployed revision and successful run evidence. Do not invent a fixed lane count.

## Requirements

Inventory every CI/CD rubric row below and map it to an artifact-specific lane: materialization,
training, DP1/DP2/DP3, inference, Web API/drift, stream-feature offline/online, RAG and three agents.
Shared jobs may cover multiple rows only with explicit artifact mapping; no missing artifact hidden
behind a green monolithic run. GitOps remains the deployment mutator, with immutable image digests.

Promotion records source/data/model versions and, for agents, prompt/provider/model/corpus and
LangChain/LangGraph dependency lock. External provider model IDs are not image digests: record
provider identity separately and never claim immutable hosted model weights.
Model promotion uses the frozen P7/P11 holdout and compatible serving contract; agent promotion
uses the fixed P8/P11 safety/quality suite. Optional LoRA STOP does not block baseline deployment.
A failed or unavailable required gate does not promote. No per-run paid inference fallback.

Helm rollback remains P9's required proof. Existing Argo Rollouts may govern Deployment-backed
canaries, never a competing controller over KServe resources. Do not add Rollouts solely for image
fidelity. Calibrate release metrics using an early P12 instrumentation slice; final P12 completion
is not a P10 prerequisite. Thresholds are frozen before candidate comparison; never widen a failing
gate to force promotion.

## Ownership and workflow

Own existing CI workflows, digest promotion and release policies. P6 provides centralized secret
access; remove superseded sealed-secret consumers only after verified rotation/recovery. Controller
and certificate-generated secrets are not required to originate in ESO. No blanket Secret deletion.

1. Reconcile all CI/CD row IDs with real artifact paths and deploy targets, including shared lanes.
2. Reuse current runner and build definitions; pin dependency/build inputs and store secrets through
   authorized CI/centralized secret integration. PR/untrusted job cannot read deployment secrets.
3. Exercise each artifact lane's successful test/build/deploy and induced failure; record revision.
4. Add model and agent gate artifacts; validate hash/revision compatibility before GitOps promotion.
5. Prove promotion changes only intended immutable artifact/config references. Data/schema changes
   use their migration workflow; never hide schema mutations in a model digest bump.
6. Exercise canary/rollback where selected, partial deployments, provider quota exhaustion, secret
   rotation and previous-release recovery. Build-only CI is not an auto-deploy pass.
7. Close only rows with real successful per-artifact runs. Local runner evidence does not imply
   cloud deployment; the manifest records actual runtime and resource-window identity.

## Success criteria

- [ ] AC-P10-1: CI runner -> rebuilds pinned source/dependencies -> produces traceable immutable image with SBOM/provenance; no unnecessary cross-CI bitwise-digest requirement.
- [ ] AC-P10-2: Auditor -> maps all CI/CD rubric rows to executed lanes -> every named artifact has test/build/auto-deploy result and immutable deployed revision, including shared-workflow subresults.
- [ ] AC-P10-3: Promotion job -> updates GitOps release -> only intended digest/config references change; no unrelated manifest edits or plaintext credentials.
- [ ] AC-P10-4: Model/agent gate -> passes or fails on frozen dataset/revision -> compatible passing candidate promoted; failed/unavailable required gate changes nothing.
- [ ] AC-P10-5: Release operator -> induces a failed deployment/canary -> prior version restores service using P9 rollback contract; thresholds not relaxed to force success.
- [ ] AC-P10-6: Engineer -> runs existing CI after integration -> all artifact lanes work without mandatory Jenkins migration or deletion of functioning GitHub workflows.
- [ ] AC-P10-7: Secret operator -> rotates authorized workload credentials -> consumers recover, old managed references removed only after success and generated secrets untouched.
- [ ] AC-P10-8: Operator -> inspects deployment controllers -> no workload has competing Rollouts/KServe ownership; selected rollback path exercised.
- [ ] AC-P10-COST: Runner -> reaches free-provider quota or unavailable resource gate -> release stays unpromoted, no paid route or auto billing upgrade.

## Risks and verification

A shared workflow can conceal missing deploy targets: use row-to-artifact evidence, not job count.
Hosted model changes limit reproducibility; date/config provenance and re-evaluation are required.
Resource-free checks cannot demonstrate Kubernetes/cloud rollout. Capture during the approved
window, export evidence, then shut down authorized resources without deleting persistent state.

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
