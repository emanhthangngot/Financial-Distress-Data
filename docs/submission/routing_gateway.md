# Routing & Gateway (NGINX Ingress Controller)

Row: `LLM-AC-13-ROUTING`. F5 NGINX Ingress Controller OSS is the only
externally reachable object; every backend Service is `ClusterIP`.

## Status: 6 of 7 rows executed, live

Captured against the deployed `fsds-evidence` GKE cluster
(`plans/260811-1627-close-llm-rubric-to-100`, phase 5). Each evidence file
below carries the 8-field contract, raw command output, and — for the six
routing rows below — is cross-anchored to the TLS certificate serial
`06BA2F629A81F5F38D53A74F3D035D8394F3` and, for the log/trace pair, a shared
Jaeger trace ID.

| Row | Evidence |
|---|---|
| Hide services behind the gateway | [LLM-routing-gateway-c-c-service-c-n-c-hide-ng-sau-.md](../phase2/evidence/llm/LLM-routing-gateway-c-c-service-c-n-c-hide-ng-sau-.md) |
| Feature Web API through the gateway | [LLM-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-.md](../phase2/evidence/llm/LLM-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-.md) |
| Agent-test UI through the gateway | [LLM-routing-gateway-ui-test-agent.md](../phase2/evidence/llm/LLM-routing-gateway-ui-test-agent.md) |
| Agent-registry UI through the gateway | [LLM-routing-gateway-ui-cho-agent-registry.md](../phase2/evidence/llm/LLM-routing-gateway-ui-cho-agent-registry.md) |
| Gateway auth (401/200) | [LLM-routing-gateway-authentication-cho-ui-test-age.md](../phase2/evidence/llm/LLM-routing-gateway-authentication-cho-ui-test-age.md) |
| Log viewer through the gateway | [LLM-routing-gateway-service-coi-log.md](../phase2/evidence/llm/LLM-routing-gateway-service-coi-log.md) |
| Trace viewer through the gateway | [LLM-routing-gateway-service-coi-trace.md](../phase2/evidence/llm/LLM-routing-gateway-service-coi-trace.md) |

All seven rows are captured; none is cut on this track.

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

- `.venv-phase2/bin/python -m pytest tests/phase2/requirements/ -k llm -q` — 31 passed.
- `.venv-phase2/bin/python scripts/audit_phase2_evidence.py --require-executed --run-validations --track LLM --gitops-root <gitops-repo> --phase1-base <sha>` — zero artifact/assertion/denylist failures; only the expected pre-freeze frozen-revision notices and the two named observability cuts remain (see [observability.md](./observability.md)).
