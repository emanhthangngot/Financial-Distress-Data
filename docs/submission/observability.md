# Observability

Row: `LLM-AC-15-OBSERVABILITY`. Prometheus + Grafana (metrics), Loki +
Grafana Explore (logs), Jaeger (traces) — each its own gateway-reachable
viewer route. GKE Cloud Logging/Monitoring disabled (see phase-03 Scope
Changes); scored via this stack instead.

## Status: 6 of 6 rows executed, live

Captured against the deployed `fsds-evidence` GKE cluster
(`plans/260811-1627-close-llm-rubric-to-100`, phase 5). The logs and traces
rows below cite the same trace ID and request ID as each other and as the
routing-gateway log/trace-viewer rows — one real request, four independently
observable artifacts (Prometheus series, Grafana panel, Loki log lines,
Jaeger trace).

| Row | Status | Evidence |
|---|---|---|
| Collect + visualize metrics (Prometheus + Grafana) | executed | [LLM-observability-collect-v-visualize-metrics-v-.md](../platform/evidence/llm/LLM-observability-collect-v-visualize-metrics-v-.md) |
| Web API metrics | executed | [LLM-observability-web-api-metrics.md](../platform/evidence/llm/LLM-observability-web-api-metrics.md) |
| Logs (same request, queried live) | executed | [LLM-observability-t-ng-t-cho-logs.md](../platform/evidence/llm/LLM-observability-t-ng-t-cho-logs.md) |
| Traces (same request, JSON persisted) | executed | [LLM-observability-t-ng-t-cho-traces.md](../platform/evidence/llm/LLM-observability-t-ng-t-cho-traces.md) |
| Token/TTFT/PII-catch metrics | executed | [LLM-observability-m-b-o-t-nh-t-c-c-metrics.md](../platform/evidence/llm/LLM-observability-m-b-o-t-nh-t-c-c-metrics.md) |
| Agent/MCP-tool call metrics | executed | [LLM-observability-agent-tool-call-metrics.md](../platform/evidence/llm/LLM-observability-agent-tool-call-metrics.md) |

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
- The drift MCP mounted endpoint used a fragile HTTP self-loopback for its
  pure drift calculation — replaced with an in-process client for loopback
  configuration while preserving the HTTP client for split deployments.
- The coordinator timeout budget was raised to 50 seconds and made
  configurable through `AGENT_TIMEOUT_SECONDS`; all three agent images were
  rebuilt with `/metrics` and rolled out at immutable Artifact Registry
  digests.

## Verification

- `.venv-platform/bin/python -m pytest tests/platform/requirements/ -k llm -q` — 31 passed.
- `.venv-platform/bin/python scripts/audit_phase2_evidence.py --strict --require-executed --run-validations --track LLM --ml 100 --llm 100 --gitops-root <gitops-repo> --lakehouse-base <sha>` — zero named cuts; 60/60 LLM rows and 100/100 points.
- Live Prometheus target health, Grafana datasource-proxy query, Loki
  `query_range`, and Jaeger `api/traces/<id>` responses are reproduced verbatim
  in each linked evidence file.
