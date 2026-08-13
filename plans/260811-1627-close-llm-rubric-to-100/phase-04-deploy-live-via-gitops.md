---
phase: 4
title: "Deploy the edge, data and observability planes live via GitOps"
status: pending
priority: P1
effort: "0.5d (cluster up)"
dependencies: [3]
---

# Phase 4: Deploy the edge, data and observability planes live via GitOps

# 0 points

## Overview

Open the cluster window and reconcile the whole stack from GitOps `master`:
sealed secrets, observability, the data plane, the model plane, the web app, and
the five protected routes with TLS and auth. **No rubric row is claimed here.**
Its output is a healthy, routed, authenticated system with real telemetry in it.

## Requirements

- Functional: all five ciphertexts materialize as Secrets; `platform-observability`
  reaches `Synced/Healthy`; the certificate is `Ready=True` via the strategy
  chosen in phase 2; every protected route answers 401 unauthenticated and 200
  authenticated over HTTPS; the workload plane (data, model, MCP, agents, web) is
  `Running` and scraped; one real generation has flowed end to end.
- Non-functional: every rubric-bearing object arrives through Argo reconciliation
  of `master`. No imperative `kubectl apply`/`patch` on the rubric path.

## Architecture

**Five ciphertexts, not one.** `platform/ingress/basic-auth-sealed-secret.yaml`
carries three SealedSecrets across two namespaces with five
`REPLACE_WITH_KUBESEAL_OUTPUT` markers: `gateway-basic-auth` in `phase2-data`,
`gateway-basic-auth` in `monitoring`, and `grafana-admin-credentials`
(`admin-user` + `admin-password`) in `monitoring`. kubeseal's default scope binds
ciphertext to name+namespace, so the same htpasswd must be sealed **twice**.
`prometheus-values.yaml:4-11` sets `grafana.admin.existingSecret:
grafana-admin-credentials` with anonymous auth disabled — an unsealed Grafana
secret means the Grafana pod never becomes ready, which alone kills all six
observability rows and the viewer routes. Phase 3's `web-runtime-config` is the
sixth ciphertext.

**Sync order that matters:** sealed-secrets controller → Secrets materialize →
routes referencing `nginx.org/basic-auth-secret` (otherwise 503, not 401) →
certificate issuance → workload plane → telemetry has scrape targets.

**Capacity.** Follow phase 2's rendered budget: apply the named disables
(`chunksCache`, `resultsCache`), scale to zero what the budget named, and if the
budget said the secondary pool is required, stop the evidence VM first and use
the Makefile target added in phase 2. Never use `gcp-up` as a mid-window reset —
it restarts the VM and leaves the secondary pool at zero.

**The correlated scenario must be drivable without a browser.** Per the red
team, the primary scripted path is `POST /v1/run` against the coordinator
**through the gateway**, not a UI click: reproduction commands in evidence must
be non-interactive. The UI round-trip (phase 3's auth plane) is exercised
separately for the two UI rows.

## Related Code Files

- Modify (gitops `master`): `platform/ingress/basic-auth-sealed-secret.yaml`
  (five real ciphertexts), plus the `web-runtime-config` SealedSecret from phase 3
- Read/verify (gitops): `argocd/applications/platform-observability.yaml`,
  `platform/ingress/*`, `platform/observability/*`, `platform/agents/*`,
  `platform/llm/ab-testing.yaml`, `apps/dev/*/values.yaml`
- No source-repo change expected. If one is required, it goes through CI and a
  digest PR — never a hand patch on the cluster.

## Implementation Steps

0. Record the credit balance and window start in `docs/submission/cost.md`
   (uncommitted for now — the freeze phase owns the commit ordering). Confirm the
   trial billing account is not upgraded.
1. Bring the cluster up per phase 2's decisions (VM state and pool sizes chosen
   deliberately, not by the default `gcp-up`). Wait for `Ready` nodes and let
   Argo CD, cert-manager, sealed-secrets and NGINX reconcile first.
2. Verify the baseline: Applications `Synced/Healthy`, no `Pending` pods left
   from an earlier window, and the GitOps checkout/Argo both on `master`.
