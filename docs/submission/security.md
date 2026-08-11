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
- Restricted-PSS sandbox namespace: executed evidence is recorded in the
  canonical agent sandbox rows under `docs/phase2/evidence/llm/`.

Status: the security rows are executed. Gateway authentication and viewer
routes are a separate live-evidence gap and remain design-only in the matrix;
they are tracked in `docs/submission/README.md` rather than being implied by
the sandbox proof.
