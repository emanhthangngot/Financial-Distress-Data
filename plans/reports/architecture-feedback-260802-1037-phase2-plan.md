---
title: "Architecture feedback validation — unified Phase 2 plan"
date: 2026-08-02
status: complete
input: "/home/pearspringmind/.codex/attachments/899865c3-7b03-4b32-9f85-710e8741dba3/pasted-text.txt"
plan: "../260802-1037-unified-phase2-ml-llm-gitops/plan.md"
---

# Architecture feedback validation

## Outcome

The feedback is mostly legitimate and materially improves execution readiness. The revised plan accepts the missing schedule/cut policy, privilege-level RBAC, disclaimer, cross-repository automation, evidence-session UX, explicit rubric gaps and Argo CD contract. It corrects four technical overstatements and rejects two proposed behaviors that would weaken or break the design.

Validation used the two original rubric CSVs, current repository contracts, the supplied system-design references, and current official KServe/Argo CD documentation. Spreadsheet row numbers in the feedback are treated as approximate; semantic requirement names are authoritative because multiline CSV cells and the header shift physical line numbers.

## Accepted

| Feedback | Verdict | Plan update |
|---|---|---|
| Add a time budget and cut-list | Accepted | Added 55-79 focused days, phase estimates, “never cut”, first-cut and second-cut tiers. |
| Add privilege-level admin RBAC | Accepted | Added `analyst`, `platform_viewer`, `platform_operator`, `platform_admin`, AAL2, RLS/server checks and fencing. |
| Add investment disclaimer | Accepted | Required on company, explanation, chat, comparison and exports. |
| Automate the source-repo to GitOps-repo handoff | Accepted | Source CI opens digest PR; dev may auto-merge after checks, main/evidence requires review. |
| Show lifecycle state and cost before provisioning | Accepted | Added durable state machine, timeline, projected/actual cost, cap denial, outbox and idempotency. |
| Clarify MLflow deployment and sync ordering | Accepted with corrected dependency | Added owned Helm chart, RDS backend, S3 artifacts and promotion-to-immutable-S3 contract. |
| Add Kustomize validation if mixed deployment is used | Accepted | Added bounded Helm/Kustomize ownership, duplicate-resource rejection, `kustomize build`, `kubeconform`, and `conftest`. |
| Make Locust HTML explicit | Accepted | Required for the rubric Web APIs with recorded SLA and parameters. |
| Make autoscaling proof explicit for feature and drift APIs | Accepted | Independent KEDA/HPA experiments and artifacts are mandatory. |
| Make TLS/domain explicit | Accepted | NGINX public edge, cert-manager certificate, domain, TLS proof and private internal services. |
| Document design patterns and five classes | Accepted | Added five ML and five LLM class contracts plus executable design-pattern proof. |
| Name two novel ideas per track | Accepted | Added PIT leakage guard, reproducibility manifest, embedding hot swap, and citation/PII guard. |
| Add LLM warm-up/HA proof | Accepted | Added cold/warm benchmark, TTFT/cost and multi-replica worker-pool proof. |
| Separate agent chat and registry UIs | Accepted | Added distinct routes, contracts, tests and evidence. |

## Accepted with technical corrections

### Two gateways remain correct, but dependency ownership is explicit

Keeping agentgateway and Envoy AI Gateway is legitimate because they own different protocols and control surfaces. However, an `LLMInferenceService` resource does not by itself guarantee that Envoy Gateway/Envoy AI Gateway has been installed. KServe 0.18 documents them as installation requirements. The GitOps platform wave therefore installs and pins them before LLM workloads. See [KServe 0.18 LLMInferenceService installation](https://kserve.github.io/website/docs/install/llmisvc-install).

### Kustomize is supported, not mandatory

The feedback says KServe 0.18 requires part of the installation through Kustomize/raw manifests. That is too strong. The official 0.18 installation guide supports Kustomize, Helm and script-based methods, and recommends OCI Helm charts for Helm installation. The revised plan still uses Kustomize where upstream overlays need patching, but never duplicates resources already owned by Helm. See [KServe 0.18 installation methods](https://kserve.github.io/website/docs/install/llmisvc-install) and [KServe Kubernetes deployment guidance](https://kserve.github.io/website/docs/admin-guide/kubernetes-deployment).

### MLflow is a promotion dependency, not a KServe runtime dependency

MLflow must be available for experiment tracking, candidate registration and promotion. KServe should not dynamically read the MLflow registry during serving. The promotion controller resolves the approved MLflow version/alias to an immutable S3 model URI and commits that URI to GitOps. MLflow is ordered before promotion jobs; the KServe controller itself need not wait on MLflow after desired state contains a valid artifact URI.

### Rubric gaps are real; cited row numbers are approximate

The missing deliverables identified in the feedback are present in the CSVs, but several physical row references are off by one or more because of the CSV header and multiline cells. The plan uses semantic IDs instead: Locust HTML, independent feature/drift autoscaling, HTTPS/domain, design-pattern proof, five classes, two ideas per track, LLM warm-up, agent chat UI and registry UI.

## Rejected

### Do not reduce the quality thresholds

The suggestion that >90% coverage and >80% mutation score may be excessive was later retracted in the same feedback. Both final rubrics explicitly require those thresholds. The revised plan retains them and scopes mutation to changed code, as the rubric directs.

### Do not treat an image-tag push as a deployment trigger

When GitOps desired state pins an immutable digest, pushing another tag does not change Git and therefore must not deploy. Source CI must open a PR that changes the desired digest. Argo CD then reconciles the merged commit. Official Argo guidance describes CI committing to Git instead of calling the Argo API; automated sync, prune and self-heal remain Git-driven. See [Argo CD automated sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/).

### Do not use imperative Argo rollback with automated sync

With automated sync enabled, rollback is a Git revert or a new Git commit referencing the prior digest. The official documentation notes that direct rollback cannot be performed while automated sync is enabled. The plan therefore keeps Git as the auditable source of truth. See [Argo CD automated sync and rollback note](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/).

## Additional finding not stated clearly in the feedback

The previous outline contained eight phases numbered 0-7, not seven. The saved execution plan now uses eight conventional phases numbered 1-8 so AK tooling, humans and evidence paths agree.

The current `docs/coursework.md` still says AWS/Kubernetes/LLM are optional or excluded. Because the user explicitly activated Phase 2, Phase 1 of the plan requires rewriting that document before code. The immutable Phase 1 boundaries remain in `docs/mini_coursework.md` and `AGENTS.md`.

The repo-mandated project skill `financial-distress-sdd` could not be found under `.codex/skills/` or the available skill catalog. No replacement skill was fabricated; the plan used the available `ak:plan` and `ak:devops` workflows. This is a tooling/configuration gap, not an architecture blocker.

## Final disposition

- Accepted: 14 feedback groups.
- Accepted with correction: 4 technical claims.
- Rejected: lowering rubric quality gates, tag-only deployment, and imperative rollback under automated sync.
- Blocking questions: none.
