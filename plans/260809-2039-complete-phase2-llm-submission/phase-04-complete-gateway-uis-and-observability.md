---
phase: 4
title: "Complete gateway, UIs and observability"
status: pending
priority: P1
effort: "1.5d"
dependencies: [3]
---

# Phase 4: Complete gateway, UIs and observability

## Overview

Make everything from phases 2-3 reachable and observable through the F5 NGINX
edge: two product UI routes, three viewer routes, authentication plus a rate
limit, and the full metrics/logs/traces set.

Rubric rows owned (21 points) — IDs and paths copied verbatim from the CSV:

| Points | rubric_id | artifact_path (authority) |
|---:|---|---|
| 2 | `LLM-routing-gateway-c-c-service-c-n-c-hide-ng-sau-` | gitops `platform/ingress/f5-nginx-values.yaml` |
| 1 | `LLM-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-` | gitops `platform/ingress/f5-nginx-values.yaml` |
| 2 | `LLM-routing-gateway-ui-test-agent` | gitops `platform/ingress/f5-nginx-values.yaml` |
| 2 | `LLM-routing-gateway-ui-cho-agent-registry` | gitops `platform/ingress/f5-nginx-values.yaml` |
| 2 | `LLM-routing-gateway-authentication-cho-ui-test-age` | gitops `platform/ingress/f5-nginx-values.yaml` |
| 2 | `LLM-routing-gateway-service-coi-log` | gitops `platform/ingress/f5-nginx-values.yaml` |
| 2 | `LLM-routing-gateway-service-coi-trace` | gitops `platform/ingress/f5-nginx-values.yaml` |
| 1 | `LLM-observability-collect-v-visualize-metrics-v-` | gitops `platform/observability/prometheus-values.yaml` — placeholder today |
| 2 | `LLM-observability-m-b-o-t-nh-t-c-c-metrics` | gitops `platform/observability/prometheus-values.yaml` |
| 2 | `LLM-observability-agent-tool-call-metrics` | gitops `platform/observability/prometheus-values.yaml` |
| 1 | `LLM-observability-web-api-metrics` | gitops `platform/observability/prometheus-values.yaml` |
| 1 | `LLM-observability-t-ng-t-cho-logs` | gitops `platform/observability/loki-otel-values.yaml` — placeholder today |
| 1 | `LLM-observability-t-ng-t-cho-traces` | gitops `platform/observability/loki-otel-values.yaml` |

Seven rows resolve to `f5-nginx-values.yaml` and four to
`prometheus-values.yaml`; a single mistake in either costs 13 or 6 points.

## Requirements

- Functional: Prometheus + Grafana, Loki and Jaeger deployed through the Argo
  Application phase 1 created for `platform/observability`, each exposed as its
  own gateway-reachable route; the agent chat and agent registry routes in
  `apps/web` **containerized and deployed** behind basic auth and an NGINX rate
  limit; a DuckDNS subdomain with a cert-manager ACME certificate serving the
  Web API kéo dữ liệu over HTTPS.
- Non-functional: installation without a reachable route scores nothing — the
  viewer rows pay for the *service being reachable*.

## Architecture

**`apps/web` already contains both scored routes.** `src/app/agents/registry/`
is a working agent-registry page and `src/components/assistant/*` +
`src/app/api/assistant/` is the chat surface — both Supabase/fixture-backed
through `getDataPort()`. The work here is **not** "build two routes"; it is:

1. repoint those two routes at the live cluster (the phase-3 registry and the
   coordinator agent) instead of fixture provenance,
2. **containerize and deploy `apps/web`** — it has no Dockerfile, no
   `output: "standalone"`, and nothing in the GitOps repo ships it, yet the
   scored rows require the UI answering *through the gateway*,
3. capture `UI-APPROVED-02` and `UI-APPROVED-03` at three viewports.

Do not build a second registry page beside the existing one; two registries
disagreeing in front of a reviewer is worse than one.

**Edge.** F5 NGINX Ingress OSS is installed with LB IP `34.21.242.110`. Register
a free DuckDNS subdomain, let cert-manager solve ACME HTTP-01. Backends stay
`ClusterIP` behind the default-deny NetworkPolicy — **whose enforcement phase 1
turned on**; before that the hide-services proof was inert. The row is proven by
a negative curl straight to a backend plus a successful curl through the route.

**Auth on every route, not just the scored one.** The scored row names the chat
UI, but exposing Grafana, Loki and Jaeger unauthenticated on a public DuckDNS
host publishes prompts, retrieved RAG chunks and tool arguments to anyone who
scans it. Apply the same sealed-secret-backed basic auth (the controller phase 1
installed) to all five routes; capture the 429 under burst on the chat route,
since row text names auth **and** rate limit. Set Grafana admin credentials from
a sealed secret and disable anonymous access explicitly.

**Observability.** Prometheus + Grafana for metrics, Loki via Grafana Explore
for logs, Jaeger for traces. The required metric set is the **literal row text**,
which is longer than the earlier draft admitted:

> token metrics (input, output, total per request); total round-trip time for a
> generation; **TTFT**; **frequencies of prompts caught by safety of PII**

plus per-agent call counts, per-MCP-tool call counts, failure counts per
invocation, and Web API RED metrics. TTFT and the PII-safety counter are scored
and were missing from the first draft — emit both.

