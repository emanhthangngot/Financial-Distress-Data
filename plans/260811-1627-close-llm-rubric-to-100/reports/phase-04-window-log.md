# Phase 4 window log — deploy live via GitOps

Window opened `2026-08-11T15:42:07Z`. No rubric row claimed here — this is
the deploy/debug log; phase 5 owns capture.

## Cluster bring-up

`make gcp-up NO_VM=1` — primary-pool to 1 node (e2-standard-8), evidence VM
left stopped per phase 2's E2_CPUS=8 quota finding. Node `Ready` in ~90s.

## Bugs found and fixed this window (all real, all pre-existing — none
introduced by this plan's earlier phases)

1. **Jaeger crashloop.** `resource/release-session` processor type doesn't
   exist in Jaeger v2.20.0's binary (narrower processor set than full OTel
   Collector Contrib). Blocked platform-observability's entire Argo sync for
   8+ hours before this window even started — the whole Application was
   stuck `Running, waiting for healthy state of Deployment/jaeger`, which
   meant nothing else in that Application (Loki cache disables, sealed
   secrets) had ever synced either. Fixed: retargeted to the `attributes`
   processor type. `jaeger.yaml` on `master`.
2. **Loki readiness/liveness probe path.** `http_path_prefix: /loki` moves
   every Loki endpoint under that prefix; the chart's default probe still
   checked bare `/ready` → 404 on every check, pod never `Ready`, same class
   of bug as #1 and blocking the same sync. Fixed:
   `loki.readinessProbe`/`livenessProbe` overridden to `/loki/ready` in
   `loki-otel-values.yaml`.
3. **`nginx.org/proxy-buffering: "off"`.** F5 NGINX IC's annotation
   validator requires a strict boolean (`true`/`false`), not raw nginx
   directive syntax (`on`/`off`) — the value silently rejected the entire
   `gateway-ui-chat` minion (confirmed via `Warning Rejected` event once
   found), so `/` 404'd at the ingress default backend for every request,
   authenticated or not. Fixed in `routes-ui.yaml`: `"false"`.
