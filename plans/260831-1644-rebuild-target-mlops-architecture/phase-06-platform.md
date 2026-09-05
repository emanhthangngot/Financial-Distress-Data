---
phase: 6
title: "Phase 6: GKE platform, Istio mesh, Vault secrets, Terraform + Ansible"
status: pending
priority: P1
effort: "10-14 days"
dependencies: ["phase-00-gates.md", "phase-03-contracts-rubric.md"]
owns: ["platform/istio/", "platform/security/", "platform/vault/", "infra/ansible/", "terraform/", "all Argo destination.namespace fields"]
---

# Phase 6: GKE platform, Istio mesh, Vault secrets, Terraform + Ansible

## Overview

Apply the final namespace topology; deploy Istio (PERMISSIVE, then mTLS STRICT); restore Vault + ESO;
verify sandbox NetworkPolicy isolation survives injection; verify Job termination on the G4 branch;
and build the **Ansible role tree** the rubric names but the previous plan never owned.
Runs in parallel with P5 — no shared files. **Resident cost: 7-9 vCPU always-on.**

Two rubric rows land here and nowhere else:

| Row | Requirement | Points |
|---|---|---|
| ML 54 | "Using **service mesh** to authorize access from service to service" | 1 |
| ML 53 / LLM 57 | "Centralize secret management via **HashiCorp Vault** (or similar tools) so it will be used across the whole organization" | 2 |
| ML 44 / LLM 48 | "Dùng **Ansible** để configure và deploy các service lên VM — **cần chia thành các role** để code clean hơn" | 3 |

Ansible had **no owning phase** in the previous plan (grep of all 10 phase files, 2026-09-01: zero
matches). The rubric explicitly grades the *role decomposition*, not merely that Ansible ran.

## Requirements

- Functional:
  - istiod and Kiali `Healthy`; mTLS STRICT enforced; Kiali renders the service graph.
  - Istio `AuthorizationPolicy` denies an unauthorized service-to-service call and permits an
    authorized one — the observable form of ML 54.
  - Vault + ESO reconcile `ExternalSecret` objects; the resulting Secret is byte-identical to the
    sealed-secrets value it will replace at P10.
  - `agents-sandbox` default-deny stays scoped to `agentgateway-system` **after** injection.
  - Ansible configures and deploys the evidence VM services, decomposed into roles, idempotent on
    a second run.
  - Terraform provisions GKE with the P0-approved topology and no phase label.
- Non-functional: PERMISSIVE → STRICT with zero inter-service breakage; KServe 0.18 routes through
  `net-istio` with no `net-kourier` resources; G4 Job termination verified on **real**
  Kubeflow/Spark/Airflow Jobs, not a synthetic sleep.

## Architecture

```
namespaces
  dataflow            (was phase2-data)
  kserve              (absorbs the dissolved phase2-llm)
  observability       (was monitoring; stack lands in P12)
  security            Vault + ESO
  istio-system        istiod + Kiali + GatewayClass: istio
  ci                  Jenkins (P10)
  rollouts            Argo Rollouts (P10)
  kubeflow            KFP + KubeRay (P7)
  tracking            MLflow (P7)
  analytic            Trino + Superset (P9)
  api-serving / web / ingress / keda
  agentgateway-system │ kagent │ agents-sandbox   ← three-namespace boundary, preserved

infra/ansible/
  inventories/evidence-vm.yml
  roles/common/        base packages, users, hardening
  roles/docker/        engine + compose plugin
  roles/observability-agent/  node exporter, promtail
  roles/lakehouse-local/      MinIO + Postgres compose stack
  roles/evidence-capture/     capture tooling + cron
  site.yml
```

## Related Code Files

- Restore from archive: `platform/security/authorization-policies.yaml`,
  `platform/security/vault-external-secrets.yaml`
- Create: `platform/istio/` Helm values (istiod, Kiali, `GatewayClass: istio`)
- Create: `platform/vault/` Helm values (Vault + ESO)
- Create: `infra/ansible/` — `site.yml`, `inventories/`, and the five roles above
- Modify: every Argo `destination.namespace` field
- Modify: `financial-distress-gitops/terraform/gcp/` — approved topology, `component=unified-platform`
- Create: `tests/platform/test_ansible_roles.py` — asserts the role tree exists and `site.yml`
  references every role (structure test; execution is proved by AC-P6-7)

