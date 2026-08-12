# Evidence — Prometheus scraping + Grafana dashboard rendering live series

- rubric_id: LLM-observability-collect-v-visualize-metrics-v-
- execution_timestamp: 2026-08-12T01:32:57+00:00
- source_sha: 29f6a7ce00a2a6ff2ac42604983e814b1eeffe06
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: kube-prometheus-stack 88.2.0 (Prometheus v3.13.2), Grafana (bundled), prometheus-client 0.24.1
- command: (1) `curl http://127.0.0.1:19090/api/v1/targets` via `kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus`; (2) Grafana login + its own datasource-proxy query for the same PromQL used by the `Phase 2 LLM observability` dashboard's "Web API request rate" panel
- expected_result: Prometheus actively scrapes the MCP services and a Grafana dashboard renders a live series from that data
- actual_result: `feature-mcp`/`drift-mcp` scrape targets report `health: up`; Grafana's own datasource proxy (using a real Grafana session cookie, not a bypass) returned non-empty vector results for the dashboard panel's exact PromQL, `sum by (service, route, status) (rate(fd_web_api_requests_total{service=~".+"}[5m]))`, including a live `route="/v1/features/by-id", service="feature-mcp", status="200"` series
- redaction_status: no gateway/basic-auth credential in this transcript (Prometheus/Grafana session queries went through `kubectl port-forward`, not the public gateway); Grafana admin password not shown

## Prometheus target health

```
$ curl -sS http://127.0.0.1:19090/api/v1/targets | jq ...
serviceMonitor/phase2-data/feature-mcp/0  http://10.20.0.137:8000/metrics  up
serviceMonitor/phase2-data/drift-mcp/0    http://10.20.0.136:8000/metrics  up
```

## Grafana's own datasource-proxy query (the dashboard panel's exact PromQL)

```
$ curl -sS -b <grafana-session-cookie> -G \
  ".../grafana/api/datasources/proxy/uid/prometheus/api/v1/query" \
  --data-urlencode 'query=sum by (service, route, status) (rate(fd_web_api_requests_total{service=~".+"}[5m]))'

{"status":"success","data":{"resultType":"vector","result":[
  {"metric":{"route":"/v1/features/by-id","service":"feature-mcp","status":"200"},"value":[1786499177.426,"0.0040642222222222225"]},
  {"metric":{"route":"/healthz","service":"feature-mcp","status":"200"},"value":[1786499177.426,"0.268..."]},
  {"metric":{"route":"/healthz","service":"drift-mcp","status":"200"},"value":[1786499177.426,"0.287..."]}
  ... ]}}
```

The dashboard `db/phase-2-llm-observability` (uid `phase2-llm-observability`) exists in the live Grafana instance and its "Web API request rate" panel uses this exact query — this is the query Grafana itself runs when rendering that panel, executed non-interactively for reproducibility.

## Root-cause note

`feature-mcp`/`drift-mcp`'s Service objects (rendered from the shared `fastapi-service` Helm chart) carried no `app.kubernetes.io/name` label, so the chart's own bundled `ServiceMonitor` (which selects on that label) matched zero Services and every discovered endpoint was silently dropped at the relabel step. Fixed by adding the label to `charts/fastapi-service/templates/service.yaml` and re-vendoring the packaged subchart `.tgz` into `charts/feature-mcp`/`charts/drift-mcp` (`helm dependency update`).
