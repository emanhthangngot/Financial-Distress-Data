# Runtime health RCA

## Executive Summary
- Issue: remaining Argo/runtime signals after the August 13 GitOps fixes.
- Impact: likely limited to Argo status noise and one possible security app health issue; Phase 2 user path was previously verified live on 2026-08-12.
- Root cause: mixed. `platform-agents` and `nginx-ingress` have direct Git evidence for recent drift/CRD fixes; `platform-inference` has operator-owned webhook drift ignore rules; `platform-security` has no matching ignore/health override and is the most plausible real remaining failure. `kagent-grafana-mcp Forbidden` likely RBAC-denied tool behavior, not platform outage.
- Status: blocked on live cluster/network access from this session. Local `kubectl` cannot reach the API server.
- Smallest safe remediation: do not change manifests blind. First re-run live Argo/kubectl checks from a network-capable shell; only refresh/sync stale apps or add narrowly-scoped ignore/health handling once the exact offending resource is observed.

## Timeline
- 2026-08-12: live Phase 2 E2E report recorded PASS, 14 required workloads ready, traces and Prometheus targets healthy (`plans/reports/e2e-integration-260812-1742-end-to-end-verification.md`).
- 2026-08-13: GitOps branch contains post-E2E drift fixes for kagent CRDs, operator-managed diff handling, and nginx ingress drift (`financial-distress-gitops` commits `25bb4e3`, `61e6c64`, `14f7763`).
- 2026-08-13 11:29 ICT: this session attempted live inspection; every `kubectl` call failed with `dial tcp 136.85.120.118:443: socket: operation not permitted`.

## Technical Analysis
### Evidence
- Live access blocker:
  - `kubectl get applications.argoproj.io -A` -> `Unable to connect to the server: dial tcp 136.85.120.118:443: socket: operation not permitted`
- Prior live-good evidence:
  - `plans/reports/e2e-integration-260812-1742-end-to-end-verification.md:11-18`
  - same report states prior `platform-agents` failure was unrelated pre-existing CRD sync failure and required service path still passed (`:51`).
- Recent GitOps remediations:
  - `argocd/applications/platform-agents-crds.yaml` separates CRDs and uses `Replace=true`.
  - `argocd/applications/platform-agents.yaml` uses `ServerSideApply=true`.
  - `argocd/applications/platform-inference.yaml` ignores operator-owned webhook mutation.
  - `argocd/applications/nginx-ingress.yaml` ignores GKE LB service mutation plus Argo tracking annotation.
  - git history: `25bb4e3 fix(agents): apply kagent CRDs before controller`, `61e6c64 fix(argocd): ignore operator-managed resource drift`, `14f7763 fix(ingress): ignore Argo tracking annotation drift`.

### Hypotheses
1. Stale Argo app status after already-corrected GitOps manifests.
   - Supported for `platform-agents`, `platform-inference`, `nginx-ingress`.
2. Real remaining drift/health issue in one app despite the fixes.
   - Most plausible for `platform-security`, because no ignore/health customization exists there and it owns cert-manager/ClusterIssuer/SealedSecret resources that often report transient or operator-specific health.
3. Runtime outage in agent workloads.
   - Weaker. Last live E2E proves required workloads and service path were healthy on 2026-08-12, and no manifest regression is visible in the inspected files.

### Findings by signal
1. `platform-agents` health `Progressing`
   - Classification: most likely stale Argo status or reconciliation still pending, not a newly proven runtime failure.
   - Why: prior root cause was oversized CRD annotation + missing API mapping (`plans/reports/e2e-integration-260812-1742-end-to-end-verification.md:51`). The current repo now has the targeted fix split across `platform-agents-crds.yaml` and `platform-agents.yaml`.
   - Smallest safe remediation: `argocd app get platform-agents{,-crds}` + refresh; if resources are healthy and CRDs established, hard refresh/sync only. Do not edit manifests unless live diff still shows a specific object failing.

