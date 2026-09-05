---
phase: 9
title: "Phase 9: API serving, KEDA, web, analytics, NGINX edge policy"
status: pending
priority: P1
effort: "10-14 days"
dependencies: ["phase-04-data-plane.md", "phase-05-cdc-streaming.md", "phase-06-platform.md", "phase-08-llm-agent-track.md"]
owns: ["src/analytics/", "apps/", "platform/analytic/", "platform/api-serving/", "platform/keda/", "platform/web/", "charts/"]
---

# Phase 9: API serving, KEDA, web, analytics, NGINX edge policy

## Overview

Deploy the API-serving and analytics layers; migrate Next.js in-cluster; restore KEDA
`ScaledObject`s; and implement the **NGINX edge policy** the rubric grades across nine rows but the
previous plan never owned: every observability and API service hidden behind the single ingress,
with basic auth, rate limiting, a domain and HTTPS. **Resident cost: 2-4 vCPU windowed.**

Rubric rows landing here:

| Rows | Requirement | Points |
|---|---|---|
| ML 2-3, 5-6; LLM 9-10, 15-16 | FastAPI + pydantic validation + healthcheck; async | 12 |
| ML 4, 7; LLM 11, 17 | Deploy to Kubernetes with Helm + `rollingupdate` + auto-fallback (`--atomic`) | 8 |
| ML 8-9 | Autoscale the data-fetch API and the drift API | 4 |
| ML 37-40; LLM 40-44 | Metric / log / trace / API / agent-UI / registry-UI services hidden behind NGINX | 18 |
| ML 41; LLM 45 | Basic authentication and rate limiting | 4 |
| ML 42; LLM 46 | Domain + HTTPS | 2 |
| ML 45; LLM 49 | Web API metrics (req/s, request count, failure count) | 3 |
| ML 33 | CI/CD for the inference engine — surface owned here, pipeline in P10 | 1 |

## Requirements

- Functional:
  - `prediction-api`, `feature-api`, `drift-api`, `feature-mcp`, `drift-mcp` all serve with FastAPI,
    pydantic validation, `/healthz` and `/readyz`, and async handlers.
  - Every service deploys by Helm with a `RollingUpdate` strategy and `helm upgrade --atomic`
    auto-fallback proven by a deliberately broken release.
  - KEDA scales `feature-api` and `drift-api` above minimum and back.
  - Superset queries Trino over Iceberg Gold; the dbt (or SQL CronJob) Gold Data Mart refreshes daily
    from Airflow and DataHub records the lineage edge.
  - In-cluster Next.js serves authenticated analyst sessions with Postgres RLS, no Supabase.
  - Exactly one external `LoadBalancer` (NGINX) fronts Grafana, the log viewer, Jaeger, the data-fetch
    API, the agent test UI and the agent registry UI — none is directly exposed.
  - Basic auth and a rate limit are enforced on the data-fetch API and the agent test UI.
  - A domain resolves over HTTPS with a cert-manager-issued certificate.
- Non-functional: Parquet Gold readers are removed only **after** the Iceberg Gold reader passes; the
  external Vercel deployment is retired only after AC-P9-9 passes.

## Architecture

```
                        Internet
                            │
                    ┌───────▼────────┐
                    │  NGINX Ingress │  ← the ONLY external LoadBalancer
                    │  TLS (cert-mgr)│    domain + HTTPS
                    │  basic auth    │    ML 41 / LLM 45
                    │  rate limit    │
                    └───────┬────────┘
     ┌──────────┬───────────┼───────────┬───────────┬──────────────┐
     ▼          ▼           ▼           ▼           ▼              ▼
  Grafana   log viewer   Jaeger    feature-api   agent test UI  registry UI
 (ClusterIP)(ClusterIP)(ClusterIP)              (Next.js)      (Next.js)

ns: api-serving   prediction-api ── feature-api ── drift-api ── feature-mcp ── drift-mcp
ns: keda          KEDA autoscales feature-api + drift-api
ns: analytic      Trino ── Superset ── dbt / SQL CronJob (Gold Data Mart)
ns: web           Next.js + Route Handlers ── Postgres RLS
```

