---
title: "Phase-03 GKE bootstrap complete: Knative/KServe, Argo CD, Ansible"
date: 2026-08-07
summary: "Finished remaining phase-03 infra: Knative+KServe CRDs, Argo CD GitOps adoption, idempotent Ansible role, docs/submission skeleton"
---

# Phase-03 GKE bootstrap complete: Knative/KServe, Argo CD, Ansible

## What happened

Completed the remaining phase-03 day-1 infra steps (13-16) on top of the
already-provisioned GKE cluster (`fsds-evidence`, project
`project-60655616-d84a-4883-867`, asia-southeast1-b):

- **Knative Serving v1.16.0 + net-kourier + KServe v0.14.1**: installed via
  `kubectl apply`/`--server-side`, then vendored as plain manifest files
  (`financial-distress-gitops/platform/inference/vendored/`) — explicitly
  NOT via Kustomize (phase-03's Scope Changes locked Kustomize out; caught
  this mid-implementation after drafting a `kustomization.yaml` and
  reverted it). 21 CRDs confirmed present.
- **Argo CD bootstrap**: Helm-installed, AppProject + 4 Applications
  (nginx-ingress, cert-manager, platform-security, platform-inference) +
  1 ApplicationSet (`dev-apps`, directory generator over `apps/dev/*`,
  empty until phase-06/07). Private repo access needed a GitHub token
  Secret (`gh auth token`) — repo-server/applicationset-controller needed a
  restart to pick it up. `cert-manager` and `platform-security` adopted
  cleanly (Synced). `nginx-ingress` and `platform-inference` settled at
  Healthy/OutOfSync — traced to GKE cloud-controller annotation churn and
  Knative webhook `caBundle` self-injection, both benign; added
  `ignoreDifferences` for the diagnosed fields, some cosmetic residual
  drift remains (documented, not blocking).
- **Ansible role** (`docker`, `gcp-k8s-tools`, `benchmark-client`) for the
  evidence VM, SSH via IAP tunnel (OS Login, no public IP). Two real bugs
  hit and fixed: Google Cloud's apt key needed `gpg --dearmor` (ASCII-armored
  source, not the binary format apt expects), and the VM's service account
  lacked `roles/container.developer` (added `terraform/gcp/iam.tf`).
  **Idempotency proven**: run 1 `changed=4 failed=0`, run 2 `changed=0
  failed=0` — exact match to the plan's success criterion.
- **`docs/submission/`** reviewer index scaffolded (7 pages) in the source
  repo, linking into `docs/platform/evidence/` per the evidence contract
  (index, not relocation).
- Updated phase-03's success-criteria checkboxes: 9 of 12 now checked with
  evidence notes; 3 remain (CI/image-digest pipeline needs phase-07, direct-
  backend-refused and gcp-down/up cost-delta need formal phase-08 capture).
  `status: todo` -> `in-review`.

## Decision

Real GCP quota surprise: the region's `CPUS` quota (32) was NOT the binding
constraint — `CPUS_ALL_REGIONS` (project-wide, 12) was, discovered only when
the first `terraform apply` failed mid-provision (`GCE_QUOTA_EXCEEDED`).
Collapsed the two-pool design to one `e2-standard-8` pool + the evidence VM
(10/12 vCPU used). User was also offered a GCP->AWS pivot when GCP appeared
to be "out of credit" (a UI/billing-lag misread, not real exhaustion) and
explicitly declined once told EKS has no free-tier control plane — stayed
on GCP.

## Next steps

- User: run `sudo pacman -S ...` for any remaining local tooling gaps (none
  currently blocking).
- Phase-04: Feast, Airflow RAG pipeline, PGVector, observability stack
  (Prometheus/Grafana/Loki/Jaeger) — `docs/submission/observability.md`
  notes the platform is ready to host it.
- Phase-06/07: real FastAPI/agent/MCP services under `apps/dev/*` (activates
  the `dev-apps` ApplicationSet), CI/CD digest-promotion pipeline, real
  Ingress routes replacing the throwaway `hello-web` test.
- Phase-08: formal evidence capture for the 3 remaining unchecked success
  criteria, plus real cost/credit-usage screenshots once GCP billing
  reporting catches up.
- Minor follow-up: chase the residual cosmetic OutOfSync on nginx-ingress
  Service / Knative webhooks if exact Synced status matters later.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
