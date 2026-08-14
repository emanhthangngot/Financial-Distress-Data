# Evidence — agent understanding notebook

- rubric_id: LLM-demonstrate-basic-underst-jupyter-notebook-demonstrate-a
- execution_timestamp: 2026-08-11T08:52:37Z
- source_sha: 8adb668c68941be821cae879fac15db60853d96e
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: Python 3.11; mcp streamable-http client; feature-mcp image deployed from the recorded GitOps revision
- command: Port-forward `feature-mcp` and run the code cells in `notebooks/agent-understanding-demo.ipynb` with `DEMO_USER_ID=VNM`, `DEMO_CHUNK_ID=phase3-chunk`, and `DEMO_SCOPE=financial-distress:read`
- expected_result: the specialist agent calls the governed MCP tool and receives structured feature and RAG context without connecting directly to Redis or PostgreSQL
- actual_result: live MCP response returned `ok=true`; the feature payload contained `z_score=null` because no online value was materialized for VNM, while the RAG payload returned chunk `phase3-chunk`, its audited text, source URI, company `VNM`, report date `2026-08-10`, and `access_class=public`
- redaction_status: reviewed — no credentials, project identifiers, node addresses, prompts, or personal data were recorded

## Reproducible output

The committed notebook contains the request identity/scope, MCP tool call, and
the captured structured response. The null online value is retained as the
actual service result rather than replaced with fixture data.
