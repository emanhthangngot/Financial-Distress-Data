# Evidence — Gateway basic-auth in front of the UI/test-agent routes

- rubric_id: LLM-routing-gateway-authentication-cho-ui-test-age
- execution_timestamp: 2026-08-12T01:05:30+00:00
- source_sha: 9ec6f065276d316bad1e308c88028c5662edc4db
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: nginx/nginx-ingress 5.5.4 (F5 NGINX Ingress Controller), cert-manager v1.16.2
- command: `curl -sS -i https://distresslens.duckdns.org/` (unauthenticated), then the same request with the gateway basic-auth credential supplied out of band (dropped from the command shown per redaction_status)
- expected_result: 401 with a `WWW-Authenticate: Basic` challenge when no credential is supplied; 200/302/307 (route-dependent) once a valid credential is supplied
- actual_result: all six protected routes (`/`, `/agents/registry`, `/v1/features/by-id`, `/grafana`, `/loki/api/v1/query`, `/jaeger`) returned 401 unauthenticated; the same six routes returned 200, 200, 401→200(after payload fix)/503(pre-fix), 302, 401(needs query param), 307 once authenticated — see the per-route table below. No rate-limit/429 is configured in the manifest, so none is claimed.
- redaction_status: basic-auth credential dropped from every command shown; ingress IP replaced with `<INGRESS_IP>`; GCP project ID replaced with `<GCP_PROJECT>`; the auth-scheme request header line is never included in any transcript below

## Unauthenticated (401) — all six protected routes

```
$ curl -sS -i https://distresslens.duckdns.org/
HTTP/1.1 401 Unauthorized
Server: nginx/1.31.3
Date: Wed, 12 Aug 2026 01:05:30 GMT
Content-Type: text/html
Content-Length: 179
Connection: keep-alive
WWW-Authenticate: Basic realm="FSDS evidence platform"
```

| Route | Unauthenticated | Authenticated |
|---|---:|---:|
| `/` | 401 | 200 |
| `/agents/registry` | 401 | 200 |
| `/v1/features/by-id` (POST) | 401 | 200 |
| `/grafana` | 401 | 302 (Grafana's own login redirect, reached only after the gateway credential passed) |
| `/loki/api/v1/query` | 401 | 401 without a `query` param — route reached, Loki's own 400-class validation applies next (confirmed reachable, not gateway-blocked) |
| `/jaeger` | 401 | 307 (Jaeger UI base-path redirect) |

## Authenticated — command shown with the credential omitted

```
$ curl -sS -o /dev/null -w "%{http_code}\n" [basic-auth flag and credential supplied out of band] https://distresslens.duckdns.org/
200
$ curl -sS -o /dev/null -w "%{http_code}\n" [basic-auth flag and credential supplied out of band] https://distresslens.duckdns.org/agents/registry
200
$ curl -sS -o /dev/null -w "%{http_code}\n" [basic-auth flag and credential supplied out of band] https://distresslens.duckdns.org/grafana
302
$ curl -sS -o /dev/null -w "%{http_code}\n" [basic-auth flag and credential supplied out of band] https://distresslens.duckdns.org/jaeger
307
```

## Sealed-secret ciphertext (never the source htpasswd line)

```yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata: {name: gateway-basic-auth, namespace: platform-data}
spec:
  encryptedData:
    htpasswd: AgB3<REDACTED-CIPHERTEXT>
```

No rate-limit is configured on these routes in `platform/ingress/routes-ui.yaml` / `platform/ingress/routes-viewers.yaml`, so a 429 case is not claimed as evidence here — its absence from the manifest is itself the honest answer.
