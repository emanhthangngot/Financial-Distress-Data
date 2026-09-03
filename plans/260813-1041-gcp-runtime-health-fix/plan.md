# GCP runtime health fix

Status: complete

## Objective

Repair the observed GKE/ArgoCD health issues without changing the Phase 2
application contracts: the orphan `default/web` Deployment, the missing
kagent `Agent` and `SandboxAgent` CRDs, and the GitOps drift caused by the
existing uncommitted operational changes.

## Expected output

1. GitOps manifests that install the kagent CRDs through an apply strategy that
   accepts their large OpenAPI schemas and allows the controller to start.
2. A clean cluster state where the real `phase2-data/web` is ready and the
   orphaned broken `default/web` Deployment is removed.
3. A durable GitOps change set preserving the existing OTLP policy, E2E Make
   target, and drift scenario changes, with validation evidence.
4. A detailed report with ArgoCD, workload, live coordinator, telemetry, and
   regression-test results.

## Acceptance criteria

- ArgoCD `platform-agents` -> applies `agents.kagent.dev` and
  `sandboxagents.kagent.dev` -> both CRDs exist, report `Synced`, are
  `Established=True`, and are discoverable through the Kubernetes API.
- kagent controller -> reconciles the installed API types -> one ready
  controller replica with no new crash loop or rest-mapping error.
- GitOps `phase2-data/web` -> resolves its namespaced runtime Secret -> the
  Deployment is ready; no broken orphan `default/web` remains.
- Existing GitOps OTLP NetworkPolicy -> remains namespace/port scoped -> live
  coordinator E2E continues to export Jaeger traces and Prometheus targets
  remain healthy.
- Source and GitOps validation -> runs without new lint, manifest, or contract
  failures -> live platform .2E and applicable repository tests pass.
- Secret handling -> uses the existing SealedSecret only -> no plaintext
  Supabase values, service-role key, or credentials are added to Git.

## Scope

In scope: `argocd/applications/platform-agents.yaml`, the already-dirty
GitOps operational files (`Makefile`, `apps/dev/web/values.yaml`,
`platform/agents/agent-sandbox.yaml`), and cleanup of the exact orphan
`default/web` Deployment. Out of scope: platform .AGs, application API/schema
changes, new cloud infrastructure, and routine credential rotation. An
emergency Grafana Viewer token rotation was performed only to invalidate a
diagnostic-exposed token; no plaintext credential was committed.

## Implementation

1. Keep server-side apply for the kagent controller/application resources, but
   move the `kagent-crds` chart into a separate Argo Application with an early
   sync wave and `Replace=true`; this option then applies only CRDs and avoids
   the oversized client-side annotation without replacing agent Deployments.
2. Validate the rendered CRD chart with server-side dry-run and inspect Argo's
   previous sync failure before applying the durable change.
3. Render and server-side dry-run the agent application, checking that CRDs are
   accepted before dependent `Agent`/`ModelConfig` resources; only add a
   missing-resource dry-run option if the live Argo evidence proves it is
   required.
4. Capture the exact `default/web` manifest and ownership metadata, confirm it
   has no Argo tracking/owner reference, confirm `phase2-data/web` is ready,
   then remove only that orphan Deployment.
5. Commit the GitOps changes on an isolated branch, push/merge only within the
   authorized deployment workflow, and wait for Argo reconciliation.

## Verification

- `helm template` and Kubernetes server-side dry-run for the kagent CRDs.
- GitOps YAML/Helm validation and `git diff --check`.
- Source platform .ocused tests and web typecheck/lint/test where applicable.
- `scripts/run_phase2_e2e.py --json --timeout 120`.
- ArgoCD application health, workload readiness, Prometheus targets, and
  Jaeger service/trace checks.

## Completion summary

- GitOps PRs `#50` through `#65` merged in `financial-distress-gitops`; final
  Grafana MCP commits: `9b3a8f0`, `239de4c`, `1a86f8a`.
- Live cluster context verified:
  `gke_project-60655616-d84a-4883-867_asia-southeast1-b_fsds-evidence`.
- ArgoCD -> reconciles deployed apps -> `13/13` applications `Synced/Healthy`.
- kagent CRDs -> apply and register -> `Established=True`; controller ready;
  built-in Agents `Ready`.
- `kagent-grafana-mcp` RemoteMCPServer -> reconciles successfully ->
  `Accepted=True`, `Reconciled`; controller registered `65` tools.
- Direct MCP initialize probe -> reaches service endpoint -> HTTP `200`.
- SealedSecret controller -> unseals the active Grafana token -> condition
  `Synced=True`; the intermediate stale-certificate ciphertext was replaced
  through PR `#65`.
- `scripts/run_phase2_e2e.py` after the fix -> validates full platform .untime
  path -> PASS `28/28`.
- Source gate -> validates repo health -> PASS (`311` pytest, `ruff`, `black`,
  `docker compose config`, Stage 1 evidence audit).
- Web checks -> validate product plane -> PASS (`184` tests, typecheck/lint,
  live e2e `6`, assistant e2e `6`).

## Residuals

- GHCR web image -> still points at a private digest -> cached node currently
  serves web, but a cold-node image pull still depends on a user-provided
  `read:packages` credential delivered out-of-band.
- `ghcr-pull-secret` placeholder -> intentionally excluded/invalid in GitOps ->
  no secret material added to Git; cold-node recovery remains an operator step
  until the user supplies a sealed credential.

## Final live closeout

- ArgoCD -> evaluates every managed application -> `13/13 Synced/Healthy`.
- kagent controller -> registers Grafana MCP -> `Accepted=True`, `65` tools,
  and no new `Forbidden`, rest-mapping, crash-loop, or panic errors in the
  final five-minute log window.
- Temporary token-creator pods -> finish credential rotation -> deleted; two
  obsolete Grafana Viewer service accounts were removed, leaving only the
  active account for the sealed runtime Secret.

## Rollback

Revert the GitOps commit if the managed `phase2-data/web` or agent path
regresses. The captured `default/web` manifest is rollback evidence only; do
not restore that orphan or its broken Secret reference unless ownership and
namespace intent are re-established explicitly.
