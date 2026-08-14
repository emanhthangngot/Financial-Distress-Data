---
phase: 11
title: "Argo Rollouts, autoscale and observability"
status: cancelled
priority: P1
effort: "2.5d"
dependencies: [5, 10]
---

> **CANCELLED 2026-08-14 (user decision, ML track dropped).** Zero LLM rubric rows reference Argo Rollouts or KEDA (measured 2026-08-14). LLM's own Observability rows (6/6) are already `executed`. Closed only ML rows (~28 pts).
> Body below is kept as the historical record of what was planned/built; nothing further is executed against it. See `plan.md` Overview.

# Phase 11: Argo Rollouts, autoscale and observability

## Overview

Progressive delivery with metric-driven automatic rollback, autoscaling for the
two Web APIs, and the observability expansion that covers metrics, logs, traces
and Web API instrumentation. Largest points-per-day phase in the plan.

## Requirements

- Functional: a regressed candidate is automatically rolled back on Prometheus
  analysis without human action; both Web APIs autoscale on load; metrics, logs
  and traces are visible through gateway-exposed viewers.
- Non-functional: rollback completes within the analysis interval budget; the
  rollout surge fits inside the phase 4 capacity headroom.

## Architecture

**Argo Rollouts over scripted promotion.** The reference repo implements
shadow -> 10% -> 25% -> 50% -> promote/rollback as several hundred lines of
Jenkins Groovy. Argo Rollouts expresses the same as a `Rollout` CRD with an
`AnalysisTemplate` querying Prometheus, and — decisively — it is pull-based and
reconciled by the same Argo CD already running here. A push-based CI job holding
cluster credentials is the weaker production posture.

Rollout strategy per workload:

| Workload | Strategy | Analysis metric | Rollback trigger |
|---|---|---|---|
| feature-api | canary 10/25/50 | p95 latency, 5xx rate | either breaches threshold |
| drift-api | canary 10/25/50 | p95 latency, 5xx rate | either breaches threshold |
| model serving | blue-green with pre-promotion analysis | prediction error rate, latency | analysis fails |
| web | canary 25/50 | 5xx rate | breach |

**Autoscale.** KEDA is already installed (`platform/agents/keda-scaledobject.yaml`).
This phase extends it to the two Web APIs, scaling the data-retrieval API on HTTP
request rate and the drift API on queue depth — the rubric asks specifically for
KEDA-style event-driven scaling rather than plain CPU HPA.

**Observability.** The current stack — OpenTelemetry Collector, Prometheus, Loki,
Jaeger, Grafana — is already the 2026 default shape, confirmed by research. No
tool changes. What is missing is coverage: Web API instrumentation, model rollout
metrics, pipeline and drift metrics, and gateway-exposed viewer routes for logs
and traces (the rubric asks for a log viewer and a trace viewer behind the
gateway, which Grafana and Jaeger satisfy under the "hoặc tool tương tự" clause).

## Related Code Files

GitOps repo:

- Create: `platform/delivery/argo-rollouts-values.yaml`
- Create: `platform/delivery/analysis-templates.yaml`
- Create: `argocd/applications/platform-delivery.yaml`
- Modify: `charts/fastapi-service/templates/` — `Rollout` variant of the Deployment
- Modify: `charts/feature-api/`, `charts/drift-api/` — enable rollout + KEDA
- Create: `charts/*/templates/scaledobject.yaml` (declared in the matrix, absent on disk)
- Modify: `platform/ingress/routes-viewers.yaml` — Grafana and Jaeger routes
- Modify: `platform/observability/dashboards.yaml` — rollout, drift, Web API dashboards
- Create: `platform/ml/ab-testing.yaml` (matrix-declared path, corrected in phase 1)

Source repo:

- Modify: `apps/feature-api/app/main.py`, `apps/drift-api/app/main.py` — OTel + Prometheus instrumentation
- Create: `scripts/capture_rollout_evidence.py`
- Create: `tests/load/test_web_api_load.py` (Locust, already a dependency)

## Implementation Steps

1. Install Argo Rollouts via Argo CD; add a `Rollout` template variant to the
   shared `fastapi-service` chart so all services inherit it from one place.
2. Write `AnalysisTemplate` objects querying Prometheus for p95 latency and 5xx
   rate, with explicit thresholds and failure limits.
3. Instrument both Web APIs with OpenTelemetry traces and Prometheus metrics so
   the analysis has real signal to read. Without this the analysis is decorative.
4. Convert feature-api and drift-api to `Rollout`, deploy a healthy candidate, and
   watch a successful progressive promotion.
5. **Deploy a deliberately regressed candidate** — inject latency or errors — and
   capture the automatic rollback: rollout status, analysis run, controller log,
   Grafana screenshot. Negative-path evidence is the acceptance signal.
6. Add A/B routing config and its monitoring dashboard for the two-version
   comparison the rubric asks for, including the no-ground-truth-yet assumption
   the rubric states.
7. Add KEDA `ScaledObject`s for both APIs; drive load with the Locust suite and
   capture scale-out and scale-in.
8. Expose Grafana and Jaeger through the gateway with authentication and rate
   limiting, satisfying the routing rows.
9. Build the dashboards: rollout status, drift metrics, Web API RED metrics,
   pipeline health.

## Verification

```bash
kubectl argo rollouts get rollout feature-api --watch
kubectl get analysisrun -A
.venv/bin/python scripts/capture_rollout_evidence.py
.venv/bin/python -m pytest tests/load -k web_api_load
kubectl get scaledobject -A
```

## Success Criteria

- [ ] Argo Rollouts -> healthy candidate deployed -> progresses through canary steps and promotes
- [ ] Argo Rollouts -> regressed candidate deployed -> analysis fails and auto-rollback completes with no human action, fully captured
- [ ] KEDA -> Locust load applied -> both APIs scale out, then scale in after load stops
- [ ] Gateway -> unauthenticated request to Grafana or Jaeger -> rejected; authenticated -> served; rate limit enforced
- [ ] Grafana -> A/B dashboard -> shows both model versions side by side
- [ ] Strict `--track LLM` gate -> unchanged PASS 100/100

## ML rubric rows closed

- A/B Testing x2 — monitoring dashboard for two versions, and no-direct-replace
  deployment (2)
- Web API rolling update with auto fallback, both services (4)
- Autoscale x2 — KEDA for the data API and the drift API (4)
- Observability x5 — metrics, logs, traces, Web API metrics, drift pipeline (9)
- Routing & Gateway x6 — services behind the gateway, auth and rate limit, log
  viewer, trace viewer, both Web APIs (11)

Approximately 28 points — the highest-density phase in the plan.

## Risk Assessment

- **A canary temporarily doubles a workload's footprint.** The phase 4 capacity
  plan reserves headroom for exactly this; verify before the first rollout rather
  than discovering it as a scheduling failure mid-demo.
- **The regressed-candidate demo must not be run against a service holding
  captured evidence.** Use a dedicated demo workload or a scratch namespace.
- **Analysis thresholds that are too tight cause false rollbacks** and too loose
  never fire. Calibrate against the Locust baseline from step 7 before claiming
  the evidence.
