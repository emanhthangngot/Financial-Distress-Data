---
phase: 10
title: "Phase 10: Jenkins-only per-artifact delivery and evidence-gated release"
status: pending
priority: P1
effort: "Re-estimate after P6 Jenkins gate; migrate one reference lane, then the full artifact catalog"
dependencies: ["phase-06-platform.md", "phase-07-ml-track.md", "phase-08-llm-agent-track.md", "phase-09-serving-edge.md"]
owns: ["Jenkinsfile", "platform/ci/", ".github/workflows/", "platform/rollouts/", "scripts/verify_supply_chain.py", "scripts/ci/"]
---

# Phase 10: Jenkins-only per-artifact delivery and evidence-gated release

## Overview

Replace GitHub Actions as the CI/CD authority. The 2026-09-12 inventory found no `Jenkinsfile` and
found stale dependency/test paths in `.github/workflows/phase2-ci.yaml` and its callers, so this is
not a cosmetic runner swap and a historical green screenshot is not parity. P6 provides a restored,
JCasC-managed controller with zero built-in executors and disposable Kubernetes agents. P10 ports
one reference lane, proves success/failure/rollback, then migrates the full artifact catalog,
switches required commit statuses and deletes superseded GitHub Actions build/deploy workflows.

Jenkins is the sole required test/build/release runner after cutover. Argo CD remains the sole
production deploy mutator: Jenkins builds, scans, signs, pushes and opens digest-only GitOps pull
requests; it never runs `kubectl apply`, `helm upgrade` or an Argo sync mutation against production.
An integration environment may auto-merge after all gates. Production requires an explicit Jenkins
approval, after which GitOps merge and Argo reconciliation are automated and observed.

## Selected pipeline architecture

SCM webhook -> multibranch Jenkins job -> ephemeral Kubernetes agent -> behavior gate -> rootless
image build -> SBOM/scan/sign -> registry digest -> digest-only GitOps PR -> policy/approval ->
merge -> Argo CD sync -> runtime smoke -> evidence record. Untrusted pull requests receive no
registry, signing, provider or GitOps credentials. Trusted jobs resolve credential IDs supplied by
P6; secret values never enter JCasC, source, pod YAML, console logs or archived artifacts.

One root `Jenkinsfile` stays thin. `platform/ci/artifacts.yaml` declares artifact name, change paths,
build context, Dockerfile, focused behavior command, image target, GitOps target and runtime smoke.
Reusable implementation lives in versioned `scripts/ci/`; Jenkins-specific orchestration remains in
`platform/ci/`. A shared library is added only if multiple repositories later need the same trusted
code; Jenkins warns that anyone who can modify a trusted global library effectively controls the
controller, so this single-repo plan does not add one for ceremony.

### File inventory

| Path | Action | Contract |
|---|---|---|
| `Jenkinsfile` | create | multibranch entry; validates catalog and dispatches one attributable lane |
| `platform/ci/artifacts.yaml` | create | complete rubric-row/artifact/change/build/GitOps/smoke mapping |
| `platform/ci/jobs/`, `platform/ci/pod-templates/` | create | job definitions and bounded untrusted/trusted agent templates |
| `scripts/ci/` | create | runner-neutral behavior, build, supply-chain, GitOps-PR and evidence commands |
| `.github/workflows/` | delete superseded delivery files after parity | no build/test/deploy authority remains |
| `docs/platform/evidence/{ml,llm}/` | update via P12 | Jenkins job/build URL and immutable release attribution |

### Artifact lanes

The catalog covers every P10 rubric row and its actual deployable: DP1/DP2/DP3, materialization,
stream-feature offline and online jobs, training, inference, feature/drift APIs, RAG, web, feature
agent, drift agent and coordinator. A matrix may share implementation, but Jenkins exposes a
separate job/run result and deployed revision for every named artifact. `feature-mcp` is the
reference lane because it has a current application/Docker surface and participates in the P9
runtime path; no second lane migrates until it proves build, integration deploy, induced failure,
rollback and evidence capture.

Promotion records source/data/model versions and, for agents, prompt/provider/model/corpus plus the
LangChain/LangGraph dependency lock. External provider model IDs are not image digests. Model
promotion uses the frozen P7/P11 holdout and compatible serving contract; agent promotion uses the
fixed P8/P11 safety/quality result. Optional LoRA STOP does not block baseline deployment.

### Interface checklist

| Producer -> consumer | Required interface |
|---|---|
| P6 -> P10 | controller URL, JCasC/plugin revision, trusted/untrusted pod templates, credential IDs, restore proof |
| P7/P8/P9 -> catalog | artifact path, focused behavior command, immutable inputs, runtime smoke and rollback target |
| Jenkins -> registry | image digest, SBOM, vulnerability result, signature/provenance identity |
| Jenkins -> GitOps | one digest/config-only PR, source SHA and previous revision; no manifest regeneration |
| Argo CD -> Jenkins/P12 | read-only convergence, health, deployed revision and rollback observation |
| P11 -> Jenkins | machine-readable release result for required regressions/eval; no test-count proxy |

### Production scenario matrix