**R-1 fallback (retained):** if the target image's "Build Gold Data Mart" component is not dbt, run
the same Airflow-daily CronJob issuing the same SQL against Trino without the dbt layer — strictly
less work, no scope increase.

## Related Code Files

- Restore from archive: `charts/feature-api/templates/scaledobject.yaml`,
  `charts/drift-api/templates/scaledobject.yaml`
- Create: `platform/analytic/trino.yaml`, `superset.yaml`, `dbt-cronjob.yaml`
- Create: `platform/api-serving/prediction-api.yaml`, `platform/keda/keda-operator.yaml`
- Create: `platform/web/nextjs-deployment.yaml`
- Create: `platform/ingress/basic-auth-secret.yaml`, `rate-limit-annotations.yaml`,
  `certificate.yaml`, `ingress-observability.yaml`, `ingress-agent-ui.yaml`
- Modify: `charts/*/templates/deployment.yaml` — explicit `RollingUpdate` with
  `maxSurge`/`maxUnavailable`
- Modify: `apps/feature-api/`, `apps/drift-api/`, `apps/feature-mcp/`, `apps/drift-mcp/` — pydantic
  models, async handlers, `/healthz`, `/readyz`, Prometheus request metrics
- Modify: `apps/web/` — remove every `@supabase/` import; Postgres RLS sessions; agent test UI;
  agent registry UI
- Modify: `src/analytics/` — bind to the live Trino client; add `trino` to `pyproject.toml`
- Create: `dags/gold_data_mart.py`

## Implementation Steps

1. **API hardening** (2 d) — pydantic request/response models, async handlers, `/healthz` and
   `/readyz`, and a Prometheus middleware exporting `req/s`, request count and failure count on all
   five services.
2. **Helm rollout semantics** (1 d) — explicit `RollingUpdate` in every chart; prove
   `helm upgrade --atomic` rolls back by shipping a deliberately broken image tag and confirming the
   previous ReplicaSet is restored.
3. **Deploy `platform-api-serving`** (2 d) — all five services.
4. **KEDA** (1 d) — restore both `ScaledObject`s; verify the metric source matches the current
   deployment; drive load and observe scale up and back.
5. **NGINX edge policy** (2 d) — convert Grafana, the log viewer and Jaeger to `ClusterIP` and route
   them through NGINX; add basic-auth and rate-limit annotations on the data-fetch API and the agent
   test UI; issue the certificate through cert-manager and bind the domain. Re-verify exactly one
   external `LoadBalancer`.
6. **`platform-analytic`** (2-3 d) — Trino with Iceberg + MinIO catalogs, Superset, dbt CronJob;
   verify a Superset dashboard query returns Gold Data Mart rows from Iceberg with no direct
   object-store credential in the browser path.
7. **Gold Data Mart DAG** (1 d) — Airflow daily trigger → mart rebuild → DataHub lineage edge from
   Silver/Gold to the mart.
8. **In-cluster Next.js** (2-3 d) — Postgres RLS sessions, no Supabase; agent test UI and agent
   registry UI as routes; authentication on the agent test UI.
9. **End-to-end prediction** (1 d) — `prediction-api` receives `company_id`, fetches online features
   from Feast/Redis through `feature-api`, returns a scored prediction.
10. **Cutover** (1 d) — after AC-P9-9 passes, retire the external Vercel deployment and remove the
    Parquet Gold readers.

## Success Criteria

- [ ] AC-P9-1 **(ML 2-3, 5-6; LLM 9-10, 15-16)**: Client → posts an invalid body to each of the five
      services → receives a pydantic 422 with field detail; `/healthz` and `/readyz` return 200; every
      handler is async