3. Seal all six ciphertexts against **this** cluster's key (two htpasswd seals in
   two namespaces, two Grafana admin keys, the web runtime config), commit to
   `master`, and confirm every Secret materializes:
   `gateway-basic-auth` in `phase2-data` and `monitoring`,
   `grafana-admin-credentials` in `monitoring`, `web-runtime-config` in the web
   namespace. Do not sync routes before this passes.
4. Sync `platform-observability`. Watch to `Synced/Healthy`. Fix failures by
   fixing the manifest on `master` and re-syncing.
5. Verify certificate issuance through phase 2's chosen strategy; confirm
   `Ready=True` and a clean `Order`/`Challenge` chain.
6. Bring up the workload plane in dependency order: data plane (Redis, Postgres,
   Feast) → model plane (agentgateway, llama.cpp servers, weights loader) → MCP
   services → agents → web. Confirm each pod `Running`, each `ServiceMonitor`
   target `UP`, and the agents' `/readyz` reporting dependencies ready.
7. Smoke all five routes from outside the cluster (no port-forward): 401 without
   credentials, 200 with. Confirm no backing service is reachable except through
   the gateway.
8. Drive the correlated scenario once as a **scripted** call through the gateway
   (coordinator `/v1/run`), including one deliberate failure so the failure
   counters are non-zero. Confirm Prometheus has the token, TTFT, PII-catch,
   agent-call and tool-call series; Loki has the request's lines; Jaeger has the
   trace. Note the trace ID.
9. Exercise the UI path once (sign in, agent-test chat, registry page) to confirm
   phase 3's auth plane works through the gateway.
10. Write a window log into this plan's `reports/`: what synced, what failed and
    why, what changed, the final health state, the trace ID and the scenario
    timestamps. It is input to the capture phase, not evidence itself.

## Success Criteria

- [ ] Operator -> lists Secrets -> `gateway-basic-auth` present in both `phase2-data` and `monitoring`, `grafana-admin-credentials` in `monitoring`, `web-runtime-config` in the web namespace, none containing a placeholder.
- [ ] Operator -> runs `argocd app get platform-observability` -> `Synced` and `Healthy`, tracking `master`.
- [ ] Operator -> checks the certificate -> `Ready=True` with a clean challenge chain.
- [ ] Operator -> curls the five routes from outside -> 401 unauthenticated, 200 authenticated, HTTPS chain valid.
- [ ] Operator -> checks Prometheus targets -> web, both MCP services, all three agents, and the model plane are `UP`.
- [ ] Operator -> runs the scripted coordinator scenario through the gateway -> non-zero token/TTFT/agent-call/tool-call/failure series, matching Loki lines, and a resolvable Jaeger trace ID.
- [ ] Operator -> signs in through the gateway -> the agent-test chat and the registry page both work against the live plane.
- [ ] Reviewer -> reads the window log -> no rubric row is claimed in it.

## Risk Assessment

- **A ciphertext sealed for the wrong namespace** → 503 on that route and a
  misleading "auth is broken" hunt. Mitigation: step 3 gates on all six Secrets
  materializing before any route sync.
- **Node pressure despite the budget** → observability pods `Pending`.
  Mitigation: phase 2's named disables and scale-to-zero list; the secondary-pool
  target; then the re-keyed cut ladder.
- **Certificate still fails** → all seven gateway rows die. This is the cut
  ladder's *abort* branch, not its Jaeger/Loki branch: without HTTPS there is
  nothing to capture at the edge. Decide within the first third of the window
  whether to fall back to an HTTP-only capture (and say so in the evidence) or
  end the window.
- **Jaeger memory storage** (`jaeger.yaml:17-24`, single replica, no PVC) loses
  the trace on any restart. Mitigation: the capture phase persists the trace JSON
  immediately; do not tear down or reschedule between step 8 and the capture.
- **Using `gcp-up` as a reset** → VM restarted, secondary pool back to zero,
  whole observability stack evicted while the command prints success. Mitigation:
  phase 2's targets; never `gcp-down`/`gcp-up` mid-window.
- Rollback: `argocd app rollback` or revert the `master` commit; the cluster
  returns to the pre-window state and the capture phase does not run.
