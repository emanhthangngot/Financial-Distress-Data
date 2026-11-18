---
phase: 9
title: "Phase 9: API serving, KEDA, web, analytics, NGINX edge policy"
status: pending
priority: P1
effort: "10-14 days"
dependencies: ["phase-04-data-plane.md", "phase-05-cdc-streaming.md", "phase-06-platform.md", "phase-08-llm-agent-track.md"]
owns: ["src/analytics/", "apps/", "platform/analytic/", "platform/api-serving/", "platform/keda/", "platform/web/", "charts/"]
---

# Phase 9: API, analyst UI and protected session demo

## Overview

Serve real API/MCP and analyst paths behind NGINX with authentication, rate limits and trusted
domain/HTTPS. Preserve working auth and external API contracts; no forced Supabase/Vercel rewrite.
No public URL 24/7 is required. Cloud Terraform remains P6 evidence, not implied by an HTTPS URL.

## Requirements and architecture

Browser -> protected NGINX -> existing web/API -> LangGraph coordinator -> scoped MCP tools ->
feature/drift services -> Feast/model and cutoff-filtered pgvector. Dashboards, logs, traces and
registry UI are reachable through protected NGINX, not exposed by independent public Services.
NGINX is the sole public application entry; a paid managed LoadBalancer is not intrinsically
required. P0 must verify the actual no-spend ingress/domain route before use.

FastAPI/pydantic input validation, async handlers, health/readiness, request/error metrics,
Helm RollingUpdate and actual automatic rollback remain required. Kubernetes multi-replica and
API autoscaling must be exercised; short free-quota load windows suffice but mocked replica counts
and static YAML do not. Retain KEDA if the existing pattern works; do not add a second autoscaler.

Request contract carries ticker, cutoff_ts, question and server-controlled request/session identity.
P8 records provider/model/prompt/corpus revisions; clients cannot choose arbitrary paid endpoints.
Responses preserve external schemas and streaming event semantics; citations/vintage/missing-data
metadata are versioned deliberately if the current API cannot carry them. Authentication derives
principal server-side; session_id is not authorization. P5 defines feature retrieval identity; do
not reintroduce company_id/company_key as a competing canonical key.

Current product auth stays unless a concrete accepted requirement demands migration. Analyst UI
supports loading, completed, no eligible evidence, stale/missing features, auth expiry, rate-limit,
provider unavailable and interrupted stream. A partial answer is visibly partial; retry is a new
request, not silent appended text from another provider. Session reset/expiry clears agent state.

Analytics: expose financial/feature provenance and current/as-of views through existing UI/query
surfaces. Trino/Superset/dbt are not mandatory new services for image fidelity; choose existing SQL
or scheduled SQL refresh where sufficient, preserving any actual owned rubric output.

## Ownership

Own apps/API/MCP handlers, web routes, charts and NGINX ingress. P8 owns agent state/inference;
P5 owns feature contract; P6 owns mesh/Vault; P12 owns telemetry implementation. Required interfaces
are agreed before editing shared response models and chart namespace fields.

## Implementation steps

1. Inventory current external schemas/auth/session flows and preserve them in the P8 parity fixture.
2. Harden input/async/health/readiness/metrics; distinguish alive from ready when dependencies fail.
3. Deploy real Helm releases; induce a failed revision and observe rollback and continued service.
4. Exercise feature/drift API autoscaling up and down under bounded load; capture actual metrics.
5. Configure NGINX routes, basic auth where graded, rate limits and trusted TLS; verify no bypass
   via public Service or unprotected UI route. Internal mesh auth is separate, not disabled.
6. Bind ticker/cutoff queries to eligible Feast/pgvector data; latest dashboard view cannot be used
   for historical answers. Present provenance and unavailable states, not generated missing values.
7. Integrate session-only LangGraph UI behavior and stream interruption handling; verify two
   simultaneous principals cannot observe each other's state/citations.
8. Exercise real domain/HTTPS, API/MCP, prediction and analyst flows in the authorized demo window.
   Stop session services after exporting evidence; publish access instructions without 24/7 claims.

## Success criteria

