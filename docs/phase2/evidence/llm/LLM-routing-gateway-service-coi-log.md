# Evidence — Log viewer through the gateway, real application log lines

- rubric_id: LLM-routing-gateway-service-coi-log
- execution_timestamp: 2026-08-12T01:31:51+00:00
- source_sha: 52dc00c17e69cdc46403f377ae83f00a5406fac5
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: Grafana (bundled Loki datasource), Loki 3.6.11, otel-collector-contrib 0.132.0
- command: `curl -sS -G https://distresslens.duckdns.org/loki/api/v1/query_range --data-urlencode 'query={service_name="unknown_service"} |= "features/by-id"' ...` through the gateway (basic-auth flag/credential supplied out of band); Grafana Explore is the intended viewer surface, this is the same query executed non-interactively
- expected_result: real application log lines are queryable through the gateway/Grafana path, correlated to a specific live request
- actual_result: `HTTP_CODE:200`; the query returned two real log lines for the exact same request (matching timestamp `2026-08-12T01:31:51.41s`, same as the trace and web-API-metrics rows): the nginx-ingress access-log line and the `feature-mcp` application's own uvicorn access-log line, both showing `POST /v1/features/by-id ... 200`
- redaction_status: basic-auth credential dropped from the command shown; ingress IP/GCP project ID do not appear in this transcript; the two log lines below are the full unredacted match — they contain only an HTTP method/path/status and a client user-agent string, no credential or PII

## Correlated log lines (same request as the traces/web-api-metrics rows below)

```
$ curl -sS [basic-auth flag and credential supplied out of band] -G \
  "https://distresslens.duckdns.org/loki/api/v1/query_range" \
  --data-urlencode 'query={service_name="unknown_service"} |= "features/by-id"' \
  --data-urlencode "start=...&end=..." --data-urlencode "limit=50"

stream: log_file_path=.../ingress-nginx_nginx-ingress-nginx-ingress-controller-.../nginx-ingress/0.log
  1786498311410175284  {"body":"27.78.86.86 - grader [12/Aug/2026:01:31:51 +0000] \"POST /v1/features/by-id HTTP/1.1\" 200 68 \"-\" \"curl/8.21.0\" \"-\"", ...}

stream: log_file_path=.../phase2-data_feature-mcp-5b7cd46c48-6clwk_.../api/0.log
  1786498311409847314  {"body":"INFO:     10.20.0.39:54184 - \"POST /v1/features/by-id HTTP/1.1\" 200 OK", ...}
```

Both lines land within 0.4ms of each other, matching the Jaeger trace `startTime=1786498311404458` and the `request_id=phase5-final-1786498311` recorded in the traces evidence file — three independent systems (Loki, Jaeger, and Prometheus's `fd_web_api_requests_total`) observing the same one request.

## Root-cause note

The gateway route (`platform/ingress/routes-viewers.yaml`, `/loki/api/v1/*`) and the Loki backend were both already correct. Two independent defects blocked this evidence until fixed in this window: (1) `otel-collector`'s `filelog` receiver used `parse_to: body` but `timestamp.parse_from: attributes.time`, so every parsed timestamp field silently landed in the wrong location and every log entry failed with "does not have the expected parse_from field" — no pod log ever reached Loki. Fixed by changing `parse_from` to `body.time` in `platform/observability/otel-collector.yaml`. (2) `feature-mcp`/`drift-mcp` had no NetworkPolicy egress rule for the OTLP endpoint, and no ServiceMonitor/Service label wiring for metrics (see the traces and web-api-metrics evidence files) — unrelated to this specific row but fixed in the same window.
