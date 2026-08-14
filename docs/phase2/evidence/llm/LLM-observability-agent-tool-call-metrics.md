# Evidence — per-agent and per-MCP-tool call/failure metrics

- rubric_id: LLM-observability-agent-tool-call-metrics
- execution_timestamp: 2026-08-12T08:34:08+00:00
- source_sha: 0bcaf1490b7ffe3561cbe409717b525488e452eb
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: coordinator/feature-agent/drift-agent and MCP images from the Phase 2 Artifact Registry digests; Prometheus recording rules from platform/observability; request path uses qwen2.5-0.5b-instruct
- command: start `kubectl -n agents-sandbox port-forward svc/coordinator 18080:80` and `kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 19090:9090`; POST the nested `feature_request`/`drift_request` payload in the companion token-metrics artifact, then query `phase2:agent_calls_total:rate5m`, `phase2:mcp_tool_calls_total:rate5m`, and `phase2:agent_invocation_failures_total:rate5m` through the Prometheus API
- expected_result: one live coordinator round-trip increments the coordinator, feature-agent, and drift-agent call series; both MCP tools have separate call series; invocation failure series are present per operation
- actual_result: the live request returned HTTP 200 with both specialists and two citations; Prometheus recorded all three agent call series, both named MCP tool series, and per-operation invocation-failure series, including zero failure values for the successful feature/drift/MCP paths
- redaction_status: no credentials, bearer tokens, pod names, IP addresses, or infrastructure labels included; only safe service, agent, tool, and operation labels are retained

## Live request

The correlated request was `phase3-live-metrics-961e550808c8`, the same
synthetic market-stress request documented in the companion token-metrics
artifact. Its machine-readable response was:

```text
{"answer_present":true,"citation_count":2,"error":null,"hops_used":1,"specialists":["drift","feature"],"status":200}
```

## Prometheus output

```text
query={__name__="phase2:agent_calls_total:rate5m"}
[
  {"metric":{"agent":"feature-agent","service":"feature-agent"},"value":[1786523648.711,"0.003508771929824561"]},
  {"metric":{"agent":"coordinator","service":"coordinator"},"value":[1786523648.711,"0.010526315789473682"]},
  {"metric":{"agent":"drift-agent","service":"drift-agent"},"value":[1786523648.711,"0.003508771929824561"]}
]

query={__name__="phase2:mcp_tool_calls_total:rate5m"}
[
  {"metric":{"service":"feature-mcp","tool":"lookup_feature_context"},"value":[1786523648.711,"0.003508771929824561"]},
  {"metric":{"service":"drift-mcp","tool":"build_realtime_drift_report"},"value":[1786523648.711,"0.003508771929824562"]}
]

query={__name__="phase2:agent_invocation_failures_total:rate5m"}
[
  {"metric":{"operation":"agent.feature.run","service":"feature-agent"},"value":[1786523648.711,"0"]},
  {"metric":{"operation":"agent.drift.run","service":"drift-agent"},"value":[1786523648.711,"0"]},
  {"metric":{"operation":"mcp.lookup_feature_context","service":"feature-mcp"},"value":[1786523648.711,"0"]},
  {"metric":{"operation":"mcp.build_realtime_drift_report","service":"drift-mcp"},"value":[1786523648.711,"0"]},
  {"metric":{"operation":"agent.specialist_http.run","service":"coordinator"},"value":[1786523648.711,"0"]},
  {"metric":{"operation":"agent.coordinator.coordinate","service":"coordinator"},"value":[1786523648.711,"0.004089944444444445"]},
  {"metric":{"operation":"http.request","service":"coordinator"},"value":[1786523648.711,"0.004089944444444445"]}
]
```

The positive coordinator failure value is a real capture-window value from
earlier rejected probes; the successful correlated request has zero failure
for its specialist HTTP, specialist agent, and MCP operations. This preserves
the per-call failure series instead of hiding non-zero observations.

The recording rules `phase2:agent_calls_total:rate5m`,
`phase2:mcp_tool_calls_total:rate5m`, and
`phase2:agent_invocation_failures_total:rate5m` are the live rule families
queried above; they are backed by the canonical `fd_agent_calls_total`,
`fd_mcp_tool_calls_total`, and `fd_invocation_failures_total` counters.
