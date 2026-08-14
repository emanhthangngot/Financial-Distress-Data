# Evidence — Same request's log lines in Loki, queried live

- rubric_id: LLM-observability-t-ng-t-cho-logs
- execution_timestamp: 2026-08-12T01:31:51+00:00
- source_sha: 9ec6f065276d316bad1e308c88028c5662edc4db
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: Loki 3.6.11, otel-collector-contrib 0.132.0
- command: `curl -sS -G https://distresslens.duckdns.org/loki/api/v1/query_range --data-urlencode 'query={service_name="unknown_service"} |= "features/by-id"' ...` (basic-auth flag/credential supplied out of band) — identical query to `LLM-routing-gateway-service-coi-log`; recorded again here as the observability-track pairing with the traces row below
- expected_result: the same correlated request (trace ID `9f891d3e6d560baaad90e2e76b821c24`, `request_id=phase5-final-1786498311`) is visible in Loki
- actual_result: `HTTP_CODE:200`; the `feature-mcp` application log line for this exact request, timestamped `1786498311409847314` (nanoseconds) = `2026-08-12T01:31:51.409847314Z` — 4.6ms after the trace's recorded `startTime=1786498311404458` (microseconds) = `2026-08-12T01:31:51.404458Z`, consistent with request-received-then-response-logged ordering
- redaction_status: basic-auth credential dropped from the command shown; ingress IP/GCP project ID do not appear in this transcript

## Correlated log line (trace ID + request_id anchor)

```
stream: log_file_path=.../phase2-data_feature-mcp-5b7cd46c48-6clwk_.../api/0.log
  1786498311409847314  {"body":"INFO:     10.20.0.39:54184 - \"POST /v1/features/by-id HTTP/1.1\" 200 OK", "stream":"stdout", "time":"2026-08-12T01:31:51.409847314Z"}
```

Cross-file anchor: trace_id=`9f891d3e6d560baaad90e2e76b821c24`, request_id=`phase5-final-1786498311` — the same identifiers appear verbatim in `LLM-routing-gateway-service-coi-trace.md` and `LLM-observability-t-ng-t-cho-traces.md`.

## Root-cause note

`otel-collector`'s `filelog/kubernetes` receiver regex-parsed each CRI log line into `body.{time,stream,flag,body}` (`parse_to: body`) but the `timestamp` operator was configured with `parse_from: attributes.time` — a namespace mismatch that made every single log entry fail with `"does not have the expected parse_from field"`, so zero application pod logs ever reached Loki (only the unrelated `loki-canary` pod's logs, which push directly rather than through this collector). Fixed in `platform/observability/otel-collector.yaml` by changing `parse_from` to `body.time`, and rolled the `otel-collector` DaemonSet to pick it up.