## Implementation Steps

1. **Namespace topology** (1 d) — rename `phase2-data` → `dataflow`; dissolve `phase2-llm` into
   `kserve`; create `security`, `ci`, `rollouts`, `kubeflow`, `tracking`, `analytic`; stub
   `observability`. Update every Argo `destination.namespace`.
2. **Istio PERMISSIVE + soak** (2-3 d) — deploy `platform-istio` (istiod, Kiali,
   `GatewayClass: istio`) in PERMISSIVE; soak 24 h; run `istioctl analyze`; watch existing workloads
   for injection errors.
3. **AuthorizationPolicy** (1 d) — restore `platform/security/authorization-policies.yaml`; apply
   per namespace on the drawn edges only.
4. **mTLS STRICT** (1 d) — apply `PeerAuthentication` STRICT; verify every drawn edge succeeds and a
   plaintext call from outside the mesh is refused.
5. **Prove ML 54 as behaviour** (0.5 d) — from a namespace with **no** `AuthorizationPolicy` grant,
   call `api-serving`; expect RBAC denial. From a granted namespace, expect success. Capture both.
6. **G4 verification on real Jobs** (1 d) — run an injected Kubeflow, Spark and Airflow Job; verify
   each reaches `Completed` within its deadline, or record branch B and exclude those namespaces.
7. **Sandbox negative test after injection** (1 d) — egress from `agents-sandbox` directly to
   `kserve` is refused; the same call through `agentgateway-system` succeeds.
8. **Vault + ESO** (2-3 d) — restore `vault-external-secrets.yaml`; deploy `platform-vault`; unseal;
   configure backends and policies; reconcile a non-critical `ExternalSecret` first.
9. **Ansible role tree** (2 d) — author `infra/ansible/` with the five roles; run `site.yml` against
   the evidence VM; run it a second time and verify `changed=0` (idempotence); capture
   `ansible-playbook --check` output as evidence.
10. **Terraform apply** (1 d) — the P0-approved topology; confirm no resource carries a phase label.

## Success Criteria

- [ ] AC-P6-1: Argo CD → syncs `platform-istio` → istiod and Kiali `Healthy`; Kiali renders a graph
      containing `api-serving`, `agents` and `kserve`
- [ ] AC-P6-2: Platform operator → applies `PeerAuthentication` STRICT → every inter-namespace call
      on a drawn edge succeeds; a plaintext call from outside the mesh is refused
- [ ] AC-P6-3 **(ML 54)**: Caller in a namespace without an `AuthorizationPolicy` grant → calls
      `api-serving` → receives an RBAC denial; the same call from a granted namespace succeeds
- [ ] AC-P6-4: Sandbox negative test **after injection** → egress from `agents-sandbox` directly to
      `kserve` is refused; through `agentgateway-system` it succeeds
- [ ] AC-P6-5: Platform operator → lists namespaces → `agentgateway-system`, `kagent` and
      `agents-sandbox` all exist as distinct namespaces; the sandbox retains restricted PSS,
      a tokenless ServiceAccount and read-only root
- [ ] AC-P6-6 **(ML 53 / LLM 57)**: ESO → reconciles an `ExternalSecret` from Vault → the resulting
      Secret is byte-identical to the sealed-secrets value it will replace; Vault is reachable from
      more than one namespace, demonstrating org-wide use
- [ ] AC-P6-7 **(ML 44 / LLM 48)**: Operator → runs `ansible-playbook site.yml` against the evidence
      VM → services are configured and deployed; a **second run reports `changed=0`**;
      `infra/ansible/roles/` contains at least five distinct roles referenced by `site.yml`
- [ ] AC-P6-8: Platform operator → runs an Istio-injected Kubeflow, Spark and Airflow Job → each
      reaches `Completed` within deadline, or G4 branch B is recorded and those namespaces are excluded
- [ ] AC-P6-9 **(ML 43 / LLM 47)**: Terraform operator → applies the approved topology from
      `financial-distress-gitops/terraform/gcp/` → **GKE cluster, both node pools, the evidence VM
      and the network are created by Terraform, not by console or `gcloud`**; `terraform state list`
      accounts for every cloud resource the platform runs on; planned and applied resources carry
      `component=unified-platform` and no phase label. State is remote-backed, and `terraform plan`
      on a clean tree reports **no drift**

