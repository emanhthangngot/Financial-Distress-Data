# Evidence — Feature agent sandbox

- rubric_id: LLM-web-api-k-o-d-li-u-user-agent-ch-y-trong-sandbox-m-b-o
- execution_timestamp: 2026-08-10T05:06:00+00:00
- source_sha: 2f0d189fb3607bd0d509201869792246202f23b0
- gitops_sha: 6ba77a0464916ee86206b4e63090d5bd4742e048
- versions: GKE Calico NetworkPolicy, restricted Pod Security, tokenless ServiceAccount
- command: `kubectl exec sandbox-negative-probe -n agents-sandbox -- sh -c 'test -f /var/run/secrets/kubernetes.io/serviceaccount/token'` plus metadata/DNS/direct-model/filesystem negatives
- expected_result: agent workload runs non-root, read-only, tokenless, default-deny with only scoped MCP/gateway egress
- actual_result: token file absent; metadata request timed out; arbitrary DNS timed out; direct model bypass timed out; `touch /x` failed read-only; feature readiness became green only after gateway dependency recovered
- redaction_status: reviewed — no token, credentials, or private IPs recorded
