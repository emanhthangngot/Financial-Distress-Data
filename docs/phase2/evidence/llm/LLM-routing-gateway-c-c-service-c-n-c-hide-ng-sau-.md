# Evidence — Backend services hidden behind the gateway

- rubric_id: LLM-routing-gateway-c-c-service-c-n-c-hide-ng-sau-
- execution_timestamp: 2026-08-12T01:29:39+00:00
- source_sha: 84c612de87d289de768c5a67439817c6df520b9a
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: nginx/nginx-ingress 5.5.4, GKE `fsds-evidence` cluster (asia-southeast1-b)
- command: `timeout 8 curl -sS -o /dev/null -w "%{http_code}\n" http://<INGRESS_IP>:80/` against the node's external address on the plain HTTP node port (no `nginx.org/*` Ingress path involved), contrasted with the same-service request through the gateway host
- expected_result: a direct attempt at the backend address/port never reaches the `web` Service (no NodePort/firewall path exists to it); the gateway host succeeds
- actual_result: the direct attempt timed out after 8s with no TCP response (`curl: (28) Operation timed out`) — the node's external IP has no open path to the `web` ClusterIP Service; the same request through `https://distresslens.duckdns.org/` succeeded with `200`
- redaction_status: ingress/node IP replaced with `<INGRESS_IP>`; GCP project ID replaced with `<GCP_PROJECT>`; basic-auth credential omitted from the gateway command shown

## Direct backend attempt — times out, no route exists

```
$ timeout 8 curl -sS -o /dev/null -w "direct-node-ip -> %{http_code} (exit %{exitcode})\n" "http://<INGRESS_IP>:80/"
curl: (28) Operation timed out after 8000 milliseconds with 0 bytes received
```

`web` is a `ClusterIP` Service (`platform/data/network-policies.yaml`); it has no `NodePort`, `LoadBalancer`, or external firewall rule of its own. The only path exposed to `0.0.0.0/0` is the F5 NGINX Ingress Controller's `LoadBalancer` Service, fronting the `web`/`feature-mcp`/`grafana`/`loki`/`jaeger` backends under one host and one TLS certificate.

## Gateway path — succeeds

```
$ curl -sS -o /dev/null -w "%{http_code}\n" [basic-auth flag and credential supplied out of band] https://distresslens.duckdns.org/
200
```

## Ingress annotation proof (the manifest that hides the backend)

`platform/ingress/routes-ui.yaml` sets `nginx.org/use-cluster-ip: "true"` on the mergeable-Ingress routes, and every backend Service referenced there is `ClusterIP`-only — none carries a `LoadBalancer` or `NodePort` of its own.