| Scenario | Expected Jenkins/GitOps behavior |
|---|---|
| Untrusted PR | behavior/build checks run without secrets; push/sign/GitOps stages are unreachable |
| Successful trusted lane | immutable artifact published, digest-only PR merged by policy, Argo healthy, runtime smoke passes |
| Behavior/eval/scan/sign failure | lane fails before promotion; desired state and production revision remain unchanged |
| Broken candidate rollout | Argo/Helm/KServe owner reports unhealthy; previous digest restores service through the selected rollback path |
| Provider quota or cloud gate unavailable | affected release remains unpromoted; no paid fallback, false green or partial evidence |
| Controller/agent interruption | pipeline resumes or reruns idempotently without duplicate promotion; disposable pod and workspace are cleaned |

### Dependency map

P6 Jenkins runtime and secrets -> reference lane -> catalog migration -> P7 model gate + P8 agent
gate + P9 runtime smoke -> GitOps promotion -> early P12 release metrics -> final P12 freeze.
P11 results flow one way into release decisions; P10 never blocks P11 from producing them.

## Implementation steps

1. Inventory every active GitHub Actions job, current path, credential, status context and rubric
   row. Mark stale/historical paths; do not port broken names as compatibility aliases.
2. Create the declarative catalog and thin Jenkinsfile. Reuse the repository's existing gate and
   focused runtime commands; add no parallel test framework or coverage-padding stage.
3. Implement the `feature-mcp` reference lane on P6's untrusted/trusted agent templates. Exercise
   success, missing dependency, denied secret, failed scan/sign, canceled build and stale GitOps base.
4. Select and record the Jenkins signing identity in ADR-023. Prefer verified workload/keyless
   identity; otherwise use a rotated Vault-managed Cosign key. ADR-011's GitHub-OIDC-only wording is
   no longer sufficient.
5. Publish SBOM/provenance/signature at the image digest. Open a GitOps PR that changes only the
   declared digest/config field and includes source SHA, build URL and previous revision.
6. Merge the integration PR, observe Argo through read-only status, run the real `feature-mcp`
   request, induce a broken revision and restore the previous digest. Freeze reference-lane evidence.
7. Migrate every catalog lane, including model/agent gates and state/schema compatibility checks.
   A shared matrix cannot hide a missing job, deploy target or runtime smoke.
8. Switch branch protection/required checks to Jenkins. Disable then delete superseded GitHub
   Actions delivery workflows; verify a commit cannot trigger duplicate build or deployment.
9. Exercise secret rotation, provider quota exhaustion, partial rollout, controller restart and
   previous-release recovery. State migrations use their own reversible workflow; a digest revert
   never pretends to undo schema state.
10. Hand P12 job/build URLs, console redaction result, digests, signatures, GitOps PR/SHA, Argo
    revision, smoke output and timestamps for every row.

## Success criteria

- [ ] AC-P10-1: Jenkins trusted lane -> rebuilds pinned source/dependencies -> produces one traceable immutable image with SBOM, vulnerability result, signature and provenance.
- [ ] AC-P10-2: Auditor -> maps all CI/CD rubric rows to executed Jenkins jobs -> every named artifact has attributable behavior/build/auto-deploy result, immutable deployed revision and runtime smoke.
- [ ] AC-P10-3: Jenkins promotion -> opens and completes a GitOps release -> only intended digest/config references change; Argo CD performs deployment and Jenkins has no production mutation credential.
- [ ] AC-P10-4: Model/agent gate -> reads the frozen P7/P8/P11 revisioned result -> compatible passing candidate promotes; failed, stale or unavailable required gate changes nothing.
- [ ] AC-P10-5: Release operator -> induces a failed deployment/canary -> prior compatible image and state contract restore service; thresholds are not relaxed to force success.
- [ ] AC-P10-6: Migration operator -> switches required statuses after reference-lane parity -> Jenkins is the sole build/test/release authority and superseded GitHub Actions delivery workflows are absent.
- [ ] AC-P10-7: Secret operator -> runs untrusted and trusted jobs then rotates credentials -> untrusted stages cannot resolve secrets, trusted consumers recover, values remain absent from logs/artifacts, old references are removed only after success.
- [ ] AC-P10-8: Operator -> inspects deployment controllers -> no workload has competing Jenkins/Argo/Rollouts/KServe ownership; each selected rollback owner is explicit and exercised.
- [ ] AC-P10-9: Recovery operator -> restarts the controller and interrupts an agent during promotion -> job state is recoverable or safely rerunnable, no duplicate GitOps PR/deploy occurs, and disposable resources are cleaned.
- [ ] AC-P10-COST: Runner -> reaches a free-provider quota or unavailable resource gate -> release stays unpromoted, no paid route or billing upgrade is reachable.

## Risks and verification

Cutting over before the reference lane proves runtime and rollback can strand delivery; switch
required checks only after evidence. A shared matrix can conceal missing deploy targets; grade the
catalog row and Jenkins run, not job count. A compromised trusted library or controller has broad
impact; use reviewed in-repo scripts, zero controller executors, isolated agents and least privilege.
Resource-free checks cannot demonstrate deployment. Capture during the approved window, export
evidence, restore/stop authorized resources, and leave blocked gates visible.

Grounding: Jenkins Pipeline-as-code and credentials
(`https://www.jenkins.io/doc/book/pipeline/jenkinsfile/`), Kubernetes disposable agents
(`https://plugins.jenkins.io/kubernetes/`), JCasC
(`https://www.jenkins.io/doc/book/managing/casc/`), shared-library trust
(`https://www.jenkins.io/doc/book/pipeline/shared-libraries/`) and controller isolation
(`https://www.jenkins.io/doc/book/security/controller-isolation/`), read 2026-09-12.

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
