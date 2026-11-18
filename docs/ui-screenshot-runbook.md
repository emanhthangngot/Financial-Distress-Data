# UI Screenshot Capture Runbook

Reproduction steps and checklist for the the platform capture campaign of
`plans/260814-1223-recsys-format-docs-overhaul/`. GKE plane is captured first
— it is the perishable resource. Local Docker stack and product plane follow.
Every row below gets exactly one `docs/pngs/manifest.csv` entry once captured
or reused.

## Cluster context (captured at)

```text
kubectl config current-context
  gke_project-60655616-d84a-4883-867_asia-southeast1-b_fsds-evidence
```

Most in-cluster UIs are `ClusterIP` only — reached via
`kubectl -n <ns> port-forward svc/<name> <local>:<remote>` for the duration of
the capture, then torn down. Public ingress host: `distresslens.duckdns.org`
(nginx, `34.21.242.110`).

## Checklist

Status legend: `[ ]` not yet captured, `re-capture` = live capture needed this
campaign, `reuse-copy` = existing PNG copied into `docs/pngs/` under a
contract name (source path recorded in the manifest).

### GKE evidence plane (capture first)

| # | Subsystem | Target capture | Disposition | Outcome |
|---|---|---|---|---|
| 1 | Argo CD | 13 applications Synced/Healthy, list view | re-capture | **gap** — `kubectl -n argocd port-forward svc/argocd-server` fails with `connection reset by peer` at the node's CNI netns layer (pod shows `Running`, other services on the same node port-forward fine). Not a sandbox/auth issue — a live node-level networking fault on that pod. CLI status (`kubectl get applications -n argocd`) confirms 13/13 Synced/Healthy and is cited as text evidence instead. User to investigate/restart the pod; re-attempt UI capture then. |
| 2 | Argo CD | one application detail view (e.g. `kagent`) | re-capture | **gap** — same blocker as row 1 |
| 3 | kagent | 10 agents Ready, list view | re-capture | **done** — `kagent_agents_ready.png` |
| 4 | kagent | one agent spec detail | re-capture | **done** — `kagent_agent_spec_detail.png` |
| 5 | kagent | one agent run/conversation | re-capture | **done** — `kagent_agent_run_success.png` (successful round-trip, `promql-agent`) plus `kagent_agent_run_token_limit_error.png` (a real error from a different agent, kept as honest evidence of an actual context-window limit) |
| 6 | Model gateway (agentgateway) | gateway programmed / route status via `kubectl` | re-capture | **done, CLI evidence** — `kubectl get gateway -A` shows `agentgateway-proxy` class `agentgateway` PROGRAMMED=True; `kubectl get httproute -A` shows `fd-chat-model-route`. Embedded as a code block in the narrative doc rather than a screenshot — no UI exists for this resource. |
| 7 | KServe | inference service `Ready` status via `kubectl get isvc` | re-capture | **done, CLI evidence** — `kubectl get isvc -A` shows `fd-chat-model` and `fd-embeddings` both `READY=True` |
| 8 | KServe | a real prediction round-trip (curl through gateway) | re-capture | **gap** — status conditions confirmed Ready via CLI (row 7); an actual inference round-trip curl was not run this campaign, left explicit |
| 9 | MCP services | tool list via kagent UI or `kubectl` describe | re-capture | **partial** — kagent agent detail panel (`kagent_agent_spec_detail.png`) lists bound tools for one agent; a dedicated MCP-server tool listing was not captured separately |
| 10 | MCP services | one tool call + response | re-capture | **done, indirect** — visible as `feature_mcp.http_request` / `drift_mcp.http_request` spans inside `jaeger_coordinator_trace_roundtrip.png` |
| 11 | Coordinator agent | full round-trip with feature + drift citations | re-capture | **done** — `jaeger_coordinator_trace_roundtrip.png`: 5-span, 170ms trace, `coordinator-agent` → `feature-agent`/`feature-mcp` and → `drift-agent`/`drift-mcp` |
| 12 | Prometheus | targets up page | re-capture | **done** — `prometheus_targets_up.png` (9/9 UP) |
| 13 | Prometheus | agent/tool call + token/latency/PII metric query | re-capture | **done, partial** — `prometheus_llm_tokens_query.png` covers token metrics (`platform:llm_request_total_tokens_total:sum`); latency and PII metric queries not separately captured this campaign |
| 14 | Grafana | dashboard list / one dashboard per rubric claim | re-capture | **blocked** — Grafana requires login; entering credentials into any field is a prohibited action regardless of source, and reading the admin secret to do so was denied by policy. Capture needs the user to authenticate interactively, or an anonymous-viewer URL if one is configured. |
| 15 | Jaeger | discoverable services list | re-capture | **done** — `jaeger_search_services.png` (6 services) |
| 16 | Jaeger | one end-to-end trace | re-capture | **done** — `jaeger_coordinator_trace_roundtrip.png` (same image serves rows 11 and 16) |
| 17 | Ingress/NGINX | routing + auth challenge on a hidden service | re-capture | **gap** — not attempted this campaign |