Metrics carry a `service` label and Grafana dashboards use template variables
(retrofit decision 7). Logs are redacted (prompts, documents, PII) with release
and session fields. **Span attributes are redacted too** — traces span
gateway → API → MCP → agent → model, so an unredacted span is the copy that
leaks what the log redaction removed.

## Related Code Files

- Create (GitOps): `platform/observability/jaeger.yaml`,
  `platform/observability/grafana-dashboards/`,
  `platform/ingress/duckdns-certificate.yaml`,
  `platform/ingress/routes-viewers.yaml`, `platform/ingress/routes-ui.yaml`,
  `platform/ingress/basic-auth-sealed-secret.yaml`,
  `apps/dev/web/` (ApplicationSet input for the product UI)
- Modify (GitOps): `platform/observability/prometheus-values.yaml`,
  `platform/observability/loki-otel-values.yaml` — **placeholders today**;
  `platform/ingress/f5-nginx-values.yaml`;
  `platform/security/letsencrypt-clusterissuer.yaml`
- Create: `apps/web/Dockerfile`; modify `apps/web/next.config.ts`
  (`output: "standalone"`)
- Modify: `apps/web/src/app/agents/registry/page.tsx` and the assistant data
  port — live cluster source instead of fixture provenance
- Modify: `apps/feature-mcp/app/main.py`, `apps/drift-mcp/app/main.py`,
  `src/agents/*.py` — emit TTFT, token, PII-safety, per-agent and per-tool
  metrics and OTel spans with redacted attributes
- Create: 13 evidence files under `docs/phase2/evidence/llm/`
- Regenerate (never hand-edit): `tests/phase2/requirements/test_llm_ac_13_routing.py`,
  `test_llm_ac_15_observability.py`

## Implementation Steps

1. Register the DuckDNS subdomain against `34.21.242.110`; commit the
   `Certificate`; confirm cert-manager issues it; capture the TLS chain.
2. Route the Web API kéo dữ liệu through the gateway on that hostname over
   HTTPS. Capture the certificate and a successful HTTPS call.
3. Capture the hide-services proof: direct call to a backend Service from
   outside → refused; the same path through the ingress → 200. This is only
   meaningful because NetworkPolicy enforcement is on.
4. Deploy Prometheus, Grafana, Loki and Jaeger through the Argo Application from
   phase 1. Expose three separate gateway routes and prove each answers.
5. Instrument the services and agents with the full literal metric set above,
   including TTFT and the PII-safety counter. Add the `service` label; build
   Grafana dashboards on template variables.
6. Propagate OTel context across gateway → API → MCP → agent → model **with span
   attributes redacted**, then prove one correlation ID resolves to a metric, a
   redacted log line and a redacted trace.
7. Containerize `apps/web`, ship it through the ApplicationSet, and repoint the
   two existing routes at live cluster data. Capture `UI-APPROVED-02` and
   `UI-APPROVED-03` at desktop, tablet and mobile per the phase-08 evidence
   rules. Keep the existing Playwright configs green.
8. Apply sealed-secret basic auth to all five gateway routes plus the rate limit
   on the chat route; capture the auth challenge and a 429 under burst.
9. Write the 13 evidence files, flip these 13 rows to `executed`, regenerate the
   CSV and requirement tests, re-run the audit. `make gcp-down`; record the delta.

## Success Criteria

- [ ] Reviewer -> calls a backend Service directly from outside the cluster -> is refused by an enforced NetworkPolicy; calls the same route through the ingress -> receives 200 over valid HTTPS on the DuckDNS hostname.
- [ ] Platform observer -> opens Grafana -> finds input/output/total tokens, round-trip time, **TTFT**, **PII-safety catch frequency**, per-agent and per-MCP-tool call counts, failure counts and Web API metrics, all filterable by the `service` template variable.
- [ ] Reviewer -> opens the log viewer and trace viewer routes through the gateway -> both answer, both challenge for authentication, and neither exposes an unredacted prompt or document.
- [ ] Reviewer -> follows one correlation ID -> finds a metric, a redacted log line and a redacted trace across the full request path.
- [ ] Analyst -> opens the deployed agent chat UI on the DuckDNS host -> is challenged for authentication, sees a 429 under burst, then sees citations and agent/tool status from the live coordinator.
- [ ] Registry viewer -> opens the registry route -> sees the phase-3 cluster registry, not fixture data, and there is exactly one registry page in the app.

## Risk Assessment

- **Viewer routes installed but unreachable** is the classic way to lose 6
  points. Mitigation: every viewer row's evidence is an HTTP response through
  the gateway, captured at write time.
- **Containerizing `apps/web` is unbudgeted work in the original draft** —
  Dockerfile, standalone output, Supabase env as sealed secrets, chart,
  ApplicationSet entry, ingress route. It is why this phase is 1.5 days.
- **Two auth layers.** NGINX basic auth in front of the app's own Supabase
  session auth can produce a confusing double challenge. Mitigation: scope basic
  auth to the gateway route and keep `resolveSession()` untouched; capture both
  behaviors in the evidence rather than hiding one.
- **Observability may not co-schedule with the model server** on one node.
  Mitigation: the phase-1 capacity budget governs; capture in a dedicated window
  with the model scaled down and state that in the evidence.
- **Over-instrumentation consumes the small cluster.** Mitigation: bounded
  retention, sampling, resource quotas, evidence-window profiles.
