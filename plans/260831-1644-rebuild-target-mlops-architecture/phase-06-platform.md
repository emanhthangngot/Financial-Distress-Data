---
phase: 6
title: "Phase 6: GKE platform, Istio mesh, Vault secrets, Terraform + Ansible"
status: pending
priority: P1
effort: "10-14 days"
dependencies: ["phase-00-gates.md", "phase-03-contracts-rubric.md"]
owns: ["platform/istio/", "platform/security/", "platform/vault/", "infra/ansible/", "terraform/", "all Argo destination.namespace fields"]
---

# Phase 6: Windowed platform, mesh, secrets, Terraform and Ansible

## Overview

Provision only a P0-verified no-additional-spend window. Kubernetes, cloud Terraform and VM Ansible
are real rubric deliverables; local manifests or Kaggle jobs cannot replace cloud deployment proof.
No assumed 48-vCPU budget, fixed pool count, 24-hour soak or always-on service floor.

## Requirements and selected topology

Use existing platform deployment patterns; preserve three namespace boundaries
`agentgateway-system`, `kagent`, `agents-sandbox`. Mesh authorization and centralized secrets remain
required capabilities. Vault/ESO and Istio are the chosen existing direction, not license to deploy
unneeded dashboards/controllers. Selective sidecar injection is allowed with explicit exclusions.
Do not claim excluded traffic has mTLS. Kiali is optional. Do not pin KServe/Knative versions from
historical prose; P0/P8 compatibility probes determine a jointly supported serving path.

Use Terraform for the actual approved cloud resources and remote state protected from secret
exposure; service-separated modules/folders and drift checks. The rubric allows GKE or cloud
services: enumerate which row is proved by which real resource, and keep K8s workload evidence
separate. No verified free resource means cloud AC stays blocked, not replaced with localhost.

Ansible must actually configure/deploy services to a VM using coherent roles (common, runtime,
service configuration, observability/capture where needed), then produce idempotent second-run
output. `--check` alone does not prove deployment; five role directories alone prove nothing.

## Ownership

Own mesh/security/Vault, cloud Terraform and Ansible. Namespace field edits are serialized with
workload owners P5/P7/P8/P9. P0 supplies read-only gates. P9 owns NGINX exposure and P12 dashboards;
P6 exposes early telemetry required by P10, without waiting for P12 final freeze.

## Implementation steps

1. Inventory namespaces, workloads, request limits, state and current security. Review approved
   Terraform plan and resource-specific teardown; do not apply absent P0 cost gate.
2. Apply approved resources through Terraform; capture state/resource IDs, protected backend and
   no-drift plan. Configure/deploy services through Ansible roles on the actual VM, then rerun.
3. Deploy mesh in PERMISSIVE only for a bounded compatibility window. Exercise every required
   service edge, Job completion and failure/retry path; inspect analyzer and error telemetry.
4. Apply authorization policy and STRICT on covered workloads; prove allowed/denied/plaintext calls.
5. Verify sandbox egress deny after injection, restricted PSS, tokenless ServiceAccount, read-only
   root and scoped gateway allow path. Framework tools must not bypass this network boundary.
6. Configure Vault/ESO least-privilege policies; test rotation and consumer recovery with a
   non-sensitive test secret first. Compare values without logging their bytes. Workload-issued
   TLS/ServiceAccount/controller secrets are not all forcibly ESO-managed.
7. If replacing existing secret delivery, cut over one consumer at a time with rollback retained
   until verification. Remove old managed credentials only after replacement works.
8. Export evidence/state backup; stop/destroy only authorized session resources; verify remaining
   disks, IPs, LBs, snapshots and other billable resources against the no-spend ledger.

## Success criteria

