# Security

Row: `LLM-AC-17-SECURITY`. Identity + restricted-PSS sandbox namespace +
default-deny NetworkPolicy + budget controls, redacted audit evidence — the
mesh-free design (Istio dropped, see phase-03 Scope Changes).

- `platform/security/default-deny-networkpolicy.yaml` (GitOps repo) —
  applied per application namespace as each is created; the live GKE snapshot
  confirms the routed application namespaces and their NetworkPolicy boundary.
  The original server-side dry-run on 2026-08-08 remains a reproducible
  manifest check, while live status is recorded in the canonical security
  evidence.
- NetworkPolicy addon (Calico) enabled on the GKE cluster.
- No service-account key JSON anywhere; Workload Identity for in-cluster
  GCP access, `gcloud auth application-default login` for Terraform.
- Restricted-PSS sandbox namespace: executed evidence is recorded in the
  canonical agent sandbox rows under `docs/phase2/evidence/llm/`.

Status: the security rows are executed in the canonical matrix. Gateway
authentication and viewer-route captures are indexed separately under Routing
& Gateway and Observability; they are not inferred from the sandbox proof.
The final submission freeze still requires SHA restamping and the strict
two-repository audit.
