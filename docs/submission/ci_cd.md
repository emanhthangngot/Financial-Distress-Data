# CI/CD

Row: `LLM-AC-12-CICD`. Source CI builds/tests/scans/signs and pushes an
immutable image + digest; a bot opens a GitOps PR changing the digest;
Argo CD reconciles the merged revision. Pushing a tag alone never deploys.

- Argo CD live (`argocd` namespace, GKE cluster `fsds-evidence`), bootstrapped
  2026-08-08. AppProject `fsds-evidence`, Applications: `nginx-ingress`,
  `cert-manager`, `platform-security`, `platform-inference`. ApplicationSet
  `dev-apps` (directory generator over `apps/dev/*`) scaffolded, empty until
  phase-06/07 add services.
- Six CI/CD workflows (build/test/scan/sign/digest-PR/promote): **TBD
  phase-05/07**.

Status: the deploy-path half (Argo CD) is live; the build/CI half is
phase-07 work.
