# Evidence — Trace viewer through the gateway, real trace with spans

- rubric_id: LLM-routing-gateway-service-coi-trace
- execution_timestamp: 2026-08-12T01:31:51+00:00
- source_sha: 09640b7ede4848f47be9dd9a1cd11b4d041a7170
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: Jaeger v2.20.0, feature-mcp `sha256:e2218e6d337b1dc1ec04a9a1e132969e9aa91c6adf034e91548a0d4e3d05b440`, opentelemetry-sdk 1.44.0
- command: `curl -sS https://distresslens.duckdns.org/jaeger/api/traces/<trace-id>` through the gateway (basic-auth flag/credential supplied out of band); trace ID obtained from Jaeger's own `/api/traces?service=feature-mcp` search
- expected_result: a real distributed trace with spans is retrievable through the gateway for a live request, not a synthetic fixture
- actual_result: `HTTP_CODE:200`; trace `9f891d3e6d560baaad90e2e76b821c24` persisted below — one span, `feature_mcp.http_request`, `operation=/v1/features/by-id`, `method=POST`, `status_code=200`, `request_id=phase5-final-1786498311`, `duration=4895µs`, `startTime=1786498311404458` — the same request correlated in the logs and web-api-metrics evidence files
- redaction_status: basic-auth credential dropped from the command shown; ingress IP/GCP project ID do not appear in this transcript; the persisted trace JSON below carries only span metadata (route, method, status, service, a caller-supplied request-id marker) — no PII, prompt, or credential fields

## Persisted trace JSON (full, unredacted — contains no sensitive fields)

```json
{
  "data": [
    {
      "traceID": "9f891d3e6d560baaad90e2e76b821c24",
      "spans": [
        {
          "traceID": "9f891d3e6d560baaad90e2e76b821c24",
          "spanID": "3358e68f0520c4b7",
          "operationName": "feature_mcp.http_request",
          "startTime": 1786498311404458,
          "duration": 4895,
          "tags": [
            {"key": "otel.scope.name", "value": "financial-distress.observability"},
            {"key": "correlation_id", "value": "unknown"},
            {"key": "method", "value": "POST"},
            {"key": "operation", "value": "/v1/features/by-id"},
            {"key": "release", "value": "phase2"},
            {"key": "release_id", "value": "unknown"},
            {"key": "request_id", "value": "phase5-final-1786498311"},
            {"key": "service", "value": "feature-mcp"},
            {"key": "session_id", "value": "unknown"},
            {"key": "status_code", "value": 200}
          ]
        }
      ],
      "processes": {"p1": {"serviceName": "feature-mcp"}}
    }
  ]
}
```

## Root-cause note (this row required a real code + build fix, not just a route)

`feature-mcp`/`drift-mcp` had the OpenTelemetry SDK dependency listed in their `Dockerfile`s and the exporter-config code path already wired (`src/observability/telemetry.py:_configure_otel_exporter`), but the **deployed image** predated that dependency actually landing in the built layer (`ModuleNotFoundError: No module named 'opentelemetry'` inside the live pod) — a stale-image gap, not a missing route. Rebuilt and pushed both images (`docker build`/`docker push` to the project Artifact Registry, new digests `sha256:e2218e6d...` / `sha256:e8fe83de...`), bumped `apps/dev/{feature,drift}-mcp/values.yaml`, and redeployed via Argo. A second, independent defect (`phase2-data-default-deny` NetworkPolicy had no egress rule for the Jaeger OTLP port) was fixed in the same window (`platform/data/network-policies.yaml`, `mcp-otlp-egress`).