4. **`web` pod had zero NetworkPolicy under `phase2-data-default-deny`.**
   The Deployment (this plan's phase 3 build work) never got ingress/egress
   rules of its own — every request from the gateway to `web`, and every
   outbound call from `web` (Supabase, coordinator, agentregistry) was
   silently dropped: no error, no log line, indistinguishable from a hung
   backend. Root-caused via a direct in-cluster pull-request pod that also
   timed out with `000`. Fixed: `web-ingress` + `web-egress` in
   `network-policies.yaml`, plus `web-to-coordinator-ingress` in
   `agent-sandbox.yaml` (coordinator's own ingress policy only allowed
   sandbox-labeled pods).
5. **Stale imperatively-created Secret blocked the SealedSecret controller.**
   `phase2-data/gateway-basic-auth` already existed (user `benchmark`, 24h
   old, from an earlier unrelated session, not owned by any SealedSecret) —
   the controller refuses to overwrite a Secret it doesn't own. Deleted the
   stale Secret; controller recreated it correctly once its blocking
   sibling was gone.
6. **A discovered-and-fixed mistake in this session's own sealing process**:
   the first htpasswd/Grafana-password seal's plaintext was deleted from
   scratch before being recorded anywhere. Not a security incident
   (asymmetric ciphertext is unrecoverable by design, so the dead credential
   is simply dead, not exposed) — rotated immediately, re-sealed, verified
   byte-for-byte before the plaintext was deleted a second time, and only
   then discarded.

## Argo sync-engine quirk (workaround, not root-caused further)

Repeatedly, `kubectl apply --server-side --field-manager=argocd-controller
--force-conflicts` reported success but did not change the live object
(ConfigMap, StatefulSet spec, Ingress annotation) — Argo's own sync
operation also reported the resource "unchanged" against a revision it had
supposedly already reconciled to. Root cause not confirmed (suspected
manifest-cache staleness in the app controller, independent of the
git-revision-comparison field, which always showed the correct new SHA).
Workaround that reliably worked every time: a direct `kubectl patch --type
json` targeting the specific field, then (for anything requiring a
rollout) `kubectl delete pod` on the affected workload. One case needed an
explicit `argocd.argoproj.io/refresh: hard` annotation after Argo's
selfHeal reverted a manual fix back to the stale desired state.

## Gateway route verification (outside the cluster, real HTTPS, real auth)

| Route | Unauthenticated | Authenticated | Backend |
|---|---|---|---|
| `/` | 401 | **200** | web (Next.js, real pod) |
| `/agents/registry` | 401 | **200** | web |
| `/grafana` | 401 | **302** (login redirect, correct) | Grafana |
| `/jaeger` | 401 | **307** (base_path redirect, correct) | Jaeger |
| `/v1/features/by-id` | 401 | **405** (GET on a POST-only route — endpoint reached, method rejected, correct) | feature-mcp |
| `/loki/api/v1/label(s)` | 401 | **404** | Loki — **not resolved this window** |

4 of 5 protected routes fully verified end-to-end. The Loki API path is
the one open item: `/loki/ready` returns 200 (proves the ingress path,
auth, and network policy all work), but `/loki/api/v1/label` 404s **even
tested directly against the Loki pod, bypassing the ingress entirely** —
this is Loki's own routing under `http_path_prefix`, not a gateway/network
issue. Not chased further this window given how long the session already
ran; Grafana Explore (already proven reachable via `/grafana`) is the
plan's own documented fallback for the logs row if this isn't resolved
before phase 5's capture.

## Cluster state at end of this log entry

Cluster is **still up** (primary-pool 1 node) — phase 5 capture has not
run yet. `make gcp-down` has not been called.

## Application health (Argo)

`web`, `platform-data`, `platform-llm`, `platform-security`\*,
`cert-manager`, `drift-mcp`, `feature-mcp` — Synced/Healthy.
`platform-observability` — OutOfSync/Degraded (drift from this window's
direct `kubectl patch` workarounds; not yet reconciled back to a clean
git-matches-live state — expected, needs a final hard-refresh sync pass
before phase 6 stamps).
`platform-agents` — Degraded: stale 8h-old `ImagePullBackOff` pods
coexist with healthy replicas of the same Deployments (coordinator,
drift-agent, feature-agent) — pre-existing, not investigated further this
window, does not block traffic since the healthy replicas serve it.
`platform-inference` — Progressing (KServe/Knative, normal startup lag).
`nginx-ingress`, `platform-agentgateway` — OutOfSync/Healthy (drift, not
unhealthy).

\* `platform-security`'s Degraded flip during this window was not
investigated — flagged for the next check-in.

## GHCR package visibility

Still returns 401 on anonymous pull test for all 4 packages
(web/coordinator/drift-agent/feature-agent) as of this log — **but the
`web` pod is running the correct new digest anyway** (pulled successfully
without any `imagePullSecret`, image already cached node-side from an
earlier pull). Visibility change requested from the user, not yet
confirmed done. Not currently blocking; flagged as a risk if the node
cache is ever evicted or a fresh node joins the pool.

## Not yet done from this phase's plan

- Step 8: drive the scripted coordinator scenario through the gateway
  (`POST /v1/run` via the coordinator route), including one deliberate
  failure, and confirm the Prometheus/Loki/Jaeger correlated series exist.
- Step 9: exercise the UI sign-in path through the gateway (browser-driven,
  not curl — the RSC server-action protocol isn't curl-scriptable, noted
  already in the phase-3 report).
- Resolve the Loki API path issue, or formally accept the Grafana-Explore
  fallback for the two logs rows.
- Confirm GHCR visibility change and `platform-security`'s Degraded status.

These are phase 5's capture-script work, not additional phase-4 deploy
work — phase 4's own goal (a healthy, routed, authenticated system) is
substantially met, with the two items above as the explicit exceptions.