2. `platform-inference` health `Progressing`
   - Classification: likely operator-owned/stale health, not enough evidence for a real failure.
   - Why: manifest explicitly ignores Knative-managed webhook drift in `argocd/applications/platform-inference.yaml`. The app includes KServe/Knative bootstrap plus two InferenceServices; those frequently remain `Progressing` while controllers settle even when the service path works.
   - Counterpoint: cannot exclude a still-not-ready `InferenceService` or loader Job without cluster access.
   - Smallest safe remediation: inspect live health tree for `InferenceService fd-chat-model`, `InferenceService fd-embeddings`, and Knative/KServe pods; refresh app if only webhook/config drift remains.

3. `platform-security` health `Degraded`
   - Classification: most plausible real remaining failure.
   - Why: unlike inference and ingress, this app has no `ignoreDifferences` or custom health handling. It manages cert-manager-related and SealedSecret-related resources. `cert-manager-values.yaml` only records values, while raw manifests in `platform/security/` include `ClusterIssuer`, SealedSecrets, default-deny policy, and a vendored sealed-secrets controller. Any missing secret material, issuer readiness, or health mismatch can leave the app degraded.
   - What is not proven: exact failing resource.
   - Smallest safe remediation: identify degraded child resource first (`argocd app get platform-security -o json` or tree view). Then:
     - if only `ClusterIssuer` readiness/ACME pending -> no manifest change; wait or refresh.
     - if `SealedSecret` template placeholder still exists in live target -> replace only that secret with real sealed ciphertext.
     - if Argo health plugin misclassifies a healthy CRD-backed resource -> add narrow custom health/ignore rule only for that kind.

4. `nginx-ingress` `OutOfSync`
   - Classification: likely operator-owned drift or stale status, not a real service failure.
   - Why: latest commit `14f7763` exists specifically to ignore the Argo tracking annotation drift on the GKE-managed LoadBalancer Service, and the app already ignores GKE target-pool/NEG/status mutation in `argocd/applications/nginx-ingress.yaml`.
   - Smallest safe remediation: refresh the app. If still `OutOfSync`, inspect the remaining live diff and extend ignore rules only for the exact GKE-mutated field, not broadly.

5. `kagent-grafana-mcp` `Forbidden` messages
   - Classification: likely real RBAC denial but not a platform health failure.
   - Why: no GitOps manifest in the inspected repo grants special Grafana/Kubernetes RBAC to a `kagent-grafana-mcp` component, and the string does not appear in the source or GitOps repo. That pattern fits an optional MCP/tool attempting an unauthorized read rather than a core serving-path outage.
   - Smallest safe remediation: identify the actor and denied verb/resource from logs. If this MCP is required, bind least-privilege RBAC for only those reads. If not required, disable the MCP/tool registration instead of widening access.

6. Pods and kagent Agents
   - Classification: unverified live status in this session.
   - Best available evidence: 2026-08-12 live E2E proved required workloads ready and functional. GitOps manifests define three sandbox deployments plus kagent controller-side resources, but current pod readiness cannot be proved without API access.
   - Smallest safe remediation: from a network-capable shell run:
     - `kubectl get pods -A`
     - `kubectl get agents.kagent.dev -A`
     - `kubectl get sandboxagents.kagent.dev -A`
     - `kubectl get applications.argoproj.io -A`

## Recommended live verification commands
- `kubectl get applications.argoproj.io -A -o wide`
- `argocd app get platform-agents`
- `argocd app get platform-agents-crds`
- `argocd app get platform-inference`
- `argocd app get platform-security`
- `argocd app get nginx-ingress`
- `kubectl get crd | grep kagent`
- `kubectl get pods -A | egrep 'kagent|knative|kserve|ingress|cert-manager|sealed|grafana|jaeger|prometheus'`
- `kubectl logs -n kagent deploy/kagent --since=30m`
- `kubectl logs -n <namespace> <kagent-grafana-mcp-pod> --since=30m`

## Unresolved Questions
- Which exact child resource keeps `platform-security` degraded?
- Does `platform-inference` still show a real not-ready `InferenceService`, or only delayed operator health?
- What exact subject/verb/resource pair is behind the `kagent-grafana-mcp` Forbidden log?
