# Evidence — Same request's Jaeger trace, trace JSON persisted

- rubric_id: LLM-observability-t-ng-t-cho-traces
- execution_timestamp: 2026-08-12T01:31:51+00:00
- source_sha: 1b38709b4ef1b28e7a1bb7f12a49b68cbfe1c049
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: Jaeger v2.20.0, feature-mcp `sha256:e2218e6d337b1dc1ec04a9a1e132969e9aa91c6adf034e91548a0d4e3d05b440`
- command: `curl -sS https://distresslens.duckdns.org/jaeger/api/traces/9f891d3e6d560baaad90e2e76b821c24` (basic-auth flag/credential supplied out of band) — same trace as `LLM-routing-gateway-service-coi-trace`, persisted here again as the observability-track pairing with the logs row above
- expected_result: the same correlated request's trace is retrievable and its JSON is persisted in the evidence (Jaeger keeps traces in memory only — no PVC, `platform/observability/jaeger.yaml`)
- actual_result: `HTTP_CODE:200`; full trace JSON persisted below, `trace_id=9f891d3e6d560baaad90e2e76b821c24`, `request_id=phase5-final-1786498311`
- redaction_status: basic-auth credential dropped from the command shown; ingress IP/GCP project ID do not appear in this transcript; trace JSON contains only span metadata, no PII/prompt/credential

## Persisted trace JSON

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
            {"key": "method", "value": "POST"},
            {"key": "operation", "value": "/v1/features/by-id"},
            {"key": "release", "value": "phase2"},
            {"key": "request_id", "value": "phase5-final-1786498311"},
            {"key": "service", "value": "feature-mcp"},
            {"key": "status_code", "value": 200}
          ]
        }
      ],
      "processes": {"p1": {"serviceName": "feature-mcp"}}
    }
  ]
}
```

Cross-file anchor: trace_id=`9f891d3e6d560baaad90e2e76b821c24`, request_id=`phase5-final-1786498311` — the same identifiers appear verbatim in `LLM-routing-gateway-service-coi-trace.md` and `LLM-observability-t-ng-t-cho-logs.md`.

## Root-cause note

Same as `LLM-routing-gateway-service-coi-trace.md`: the deployed `feature-mcp`/`drift-mcp` images predated the `opentelemetry-*` dependencies actually landing in the built container layer, so the OTel SDK import failed at runtime and no span was ever created despite the exporter-config code path already existing. Rebuilt and redeployed both images with the current `Dockerfile`s (which do declare the OTel packages), plus a NetworkPolicy egress fix for the Jaeger OTLP port that was blocking export even for services that could import the SDK.