- [ ] AC-P9-2 **(ML 4, 7; LLM 11, 17)**: Operator → runs `helm upgrade --atomic` with a broken image
      → the release rolls back automatically and the previous ReplicaSet serves traffic; the chart
      declares `RollingUpdate`
- [ ] AC-P9-3 **(ML 8-9)**: KEDA → observes load on `feature-api` and on `drift-api` → scales each
      Deployment above minimum and back, using the restored `ScaledObject`s
- [ ] AC-P9-4 **(ML 37-40; LLM 40-44)**: Operator → lists Services → Grafana, the log viewer, Jaeger,
      `feature-api`, the agent test UI and the agent registry UI are all `ClusterIP` and reachable
      **only** through NGINX; `kubectl get svc -A --field-selector spec.type=LoadBalancer` returns
      exactly one row
- [ ] AC-P9-5 **(ML 41; LLM 45)**: Anonymous client → requests the data-fetch API and the agent test
      UI → receives 401; with credentials → 200; exceeding the configured rate → 429
- [ ] AC-P9-6 **(ML 42; LLM 46)**: Browser → opens the configured domain over HTTPS → a valid
      cert-manager certificate is served; plain HTTP redirects to HTTPS
- [ ] AC-P9-7 **(ML 45; LLM 49)**: Prometheus → scrapes each Web API → `req/s`, total requests and
      total failures are present with correct labels
- [ ] AC-P9-8 **(ML 51 surface; LLM 43-44)**: Analyst → opens the Superset dashboard through NGINX →
      sees current-quarter distress metrics with no direct object-store credential
- [ ] AC-P9-9: In-cluster Next.js → serves an authenticated analyst session → Postgres RLS is
      enforced; zero `@supabase/` imports remain; only then is the Vercel deployment retired
- [ ] AC-P9-10: Airflow daily DAG → triggers the Gold Data Mart build → mart tables refresh and
      DataHub records the lineage edge from Silver/Gold to the mart
- [ ] AC-P9-11: `prediction-api` → receives `company_id` → fetches online features from Feast/Redis
      through `feature-api` → returns a scored prediction
- [ ] AC-P9-12: Engineer → greps `src/` for Parquet Gold readers → zero remain, and the Iceberg Gold
      reader passed first

## Risk Assessment

**Risk (R-1):** the Gold Data Mart component is dbt only by logo inference. Signal: the dbt CLI
cannot connect to Trino, or the schema is incompatible. Response: the recorded fallback — an Airflow
CronJob issuing the same SQL against Trino. Strictly less work; scope does not increase.

**Risk:** Supabase Auth dependencies are not fully removed. Signal: sessions fail without a Supabase
URL. Mitigation: audit every `@supabase/` import before deploying. Response: keep Vercel live until
all Supabase calls are gone — AC-P9-9 gates the retirement.

**Risk:** a KEDA `ScaledObject` targets the wrong metric source after restore. Signal: no scaling
under load. Mitigation: verify the source (`kafka-topic` or `prometheus`) matches the current
deployment before load-testing. Response: update the metric source in the `ScaledObject`.

**Risk:** converting Grafana / Jaeger to `ClusterIP` breaks an existing evidence path that used a
direct URL. Signal: a P12 capture row cannot reach the dashboard. Mitigation: update the matrix rows
in the same commit as the conversion. Response: capture through the NGINX path — which is what the
rubric grades.

**Risk:** basic auth breaks the agent-to-API call path inside the mesh. Signal: agents receive 401
after AC-P9-5. Mitigation: apply auth at the **ingress**, not at the Service; in-mesh traffic does
not traverse NGINX. Response: scope the auth annotation to the external Ingress resource only.

**Risk:** the domain and certificate depend on DNS the project does not control. Signal: an ACME
challenge fails. Mitigation: verify DNS delegation before requesting the certificate; the retained
static IP is already allocated. Response: use a DNS-01 challenge, or record the gap and serve a
self-signed certificate with the limitation documented — do not claim a valid chain that does not exist.

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