- [ ] AC-P6-1: GitOps operator -> reconciles selected mesh -> controller healthy and required request paths traced without requiring a Kiali deployment.
- [ ] AC-P6-2: Platform operator -> enables STRICT on covered edges -> authorized encrypted calls succeed and plaintext unauthorized calls fail.
- [ ] AC-P6-3: Unauthorized workload -> calls protected API -> denied; granted workload succeeds, proving service-mesh authorization (P9 rubric owner).
- [ ] AC-P6-4: Sandbox workload -> calls inference directly then through allowed gateway -> direct denied, scoped route succeeds after injection.
- [ ] AC-P6-5: Platform auditor -> inspects and exercises agent boundary -> three namespaces remain distinct with restricted PSS, tokenless identity and read-only root.
- [ ] AC-P6-6: Secret operator -> rotates a test credential through Vault/ESO -> authorized consumers in multiple namespaces update; unauthorized reads fail and logs reveal no value (P9 rubric owner).
- [ ] AC-P6-7: Ansible operator -> runs role-decomposed playbook twice on actual VM -> service checks pass and second run reports changed=0; capture commands and results.
- [ ] AC-P6-8: Data/ML operator -> runs real injected jobs -> completion and output verified, or specific namespaces excluded and remaining security accurately described.
- [ ] AC-P6-9: Terraform operator -> applies approved no-spend cloud plan -> real resources match protected state, labels and module boundaries; next plan has no drift. No free allocation means blocked, not passed.
- [ ] AC-P6-COST: Operator -> ends resource window -> exported evidence persists and no unapproved residual charge source remains; no 24/7 availability claim.

## Risks and verification

An alert is not a spending cap. If resource lifecycle cannot remain inside free allocation, stop
before apply. Mesh changes can break Jobs/streaming; use bounded real requests, not a blind soak.
Secret cutover can strand consumers; prove rotation/recovery before deleting old delivery.
Terraform validation and Ansible syntax/check mode are preflight only, not runtime proof.

## Rubric Citations (phase-03 R-12 closure, appended 2026-09-05)

Every rubric row this phase owns per `docs/rubric-matrix-unified.csv`'s `owning_phase` column, cited so `scripts/verify_rubric_coverage.py` can resolve ownership to an assertion (R-12). Each line names the row's real `rubric_id`, its stated requirement, and its proof artifact/deliverable — the row's own matrix columns, not invented text. Rows whose capability is not yet implemented are forward specs, matching this file's other `AC-P6-*` entries.

- AC-P6-RUBRIC-1: `LLM-iac-d-ng-ansible-configure-v-deplo` — platform_operator -> delivers "Dùng Ansible để configure và deploy các service lên VM ; (cần chia thành các role để code clean hơn)" -> Capture màn hình thể hiện từng setup đã chạy thành công (evidence: `docs/platform/evidence/llm/LLM-iac-d-ng-ansible-configure-v-deplo.md`)
- AC-P6-RUBRIC-2: `LLM-iac-d-ng-terraform-setup-gke-ho-c-` — platform_operator -> delivers "IaC — Dùng Terraform để setup GKE hoặc các cloud services (để ý cách chia folder theo từng service nếu có, ví dụ như sau)" -> Capture màn hình thể hiện từng setup đã chạy thành công (evidence: `docs/platform/evidence/llm/LLM-iac-d-ng-terraform-setup-gke-ho-c-.md`)
- AC-P6-RUBRIC-3: `ML-iac-d-ng-ansible-configure-v-deplo` — platform_operator -> delivers "Dùng Ansible để configure và deploy các service lên VM ; (cần chia thành các role để code clean hơn)" -> Capture màn hình thể hiện từng setup đã chạy thành công (evidence: `docs/platform/evidence/ml/ML-iac-d-ng-ansible-configure-v-deplo.md`)
- AC-P6-RUBRIC-4: `ML-iac-d-ng-terraform-setup-gke-ho-c-` — platform_operator -> delivers "IaC — Dùng Terraform để setup GKE hoặc các cloud services (để ý cách chia folder theo từng service nếu có, ví dụ như sau)" -> Capture màn hình thể hiện từng setup đã chạy thành công (evidence: `docs/platform/evidence/ml/ML-iac-d-ng-terraform-setup-gke-ho-c-.md`)
