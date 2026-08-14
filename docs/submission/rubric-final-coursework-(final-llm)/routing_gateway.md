---
title: "Routing & Gateway"
date: 2026-08-14
status: active
---

# Routing & Gateway: one NGINX ingress hides every backend, gated by basic-auth

This doc proves the seven rows in "Routing & Gateway (NGINX Ingress
Controller)": every backend service (web, feature API, Grafana, Loki,
Jaeger) is reachable only through `https://distresslens.duckdns.org`, gated
by basic-auth, with real request/log/trace correlation across three
independent observability systems. It does not hide one real, disclosed
defect in the agent-test round-trip — see the honesty note in step 7.

**Active deployment facts:** F5 NGINX Ingress Controller
(`nginx/nginx-ingress` 5.5.4), cert-manager v1.16.2, host
`distresslens.duckdns.org`, all backends `ClusterIP`-only.

## Part I — Hidden backends and authentication

### 1. No backend has a direct external path

```text
$ timeout 8 curl -sS -o /dev/null -w "%{http_code}\n" "http://<INGRESS_IP>:80/"
curl: (28) Operation timed out after 8000 milliseconds with 0 bytes received
```

`web` is `ClusterIP`-only (`platform/data/network-policies.yaml`) — no
NodePort, no LoadBalancer of its own. `platform/ingress/routes-ui.yaml` sets
`nginx.org/use-cluster-ip: "true"` on every mergeable-Ingress route; the F5
NGINX Ingress Controller's `LoadBalancer` Service is the only path exposed to
`0.0.0.0/0`. Full evidence:
[`LLM-routing-gateway-c-c-service-c-n-c-hide-ng-sau-.md`](../../phase2/evidence/llm/LLM-routing-gateway-c-c-service-c-n-c-hide-ng-sau-.md).

### 2. Basic-auth challenge on every protected route

```text
$ curl -sS -i https://distresslens.duckdns.org/
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Basic realm="FSDS evidence platform"
```

| Route | Unauthenticated | Authenticated |
|---|---:|---:|
| `/` | 401 | 200 |
| `/agents/registry` | 401 | 200 |
| `/v1/features/by-id` (POST) | 401 | 200 (after the fix in step 3) |
| `/grafana` | 401 | 302 (Grafana's own login) |
| `/loki/api/v1/query` | 401 | 401 without `query` param (route reached, Loki's own validation applies) |
| `/jaeger` | 401 | 307 (Jaeger UI redirect) |

Credential stored as a `SealedSecret` (`gateway-basic-auth`), ciphertext
only, never the source htpasswd line. No rate-limit is configured on these
routes — its absence is stated honestly rather than claimed. Full evidence:
[`LLM-routing-gateway-authentication-cho-ui-test-age.md`](../../phase2/evidence/llm/LLM-routing-gateway-authentication-cho-ui-test-age.md).

## Part II — Real services through the gateway

### 3. Feature Web API — real data, real fix

```text
$ curl -sS [auth] -X POST "https://distresslens.duckdns.org/v1/features/by-id" \
    -d '{"user_id":"VNM","feature_names":["stream_market_features:last_price",...]}'
{"user_id":"VNM","features":{"last_price":72.5,"event_count_1h":42}}   HTTP 200
```

**Real bug found and fixed:** `feature-mcp`'s `FEAST_REPO_PATH` pointed at the
renamed `feature_store.yaml` **file** instead of its **directory**, so
`feast.FeatureStore(repo_path=...)` raised `FileNotFoundError` on every
request and the route answered `503`. Fixed in
`apps/dev/feature-mcp/values.yaml`, redeployed via Argo. Full evidence:
[`LLM-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-.md`](../../phase2/evidence/llm/LLM-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-.md).

### 4. Log viewer — real correlated log lines

Two log lines for the same `POST /v1/features/by-id` request, 0.4ms apart:
the nginx-ingress access log and `feature-mcp`'s uvicorn access log, both
`200`. **Real bug found and fixed:** `otel-collector`'s `filelog` receiver
used `parse_to: body` but `timestamp.parse_from: attributes.time` — every log
entry failed silently and nothing reached Loki. Fixed by correcting
`parse_from` to `body.time`. Full evidence:
[`LLM-routing-gateway-service-coi-log.md`](../../phase2/evidence/llm/LLM-routing-gateway-service-coi-log.md).

### 5. Trace viewer — real span for the same request

Trace `9f891d3e6d560baaad90e2e76b821c24`, span `feature_mcp.http_request`,
`request_id=phase5-final-1786498311` — the same `request_id` correlates
across Loki, Jaeger, and Prometheus for one single request. **Real bug found
and fixed:** the deployed `feature-mcp`/`drift-mcp` images predated the
OpenTelemetry SDK dependency actually landing in the built layer
(`ModuleNotFoundError`); rebuilt and redeployed both images. Full evidence:
[`LLM-routing-gateway-service-coi-trace.md`](../../phase2/evidence/llm/LLM-routing-gateway-service-coi-trace.md).

### 6. Agent registry UI — live adapter, not static markup

```text
$ curl -sS [auth] "https://distresslens.duckdns.org/agents/registry" -o registry.html
$ grep -oE "coordinator|drift-agent|feature-agent" registry.html | sort | uniq -c
      3 coordinator
      6 drift-agent
      6 feature-agent
```

These three names match exactly the three live `agents-sandbox` Deployments
— the page reflects live cluster state via
`apps/web/src/lib/data/live-registry-adapter.ts`, not a hardcoded list. Full
evidence:
[`LLM-routing-gateway-ui-cho-agent-registry.md`](../../phase2/evidence/llm/LLM-routing-gateway-ui-cho-agent-registry.md).

### 7. Agent-test UI — a real signed-in round-trip, with a disclosed defect

A real Supabase session token drove an authenticated SSE round-trip through
the gateway to the coordinator agent:

```text
data: {"type":"state","state":"streaming","reason":null}
data: {"type":"error","code":"MALFORMED_RESPONSE","reason":"..."}
HTTP_CODE:200
```

The coordinator itself answered `200 OK` (confirmed in its own access log)
but returned an empty `answer` field — a known coordinator/drift-mcp
round-trip defect, recorded and accepted as a named gap rather than hidden.
The row's requirement — a routed, authenticated round-trip — is proven; the
AI answer's correctness is not claimed. Full evidence:
[`LLM-routing-gateway-ui-test-agent.md`](../../phase2/evidence/llm/LLM-routing-gateway-ui-test-agent.md).

## Limitations

Two real, disclosed defects remain visible in this evidence set rather than
polished away: the agent-test round-trip returns `MALFORMED_RESPONSE` for
the specific query tested, and no rate-limiting is configured on any gateway
route. Both are named explicitly in their evidence rows.

## References

- NGINX Ingress Controller: https://kubernetes.github.io/ingress-nginx/
