# Observability

Row: `LLM-AC-15-OBSERVABILITY`. Prometheus + Grafana (metrics), Loki +
Grafana Explore (logs), Jaeger (traces) — each its own gateway-reachable
viewer route. GKE Cloud Logging/Monitoring disabled (see phase-03 Scope
Changes); scored via this stack instead.

## Implementation present (static)

The application-side instrumentation is present in the current working tree:

- `src/observability/telemetry.py` provides service-labeled Prometheus
  families for input/output/total tokens, generation round-trip time, TTFT,
  PII-safety catches, per-agent calls, per-MCP-tool calls, invocation failures
  and Web API RED metrics.
- The same module redacts prompts, documents, PII, credentials and model
  output while retaining correlation, release and session metadata for logs
  and span attributes.
- `apps/feature-mcp/app/main.py`, `apps/drift-mcp/app/main.py`, their MCP
  servers, and `src/agents/*.py` wire the metric and trace hooks into service,
  tool and agent execution paths.

The sibling `financial-distress-gitops` working tree contains the static
platform shape in `argocd/applications/platform-observability.yaml`,
`platform/observability/prometheus-values.yaml`,
`platform/observability/loki-otel-values.yaml`,
`platform/observability/jaeger.yaml`,
`platform/observability/otel-collector.yaml`,
`platform/observability/grafana-dashboards/`, and the viewer ingress route.
These changes are uncommitted and have not been shown to Argo CD as a
reconciled revision.

## Validation performed

- `.venv-phase2/bin/python -m pytest -q tests/phase2/test_observability.py` —
  **3 passed**.
- `.venv/bin/python -m pytest -q tests/phase2/requirements/test_llm_ac_13_routing.py tests/phase2/requirements/test_llm_ac_15_observability.py` — exit 0,
  **13 skipped** because the rows remain `design_only`; this is not runtime
  proof of a deployed telemetry stack.
- The focused web tests and `npm run typecheck` also pass; the route-level
  results are recorded in [routing_gateway.md](./routing_gateway.md).

## Deployment and evidence status

The metrics, log-redaction and trace-correlation behavior has local source
coverage only. No Prometheus/Grafana, Loki or Jaeger installation, gateway
viewer response, dashboard capture, or end-to-end correlation across
gateway → API → MCP → agent → model has been executed in this worktree. No
Phase 04 observability evidence file has been executed, and none of the six
observability rows is claimed as `executed`; the rubric CSV remains
`design_only` for these rows.

## Release blockers before live proof

- The gateway auth secret must be provisioned through the sealed-secret flow
  and verified on every viewer route. No credential is stored in this page.
- The web deployment must receive the Supabase runtime Secret referenced as
  `web-runtime-config`; its presence and runtime behavior are not verified.
- The web image and observability manifests must be released from immutable
  image/source/GitOps SHAs. The current web image digest is empty and both
  checkouts contain uncommitted Phase 04 changes.
- A schedulable GKE cluster with capacity for the observability stack and its
  application dependencies must be available. This session did not verify a
  live node pool, Argo sync, or pod readiness.

Until those blockers are cleared, the telemetry code and manifests are static
implementation evidence only; they do not establish deployed observability.
