# Evidence — Feature agent sandbox

- rubric_id: LLM-web-api-k-o-d-li-u-user-agent-ch-y-trong-sandbox-m-b-o
- execution_timestamp: 2026-08-10T05:06:00+00:00
- source_sha: 6ee3175073333df7ed3ed6737bc6c2ac65e6a0a8
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: GKE Calico NetworkPolicy, restricted Pod Security, tokenless ServiceAccount
- command: `kubectl exec sandbox-negative-probe -n agents-sandbox -- sh -c 'test -f /var/run/secrets/kubernetes.io/serviceaccount/token'` plus metadata/DNS/direct-model/filesystem negatives
- expected_result: agent workload runs non-root, read-only, tokenless, default-deny with only scoped MCP/gateway egress
- actual_result: token file absent; metadata request timed out; arbitrary DNS timed out; direct model bypass timed out; `touch /x` failed read-only; feature readiness became green only after gateway dependency recovered
- redaction_status: reviewed — no token, credentials, or private IPs recorded
