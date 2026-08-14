# Evidence — Feature Web API served through the gateway

- rubric_id: LLM-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-
- execution_timestamp: 2026-08-12T01:31:51+00:00
- source_sha: 529fc06a0919fb9dab74aeeff43e14d440e1f8d8
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: feature-mcp `sha256:e2218e6d337b1dc1ec04a9a1e132969e9aa91c6adf034e91548a0d4e3d05b440`, Feast 0.65.0, nginx/nginx-ingress 5.5.4
- command: `curl -sS -X POST https://distresslens.duckdns.org/v1/features/by-id -H "Content-Type: application/json" -d '{"user_id":"VNM","feature_names":["stream_market_features:last_price","stream_market_features:event_count_1h"]}'` (basic-auth flag and credential supplied out of band)
- expected_result: 200 with real online-feature values read from the Feast/Redis online store through the gateway, not a static fixture
- actual_result: `HTTP_CODE:200`, body `{"user_id":"VNM","features":{"last_price":72.5,"event_count_1h":42}}` — values match the same keys read directly out of Redis (`GET`-equivalent `HGETALL` on the `ticker=VNM` online-store hash) during root-cause diagnosis, confirming the response is live data, not a stub
- redaction_status: basic-auth credential dropped from the command shown; ingress IP replaced with `<INGRESS_IP>` (not used in this transcript); GCP project ID replaced with `<GCP_PROJECT>` where the image digest's registry path is shown

## Request/response through the gateway

```
$ curl -sS -w "\nHTTP_CODE:%{http_code}\n" [basic-auth flag and credential supplied out of band] \
  -X POST "https://distresslens.duckdns.org/v1/features/by-id" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"VNM","feature_names":["stream_market_features:last_price","stream_market_features:event_count_1h"]}'
{"user_id":"VNM","features":{"last_price":72.5,"event_count_1h":42}}
HTTP_CODE:200
```

## Root-cause note (why this row needed a live fix, not just a route)

The route was already wired (`platform/ingress/routes-ui.yaml`), but the backend itself was broken: `feature-mcp`'s `FEAST_REPO_PATH` env var pointed at the renamed `feature_store.yaml` **file** (`/service/feature_repo/structured/feature_store.cluster.yaml`) instead of its **directory**, so `feast.FeatureStore(repo_path=...)` raised `FileNotFoundError` on every request and the route answered `503 dependency_unavailable`. Fixed in `apps/dev/feature-mcp/values.yaml` (`FEAST_REPO_PATH: /service/feature_repo/structured`), redeployed via Argo, and reverified with the request/response above.
