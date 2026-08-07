# Security

Row: `LLM-AC-17-SECURITY`. Identity + restricted-PSS sandbox namespace +
default-deny NetworkPolicy + budget controls, redacted audit evidence — the
mesh-free design (Istio dropped, see phase-03 Scope Changes).

- `platform/security/default-deny-networkpolicy.yaml` (GitOps repo) —
  applied per application namespace as each is created; validated via
  `kubectl apply --dry-run=server` 2026-08-08, not yet applied to a live app
  namespace (none exist before phase-06).
- NetworkPolicy addon (Calico) enabled on the GKE cluster.
- No service-account key JSON anywhere; Workload Identity for in-cluster
  GCP access, `gcloud auth application-default login` for Terraform.
- Restricted-PSS sandbox namespace: **TBD phase-06** (agent sandbox row).

Status: platform-level controls live; app-level enforcement pending
phase-06/07.