### Local the platform stack

| # | Subsystem | Target capture | Disposition | Outcome |
|---|---|---|---|---|
| 18 | Airflow | DAG graph — `dp1_bronze_ingest`/`ingest_source_to_bronze` | reuse-copy | **done** — `airflow_dp1_bronze_ingest_dag.png` |
| 19 | Airflow | DAG graph — `build_silver_gold` | reuse-copy | **done** — `airflow_dp2_silver_gold_dag.png` |
| 20 | Airflow | DAG graph — `build_offline_features` | reuse-copy | **done** — `airflow_dp3_offline_features_dag.png` |
| 21 | Airflow | successful task-tree run per DAG | reuse-copy | **done** — `airflow_dp2_dp3_successful_run.png` |
| 22 | Kafka | topic offsets | gap | not captured — no existing capture; would need the local Docker stack brought up fresh |
| 23 | MinIO | Bronze/Silver/Gold object paths | gap | not captured — same reason |
| 24 | DuckDB/DBeaver | Gold views, schema, row counts | gap | not captured — same reason |
| 25 | Flink | job overview | reuse-copy | **done** — `flink_job_overview.png` |
| 26 | Flink | checkpoints, baseline vs optimized | reuse-copy | **done** — `flink_checkpoints_baseline.png` + `flink_checkpoints_optimized.png` |
| 27 | Spark UI | baseline vs optimized stage timings | reuse-copy | **done** — `spark_stage_timings_baseline.png` + `spark_stage_timings_optimized.png` |

### Product plane

| # | Subsystem | Target capture | Disposition | Outcome |
|---|---|---|---|---|
| 28 | Web app | login | reuse-copy | **done** — `product_web_login_success.png` |
| 29 | Web app | analyst surfaces (companies) | reuse-copy | **done** — `product_analyst_companies_surface.png` |
| 30 | Web app | agent registry UI | reuse-copy | **done** — `product_agent_registry_ui.png` |
| 31 | Web app | agent chat / assistant | gap | not captured — only a `root--assistant-unavailable` state exists in the source pool, no active-chat capture |
| 32 | Supabase | RLS policies | gap | not captured — out of scope this campaign |
| 33 | Supabase | auth users table (redacted) | gap | not captured — out of scope this campaign |

**Campaign summary:** 20 images landed in `docs/pngs/` (9 live GKE captures, 11 reuse-copies). 8 rows remain explicit gaps (Argo CD UI x2, KServe round-trip curl, dedicated MCP tool list, Kafka/MinIO/DuckDB local captures, product chat, Supabase x2); Grafana is blocked on interactive login. None invented.

## Capture — GKE plane

```bash
# Argo CD (admin UI on 8080 -> svc 443)
kubectl -n argocd port-forward svc/argocd-server 8081:443 &
# open https://localhost:8081, applications list + one detail view

# kagent UI
kubectl -n kagent port-forward svc/kagent-ui 8082:8080 &
# open http://localhost:8082, agents list + one spec + one run

# Grafana
kubectl -n monitoring port-forward svc/monitoring-grafana 8083:80 &
# open http://localhost:8083

# Prometheus
kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 8084:9090 &
# open http://localhost:8084/targets, then a metric query

# Jaeger
kubectl -n monitoring port-forward svc/jaeger 8086:16686 &
# open http://localhost:8086

# KServe / gateway status (CLI, no UI — capture terminal output)
kubectl get isvc -A
kubectl -n agentgateway-system get pods,svc
```

Kill every `port-forward` (`kill %1 %2 ...` or `pkill -f "kubectl.*port-forward"`
scoped to this session's PIDs only) once the capture set for that service is
done — do not leave forwards running past the campaign.

## Capture — local the platform stack

See `AGENTS.md` for the Flink opt-in flag. Existing captures already satisfy
rows 18–21 and 25–27 (reuse-copy); rows 22–24 need the stack brought up fresh
if a re-capture is chosen instead of leaving them as documented gaps.

## Capture — product plane

`scripts/capture_ui_screenshots.py` extended per the platform requirements, or
reuse existing `docs/platform/evidence/product/*.png` Playwright captures
(already contract-quality: state, role, viewport encoded in filename).

## Redaction pass (blocking gate before commit)

Every new PNG reviewed for: secrets, tokens, cookies, JWTs, private IPs beyond
what's already public in the repo, personal data. Blur or re-take otherwise —
this gate blocks the commit, not a formality.

## After capture

1. Fill `docs/pngs/manifest.csv` — one row per image, `proves` cell never
   empty.
2. Any checklist row still unresolved after this campaign is left as an
   explicit `gap` in this table, never invented.
3. Commit: `docs(evidence): capture live tool screenshots for narrative docs`.