- [ ] AC-P9-1: Client -> submits invalid bodies and checks liveness/readiness -> precise 422 errors; live process distinguished from dependency-ready service; async request path exercised.
- [ ] AC-P9-2: Operator -> deploys broken Helm revision with automatic fallback -> prior healthy version serves traffic after rollback; RollingUpdate configured.
- [ ] AC-P9-3: Load client -> drives feature/drift API demand -> actual replica increase then scale-down observed with stable request/error metrics.
- [ ] AC-P9-4: External client -> accesses API, dashboards, logs, traces, agent and registry UIs -> only intended NGINX routes work; direct public bypass fails.
- [ ] AC-P9-5: Anonymous/authorized/over-limit client -> exercises graded API/UI routes -> 401/200/429 respectively; credentials never appear in logs.
- [ ] AC-P9-6: Browser -> opens controlled Web API domain -> valid trusted certificate, HTTP redirects and protected endpoints; no self-signed/local-only substitute for unverified rubric expectations.
- [ ] AC-P9-7: Prometheus -> scrapes actual Web API traffic -> request rate/count/failures distinguish successful and failed requests.
- [ ] AC-P9-8: Analyst -> inspects risk data -> current/as-of values with source/vintage provenance and no browser object-store credential.
- [ ] AC-P9-9: Two authenticated analysts -> run and reset independent sessions -> existing auth preserved, cross-session state denied and expiry/reset clears memory.
- [ ] AC-P9-10: Scheduled data refresh -> updates selected analytical view -> as-of history retained and lineage shows real upstream dependencies.
- [ ] AC-P9-11: Prediction API -> receives ticker and applicable feature cutoff -> retrieves P5-approved feature snapshot and returns versioned model score; missing/stale features are explicit.
- [ ] AC-P9-12: Engineer -> cuts over active Gold readers -> Iceberg path passes first, all active consumers migrated and obsolete readers removed without deleting Bronze evidence.
- [ ] AC-P9-STREAM: Analyst -> observes provider failure before/after first streamed content -> clear unavailable/interrupted state; no mixed-provider continuation or uncited fabricated result.

## Risks

Unavailable DNS/free ingress blocks the domain AC; document it rather than claiming localhost is
cloud. Free-tier provider congestion can fail the demo: rehearse an honest unavailable response.
NGINX ingress auth does not replace service-mesh authorization, and a session key never replaces
principal authorization. API contract changes require explicit versioning and full caller cutover.

## Rubric Citations (phase-03 R-12 closure, appended 2026-09-05)

Every rubric row this phase owns per `docs/rubric-matrix-unified.csv`'s `owning_phase` column, cited so `scripts/verify_rubric_coverage.py` can resolve ownership to an assertion (R-12). Each line names the row's real `rubric_id`, its stated requirement, and its proof artifact/deliverable — the row's own matrix columns, not invented text. Rows whose capability is not yet implemented are forward specs, matching this file's other `AC-P9-*` entries.

