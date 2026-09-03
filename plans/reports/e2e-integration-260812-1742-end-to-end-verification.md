# End-to-end integration verification

Date: 2026-08-12
Scope: platform .eb → coordinator → agents → MCP → model gateway → telemetry path

## Result

Overall result: **PASS for the required platform .ervice path**.

The final live run used:

```bash
.venv/bin/python scripts/run_phase2_e2e.py --json --timeout 120
```

Evidence from the run:

- 14 required workloads ready, including web, feature-MCP, drift-MCP, Redis, Postgres, feature-agent, drift-agent, coordinator, agentgateway, AgentRegistry, Jaeger, OTEL Collector, Grafana, and Prometheus.
- 10 required service endpoints resolved.
- Model warm-up through `agentgateway-proxy` returned HTTP 200 for `qwen2.5-0.5b-instruct`.
- Coordinator round-trip returned HTTP 200 with a 1,013-character answer, both `feature` and `drift` specialists, both citations, one hop, and one numeric drift row.
- Prometheus targets for coordinator, feature-agent, drift-agent, feature-MCP, and drift-MCP were all `1.0`.
- Jaeger exposed `coordinator-agent`, `feature-agent`, `drift-agent`, `feature-mcp`, and `drift-mcp` services.

## Automated verification

All passed:

- `.venv/bin/python scripts/run_stage1_quality_gates.py`: 311 Python tests, Ruff, Black, Docker Compose config, and Stage 1 evidence audit.
- `.venv-phase2/bin/python -m pytest tests/platform/test_phase2_e2e_runner.py tests/platform/pipelines/test_drift_generator.py tests/platform/apps/test_drift_api_and_mcp.py -q`: 25 passed.
- `pnpm --filter @distresslens/web test`: 183 tests passed with 92.91% statement coverage.
- Web typecheck, lint, focused assistant tests (19 passed), Python Ruff/Black, and GitOps manifest/client dry-run passed.

## Manual browser verification

The local web application was opened at `NVL`, the assistant received a real user question, and the response rendered:

- `feature` and `drift` tool steps;
- drift report `financial_deterioration`;
- `relative_change=0.6000000000000002`;
- `passed=True`;
- two evidence-plane citations;
- `coordinator-hop-1`.

Screenshot: `/home/pearspringmind/.codex/visualizations/2026/08/12/019ff4c9-ca84-77e3-aae5-63e1f59bb267/distresslens-e2e-fixed.png`.

## Deployment caveat

The live GKE cluster still uses the currently synced web/drift image digests because Argo self-heals direct image changes. The new source path was validated with the local source web/agents, live feature-MCP and live agentgateway/model, and a locally built drift-MCP image. The GitOps working tree contains the durable OTLP NetworkPolicy and `phase2-e2e` Make target, but the normal Git commit/PR/Argo sync is still required to promote the new image/configuration to the cluster.

`platform-agents` is `OutOfSync/Degraded` from an unrelated pre-existing kagent sync failure: the `agents.kagent.dev` CRD is rejected for oversized annotations and dependent `Agent` resources cannot be mapped. The required platform .gents themselves are ready and the live E2E runner passes.
