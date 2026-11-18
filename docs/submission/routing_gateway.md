# Routing & Gateway (NGINX Ingress Controller)

Row: `LLM-AC-13-ROUTING`. F5 NGINX Ingress Controller OSS is the only
externally reachable object; every backend Service is `ClusterIP`.

## Status: 7 of 7 rows captured, freeze pending

Captured against the deployed `fsds-evidence` GKE cluster
(`plans/260811-1627-close-llm-rubric-to-100`, phase 5). Each evidence file
below carries the 8-field contract and raw command output. The log/trace pair
is cross-anchored to a shared Jaeger trace ID. The rows are represented as
`executed` in the canonical matrix; the final two-repository freeze still
depends on post-commit source/GitOps SHA restamping.

| Row | Evidence |
|---|---|
| Hide services behind the gateway | [LLM-routing-gateway-c-c-service-c-n-c-hide-ng-sau-.md](../platform/evidence/llm/LLM-routing-gateway-c-c-service-c-n-c-hide-ng-sau-.md) |
| Feature Web API through the gateway | [LLM-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-.md](../platform/evidence/llm/LLM-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-.md) |
| Agent-test UI through the gateway | [LLM-routing-gateway-ui-test-agent.md](../platform/evidence/llm/LLM-routing-gateway-ui-test-agent.md) |
| Agent-registry UI through the gateway | [LLM-routing-gateway-ui-cho-agent-registry.md](../platform/evidence/llm/LLM-routing-gateway-ui-cho-agent-registry.md) |
| Gateway auth (401/200) | [LLM-routing-gateway-authentication-cho-ui-test-age.md](../platform/evidence/llm/LLM-routing-gateway-authentication-cho-ui-test-age.md) |
| Log viewer through the gateway | [LLM-routing-gateway-service-coi-log.md](../platform/evidence/llm/LLM-routing-gateway-service-coi-log.md) |
| Trace viewer through the gateway | [LLM-routing-gateway-service-coi-trace.md](../platform/evidence/llm/LLM-routing-gateway-service-coi-trace.md) |

All seven rows are captured; none is cut on this track. This page is a
reviewer index, not the final freeze seal.

## Bugs found and fixed during capture

- `feature-mcp`'s `FEAST_REPO_PATH` pointed at a file, not a directory —
  `feast.FeatureStore` failed on every request (`apps/dev/feature-mcp/values.yaml`).
- `feature-mcp`/`drift-mcp` Services carried no `app.kubernetes.io/name` label,
  so their bundled `ServiceMonitor` matched nothing (`charts/fastapi-service/templates/service.yaml`).
- `feature-mcp`/`drift-mcp` had no NetworkPolicy egress for the Jaeger OTLP
  port (`platform/data/network-policies.yaml`).
- The deployed `feature-mcp`/`drift-mcp` images predated the OpenTelemetry SDK
  dependency actually landing in the built layer; rebuilt and repushed both.
- `otel-collector`'s log-parsing pipeline had a `parse_to`/`parse_from`
  namespace mismatch that silently dropped every pod log line before it
  reached Loki (`platform/observability/otel-collector.yaml`).

## Verification

- `.venv-platform/bin/python -m pytest tests/platform/requirements/ -k llm -q` — 31 passed.
- `.venv-platform/bin/python scripts/audit_phase2_evidence.py --require-executed --run-validations --track LLM --gitops-root <gitops-repo> --lakehouse-base <sha>` — rerun after SHA restamping; the strict final freeze gate must report zero findings without acceptance cuts.
