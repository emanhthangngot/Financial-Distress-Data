# Redaction convention — synthetic template (Phase 1, step 7)

Proves the redaction convention passes `_audit_all_evidence_bodies`
(`scripts/audit_phase2_evidence.py:753-770`) before any real gateway capture.
Not a scored evidence file — kept here as the phase-5 capture template.

## Substitutions

Described without reproducing the raw trigger shape (this table itself must
also pass the denylist — the real values live only in the out-of-band
credential channel, never in a committed file):

| Raw form | Redacted form |
|---|---|
| the retained gateway ingress IPv4 address | `<INGRESS_IP>` |
| the GCP project ID | `<GCP_PROJECT>` |
| the HTTP auth-scheme request header and its value (scheme name, then a colon, then the credential) | drop the whole line, note `redaction_status: <that header>-header line removed` |
| curl's single-letter or long-form basic-auth flag followed by a credential | drop the flag and its argument entirely from the command shown |
| a URL with username and password embedded before the host (`scheme://` + credential + `@` + host) | rewrite as `scheme://<REDACTED>@host` |
| an htpasswd bcrypt hash (`$2` + a version letter + `$` + cost + `$` + a 53-char salt/hash) | `$2b$<REDACTED>` (cost and hash dropped, not just cost) |

## Synthetic capture (redacted, matches the shape phase 5 will produce)

- rubric_id: SYNTHETIC-redaction-template (not a real rubric_id — do not audit as scored)
- execution_timestamp: 2026-08-11T17:00:00+00:00
- source_sha: ddbcbe7bd41ae4883954b8a247efdc67c7329078
- gitops_sha: 921bdc1075ef8335e0f509747bd64db2d525f73e
- versions: nginx-ingress f5-nginx 3.7.0, cert-manager 1.15.0
- command: `curl -sv https://distresslens.duckdns.org/agents/registry` (basic-auth flag and credential supplied out of band, omitted from this reproduction string)
- expected_result: 200 with session cookie when authenticated; 401 with no auth-scheme header
- actual_result: unauthenticated request against the gateway returns 401 and the realm; authenticated request (credential redacted) returns 200
- redaction_status: basic-auth credential dropped from the command shown; the request's auth-scheme header line removed entirely; ingress IP replaced with `<INGRESS_IP>`; GCP project ID replaced with `<GCP_PROJECT>`

## Command output (synthetic, redacted)

Negative case — no credential, hide-services proof (direct pod IP unreachable
from outside the cluster, only the gateway host resolves):

```
$ curl -sv https://distresslens.duckdns.org/agents/registry
*   Trying <INGRESS_IP>:443...
* Connected to distresslens.duckdns.org (<INGRESS_IP>) port 443
> GET /agents/registry HTTP/1.1
> Host: distresslens.duckdns.org
<
< HTTP/1.1 401 Unauthorized
< www-authenticate: Basic realm="FSDS evidence platform"
```

Positive case — basic-auth flag and credential omitted from the shown command
(supplied out of band at capture time):

```
$ curl -sv https://distresslens.duckdns.org/agents/registry
*   Trying <INGRESS_IP>:443...
* Connected to distresslens.duckdns.org (<INGRESS_IP>) port 443
> GET /agents/registry HTTP/1.1
> Host: distresslens.duckdns.org
[auth-scheme request header line removed — see redaction_status]
<
< HTTP/1.1 200 OK
< content-type: text/html
```

Sealed-secret ciphertext (never the source htpasswd line, never a bcrypt
hash — only the SealedSecret's `encryptedData` block is ever committed, and
that block is asymmetric ciphertext, not the credential itself):

```yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata: {name: gateway-basic-auth, namespace: phase2-data}
spec:
  encryptedData:
    htpasswd: AgB3<REDACTED-CIPHERTEXT>
```
