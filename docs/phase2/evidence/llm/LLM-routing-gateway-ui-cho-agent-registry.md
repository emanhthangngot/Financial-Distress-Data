# Evidence — Agent registry UI through the gateway, live adapter entries

- rubric_id: LLM-routing-gateway-ui-cho-agent-registry
- execution_timestamp: 2026-08-12T01:32:00+00:00
- source_sha: 09640b7ede4848f47be9dd9a1cd11b4d041a7170
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: web `sha256:499464d53abba129d48f4e1cc8b4e32acc37d9404f616badbf0b5eba7e306ae3`, `live-registry-adapter.ts` (server-rendered)
- command: `curl -sS https://distresslens.duckdns.org/agents/registry` (basic-auth flag and credential supplied out of band)
- expected_result: the registry page renders through the gateway, populated by the live registry adapter (`apps/web/src/lib/data/live-registry-adapter.ts`), not a static fixture page
- actual_result: `HTTP_CODE:200`, 61929-byte server-rendered HTML page whose body contains real entries for all three deployed agents: `coordinator` (3 occurrences), `drift-agent` (6), `feature-agent` (6), each with a live `status` field — these names come only from the adapter's runtime registry read, never from the page's static markup
- redaction_status: basic-auth credential dropped from the command shown; the page's rendered `_next/static` asset hashes are build-tool output, not secrets, and are left as-is; ingress IP/GCP project ID do not appear in this transcript

## Request and rendered-content check

```
$ curl -sS [basic-auth flag and credential supplied out of band] \
  "https://distresslens.duckdns.org/agents/registry" -o registry.html
$ wc -c registry.html
61929 registry.html
$ grep -oE "coordinator|drift-agent|feature-agent|status" registry.html | sort | uniq -c
      3 coordinator
      6 drift-agent
      6 feature-agent
      4 status
```

These three agent names match exactly the three `agents-sandbox` Deployments running in the cluster during this window (`coordinator`, `drift-agent`, `feature-agent`), confirming the registry page reflects the live cluster state rather than a hardcoded list.
