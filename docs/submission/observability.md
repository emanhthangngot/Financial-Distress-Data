# Observability

Row: `LLM-AC-15-OBSERVABILITY`. Prometheus + Grafana (metrics), Loki +
Grafana Explore (logs), Jaeger (traces) — each its own gateway-reachable
viewer route. GKE Cloud Logging/Monitoring disabled (see phase-03 Scope
Changes); scored via this stack instead.

## Status: 4 of 6 rows executed, live; 2 named cuts

Captured against the deployed `fsds-evidence` GKE cluster
(`plans/260811-1627-close-llm-rubric-to-100`, phase 5). The logs and traces
rows below cite the same trace ID and request ID as each other and as the
routing-gateway log/trace-viewer rows — one real request, four independently
observable artifacts (Prometheus series, Grafana panel, Loki log lines,
Jaeger trace).

| Row | Status | Evidence |
|---|---|---|
| Collect + visualize metrics (Prometheus + Grafana) | executed | [LLM-observability-collect-v-visualize-metrics-v-.md](../phase2/evidence/llm/LLM-observability-collect-v-visualize-metrics-v-.md) |
| Web API metrics | executed | [LLM-observability-web-api-metrics.md](../phase2/evidence/llm/LLM-observability-web-api-metrics.md) |
| Logs (same request, queried live) | executed | [LLM-observability-t-ng-t-cho-logs.md](../phase2/evidence/llm/LLM-observability-t-ng-t-cho-logs.md) |
| Traces (same request, JSON persisted) | executed | [LLM-observability-t-ng-t-cho-traces.md](../phase2/evidence/llm/LLM-observability-t-ng-t-cho-traces.md) |
| Token/TTFT/PII-catch metrics | **design_only (named cut)** | blocked by a live round-trip defect between the coordinator and `drift-mcp` (self-referential HTTP loopback); the coordinator answers but the metrics-emitting path is never reached |
| Agent/MCP-tool call metrics | **design_only (named cut)** | blocked by the `coordinator`/`feature-agent`/`drift-agent` Deployments running a stale image that has no `/metrics` endpoint; requires a new CI + digest-bump cycle across all three agent workflows, out of scope for this window |

Both cuts stay `design_only` in `docs/phase2/rubric-matrix.csv` and are
declared here rather than claimed.

## Bugs found and fixed during capture

- `feature-mcp`/`drift-mcp` Services carried no `app.kubernetes.io/name`
  label, so their bundled Prometheus `ServiceMonitor` never matched any
  endpoint — fixed at the shared chart level
  (`charts/fastapi-service/templates/service.yaml`), then re-vendored into
  both wrapper charts (`helm dependency update`).
- `feature-mcp`/`drift-mcp` had no NetworkPolicy egress rule for the Jaeger
  OTLP port — every span export was silently dropped
  (`platform/data/network-policies.yaml`, `mcp-otlp-egress`).
- The deployed `feature-mcp`/`drift-mcp` images predated the OpenTelemetry
  SDK dependency actually landing in the built container layer
  (`ModuleNotFoundError` at runtime despite the exporter code already
  existing) — rebuilt and repushed both images.
- `otel-collector`'s `filelog` receiver parsed timestamps into
  `body.time` but read them back from `attributes.time` — a namespace
  mismatch that failed every single log entry and kept all application pod
  logs out of Loki (`platform/observability/otel-collector.yaml`).

## Verification

- `.venv-phase2/bin/python -m pytest tests/phase2/requirements/ -k llm -q` — 31 passed.
- `.venv-phase2/bin/python scripts/audit_phase2_evidence.py --require-executed --run-validations --track LLM --gitops-root <gitops-repo> --phase1-base <sha>` — the only non-frozen-revision findings are the two named cuts above.
- Live Prometheus target health, Grafana datasource-proxy query, Loki
  `query_range`, and Jaeger `api/traces/<id>` responses are reproduced verbatim
  in each linked evidence file.
