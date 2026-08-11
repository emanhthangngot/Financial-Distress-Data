# Evidence — Feature MCP Helm deployment

- rubric_id: LLM-web-api-k-o-d-li-u-user-in-the-form-of-mcp-tool-to-k8s
- execution_timestamp: 2026-08-10T05:04:00+00:00
- source_sha: 758722c52ef3035a7e3f9464dc03c5a39e50a74e
- gitops_sha: 921bdc1075ef8335e0f509747bd64db2d525f73e
- versions: Helm 3, feature-mcp chart 0.1.0, Artifact Registry immutable digest
- command: `helm upgrade --install feature-mcp charts/feature-mcp -n phase2-data -f apps/dev/feature-mcp/values.yaml --atomic --timeout 5m`
- expected_result: parameterized chart deploys MCP service with rolling update and atomic fallback
- actual_result: healthy revision 6 deployed; prior deliberately bad image revision rolled back atomically to the healthy revision; chart render and rolling update completed without failed requests
- redaction_status: reviewed — image digests are public deployment identifiers, no credentials