- AC-P9-RUBRIC-1: `LLM-routing-gateway-authentication-cho-ui-test-age` — platform_operator -> delivers "Setup authentication cho UI test agent ở trên" -> Capture màn hình thể hiện từng setup đã thành công (evidence: `docs/platform/evidence/llm/LLM-routing-gateway-authentication-cho-ui-test-age.md`)
- AC-P9-RUBRIC-2: `LLM-routing-gateway-c-c-service-c-n-c-hide-ng-sau-` — platform_operator -> delivers "Routing & Gateway (NGINX Ingress Controller) — Các service cần được hide đằng sau gateway" -> Capture màn hình thể hiện từng setup đã thành công (evidence: `docs/platform/evidence/llm/LLM-routing-gateway-c-c-service-c-n-c-hide-ng-sau-.md`)
- AC-P9-RUBRIC-3: `LLM-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-` — platform_operator -> delivers "Làm cái này cho Web API kéo dữ liệu. Mọi người có thể tham khảo 2 đồ án sau: cái này và cái này" -> Capture màn hình thể hiện từng setup đã thành công (evidence: `docs/platform/evidence/llm/LLM-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-.md`)
- AC-P9-RUBRIC-4: `LLM-routing-gateway-service-coi-log` — platform_operator -> delivers "Service để coi log (ví dụ Kibana)" -> Capture màn hình thể hiện từng setup đã thành công (evidence: `docs/platform/evidence/llm/LLM-routing-gateway-service-coi-log.md`)
- AC-P9-RUBRIC-5: `LLM-routing-gateway-service-coi-trace` — platform_operator -> delivers "Service để coi trace (ví dụ Jaeger)" -> Capture màn hình thể hiện từng setup đã thành công (evidence: `docs/platform/evidence/llm/LLM-routing-gateway-service-coi-trace.md`)
- AC-P9-RUBRIC-6: `LLM-routing-gateway-ui-test-agent` — platform_operator -> delivers "UI để test agent (xem tại đây)" -> Capture màn hình thể hiện từng setup đã thành công (evidence: `docs/platform/evidence/llm/LLM-routing-gateway-ui-test-agent.md`)
- AC-P9-RUBRIC-7: `LLM-security-centralize-secret-management` — platform_operator -> delivers "Security — Centralize secret management" -> Capture màn hình thể hiện cách mọi người thực hiện centrailize secret management (evidence: `docs/platform/evidence/llm/LLM-security-centralize-secret-management.md`)
- AC-P9-RUBRIC-8: `LLM-web-api-cho-real-time-dri-in-the-form-of-mcp-tool-to-k8s` — platform_operator -> delivers "Deploy in the form of MCP tool to k8s with helm + rollingupdate + auto fallback (see here); Remember, your MCP tool is not like normal API d..." -> Demonstrate Agent có trên registry, được deploy với multi-replica, giới hạn quyền thông qua Sandbox và màn hình UI chat với Agent (evidence: `docs/platform/evidence/llm/LLM-web-api-cho-real-time-dri-in-the-form-of-mcp-tool-to-k8s.md`)
- AC-P9-RUBRIC-9: `LLM-web-api-k-o-d-li-u-user-in-the-form-of-mcp-tool-to-k8s` — platform_operator -> delivers "Deploy in the form of MCP tool to k8s with helm + rollingupdate + auto fallback (see here); Remember, your MCP tool is not like normal API d..." -> Demonstrate Agent có trên registry, được deploy với multi-replica, giới hạn quyền thông qua Sandbox và màn hình UI chat với Agent (evidence: `docs/platform/evidence/llm/LLM-web-api-k-o-d-li-u-user-in-the-form-of-mcp-tool-to-k8s.md`)
- AC-P9-RUBRIC-10: `ML-routing-gateway-authentication-rate-limit-cho-` — platform_operator -> delivers "Setup authentication & rate limit cho Web API kéo dữ liệu" -> Capture màn hình thể hiện từng setup đã thành công (evidence: `docs/platform/evidence/ml/ML-routing-gateway-authentication-rate-limit-cho-.md`)
- AC-P9-RUBRIC-11: `ML-routing-gateway-c-c-service-c-n-c-hide-ng-sau-` — platform_operator -> delivers "Routing & Gateway (NGINX Ingress Controller) — Các service cần được hide đằng sau gateway" -> Capture màn hình thể hiện từng setup đã thành công (evidence: `docs/platform/evidence/ml/ML-routing-gateway-c-c-service-c-n-c-hide-ng-sau-.md`)
- AC-P9-RUBRIC-12: `ML-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-` — platform_operator -> delivers "Làm cái này cho Web API kéo dữ liệu. Mọi người có thể tham khảo 2 đồ án sau: cái này và cái này" -> Capture màn hình thể hiện từng setup đã thành công (evidence: `docs/platform/evidence/ml/ML-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-.md`)
- AC-P9-RUBRIC-13: `ML-routing-gateway-service-coi-log` — platform_operator -> delivers "Service để coi log (ví dụ Kibana)" -> Capture màn hình thể hiện từng setup đã thành công (evidence: `docs/platform/evidence/ml/ML-routing-gateway-service-coi-log.md`)
- AC-P9-RUBRIC-14: `ML-routing-gateway-service-coi-trace` — platform_operator -> delivers "Service để coi trace (ví dụ Jaeger)" -> Capture màn hình thể hiện từng setup đã thành công (evidence: `docs/platform/evidence/ml/ML-routing-gateway-service-coi-trace.md`)
- AC-P9-RUBRIC-15: `ML-routing-gateway-web-api-k-o-d-li-u` — platform_operator -> delivers "Web API kéo dữ liệu" -> Capture màn hình thể hiện từng setup đã thành công (evidence: `docs/platform/evidence/ml/ML-routing-gateway-web-api-k-o-d-li-u.md`)
- AC-P9-RUBRIC-16: `ML-security-centralize-secret-management` — platform_operator -> delivers "Security — Centralize secret management" -> Capture màn hình thể hiện cách mọi người thực hiện centrailize secret management (evidence: `docs/platform/evidence/ml/ML-security-centralize-secret-management.md`)
- AC-P9-RUBRIC-17: `ML-security-using-service-mesh-to-authoriz` — platform_operator -> delivers "Using service mesh to authorize access from service to service" -> Capture màn hình thể hiện cách mọi người thực hiện authorize service-to-service (evidence: `docs/platform/evidence/ml/ML-security-using-service-mesh-to-authoriz.md`)
- AC-P9-RUBRIC-18: `ML-web-api-cho-real-time-dri-to-k8s-with-helm-rollingupdate` — platform_operator -> delivers "Deploy to k8s with helm + rollingupdate + auto fallback (see --atomic)" -> Capture màn hình cách mọi người handle rolling update và fall back (evidence: `docs/platform/evidence/ml/ML-web-api-cho-real-time-dri-to-k8s-with-helm-rollingupdate.md`)
- AC-P9-RUBRIC-19: `ML-web-api-k-o-d-li-u-to-k8s-with-helm-rollingupdate` — platform_operator -> delivers "Deploy to k8s with helm + rollingupdate + auto fallback (see --atomic)" -> Capture màn hình cách mọi người handle rolling update và fall back (evidence: `docs/platform/evidence/ml/ML-web-api-k-o-d-li-u-to-k8s-with-helm-rollingupdate.md`)
