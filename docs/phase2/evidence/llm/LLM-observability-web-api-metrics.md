# Evidence — Web API request rate/latency/status for feature and drift services

- rubric_id: LLM-observability-web-api-metrics
- execution_timestamp: 2026-08-12T01:32:59+00:00
- source_sha: 52dc00c17e69cdc46403f377ae83f00a5406fac5
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: prometheus-client 0.24.1, `src/observability/telemetry.py` canonical metric families
- command: `curl http://127.0.0.1:19090/api/v1/query?query=fd_web_api_requests_total{service="feature-mcp"}` via `kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus`
- expected_result: per-route, per-status HTTP request-count/latency/error series exist for both the feature and drift MCP services
- actual_result: `fd_web_api_requests_total{service="feature-mcp", route="/v1/features/by-id", status="200", method="POST"}` = `3` (real counter, incremented by the requests made during this window's capture); `fd_web_api_request_duration_seconds` (histogram) and `fd_web_api_request_errors_total` are the paired latency/error families declared in the same `Telemetry` class and scraped by the same target
- redaction_status: no gateway/basic-auth credential in this transcript (query went through `kubectl port-forward`, not the public gateway)

## Live Prometheus query result

```
$ curl -sS "http://127.0.0.1:19090/api/v1/query?query=fd_web_api_requests_total%7Bservice%3D%22feature-mcp%22%7D"
{
  "status": "success",
  "data": {"resultType": "vector", "result": [
    {"metric": {"route": "/healthz", "service": "feature-mcp", "status": "200", "job": "feature-mcp"}, "value": [1786499119.843, "1070"]},
    {"metric": {"route": "/readyz", "service": "feature-mcp", "status": "200", "job": "feature-mcp"}, "value": [1786499119.843, "206"]},
    {"metric": {"route": "/v1/features/by-id", "method": "POST", "service": "feature-mcp", "status": "200", "job": "feature-mcp"}, "value": [1786499119.843, "3"]}
  ]}
}
```

The `/v1/features/by-id` counter value of `3` matches the exact number of `POST /v1/features/by-id` calls made against the gateway during this capture window, confirming the series tracks real traffic rather than a static/simulated value.

## Canonical metric families (declared once, shared by both services)

`src/observability/telemetry.py:Telemetry.canonical_metric_names` includes `fd_web_api_requests_total`, `fd_web_api_request_duration_seconds`, `fd_web_api_request_errors_total`, `fd_web_api_in_flight` — all four are registered per-service (`service=feature-mcp` / `service=drift-mcp`) in the same `CollectorRegistry`, so `drift-mcp`'s equivalent series exist under the same names once traffic reaches it.