## Risk Assessment

**Risk:** PERMISSIVE → STRICT breaks an existing call. Signal: 503s between namespaces after the
switch. Mitigation: 24 h PERMISSIVE soak with `istioctl analyze`. Response: revert
`PeerAuthentication` to PERMISSIVE; fix the specific service; re-attempt.

**Risk:** Istio injection breaks Knative-routed KServe. Signal: `InferenceService` revisions stop
routing through `net-istio`. Mitigation: install and smoke-test the Istio `GatewayClass` and
`InferenceService` route before deleting the old Kourier resources. Response: roll back the
`net-istio` cutover as one GitOps revision; do not retain two active network layers.

**Risk:** Vault unsealing fails or rotation breaks ESO. Signal: `ExternalSecret` stuck
`SecretSyncedError`. Mitigation: test with a non-critical secret first; ESO is purely additive until
the P10 flip. Response: roll back to sealed-secrets; the flip has not happened yet.

**Risk:** Ansible is written as one monolithic playbook. Signal: `roles/` has fewer than five
directories, or `site.yml` inlines tasks. Mitigation: AC-P6-7 counts roles. Response: decompose —
the rubric grades the role split explicitly.

**Risk:** Ansible is not idempotent, so a second run reports changes. Signal: `changed>0` on run two.
Mitigation: use module state declarations, never `shell:` for anything a module covers. Response:
replace the offending task with a proper module; `changed=0` is the graded assertion.

**Risk:** Istio's 5-6 always-on vCPU pushes the resident floor past the approved quota. Signal:
pods `Pending` on `Insufficient cpu` after P6. Mitigation: P0 G0 branch A must be recorded before
P6 opens. Response: selective injection — mesh only `kserve`, `agents` and `api-serving`, which is
sufficient for AC-P6-3, and record the reduction in ADR-016.

## Rubric Citations (phase-03 R-12 closure, appended 2026-09-05)

Every rubric row this phase owns per `docs/rubric-matrix-unified.csv`'s `owning_phase` column, cited so `scripts/verify_rubric_coverage.py` can resolve ownership to an assertion (R-12). Each line names the row's real `rubric_id`, its stated requirement, and its proof artifact/deliverable — the row's own matrix columns, not invented text. Rows whose capability is not yet implemented are forward specs, matching this file's other `AC-P6-*` entries.

- AC-P6-RUBRIC-1: `LLM-iac-d-ng-ansible-configure-v-deplo` — platform_operator -> delivers "Dùng Ansible để configure và deploy các service lên VM ; (cần chia thành các role để code clean hơn)" -> Capture màn hình thể hiện từng setup đã chạy thành công (evidence: `docs/platform/evidence/llm/LLM-iac-d-ng-ansible-configure-v-deplo.md`)
- AC-P6-RUBRIC-2: `LLM-iac-d-ng-terraform-setup-gke-ho-c-` — platform_operator -> delivers "IaC — Dùng Terraform để setup GKE hoặc các cloud services (để ý cách chia folder theo từng service nếu có, ví dụ như sau)" -> Capture màn hình thể hiện từng setup đã chạy thành công (evidence: `docs/platform/evidence/llm/LLM-iac-d-ng-terraform-setup-gke-ho-c-.md`)
- AC-P6-RUBRIC-3: `ML-iac-d-ng-ansible-configure-v-deplo` — platform_operator -> delivers "Dùng Ansible để configure và deploy các service lên VM ; (cần chia thành các role để code clean hơn)" -> Capture màn hình thể hiện từng setup đã chạy thành công (evidence: `docs/platform/evidence/ml/ML-iac-d-ng-ansible-configure-v-deplo.md`)
- AC-P6-RUBRIC-4: `ML-iac-d-ng-terraform-setup-gke-ho-c-` — platform_operator -> delivers "IaC — Dùng Terraform để setup GKE hoặc các cloud services (để ý cách chia folder theo từng service nếu có, ví dụ như sau)" -> Capture màn hình thể hiện từng setup đã chạy thành công (evidence: `docs/platform/evidence/ml/ML-iac-d-ng-terraform-setup-gke-ho-c-.md`)
