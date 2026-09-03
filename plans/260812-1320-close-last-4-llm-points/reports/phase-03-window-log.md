# Phase 3 Window Log — Live LLM Observability Capture

Date: 2026-08-12 08:34 UTC  
Plan: `260812-1320-close-last-4-llm-points`  
Scope: final two LLM observability rows

## Result

The live cluster window recovered the final four LLM points. The coordinator
returned HTTP 200 with a non-empty answer, two citations, and both specialists
(`feature`, `drift`). Prometheus reported all five service targets as `up=1` and
returned the required agent, MCP-tool, token, generation, TTFT, PII, and
failure series.

The exact machine-readable evidence is in:

- `docs/platform/evidence/llm/LLM-observability-m-b-o-t-nh-t-c-c-metrics.md`
- `docs/platform/evidence/llm/LLM-observability-agent-tool-call-metrics.md`

## Live checks

| Check | Observed result |
|---|---|
| Running images | coordinator, feature-agent, drift-agent, and drift-mcp matched the immutable Artifact Registry digests from the merged GitOps revision |
| Metrics scrape | `coordinator=1`, `feature-agent=1`, `drift-agent=1`, `feature-mcp=1`, `drift-mcp=1` |
| Coordinator request | `status=200`, `answer_present=true`, `citation_count=2`, `specialists=[drift, feature]`, `hops_used=1` |
| Per-request model metrics | feature and drift emitted input/output/total tokens, generation round-trip seconds, TTFT seconds, and `email` PII catches |
| Agent/tool metrics | all three agent call series and both MCP tool series present; per-operation invocation failure recording rule present |

## Scenario

The live request used the valid `stream_market_features:last_price` feature
view and synthetic rows `AAA`/`BBB` for the `market_stress` scenario. The
question included `analyst@example.test`, a synthetic email that matched the
runtime PII detector. No real personal data was used.

## Notes

The first probe in this window returned HTTP 500 because it sent specialist
fields at the coordinator top level. Coordinator logs identified the exact
Pydantic contract error (`feature_request` and `drift_request` are required).
That failed validation probe is not used as evidence. The following nested
payload was accepted and produced the successful capture above.

The live service was accessed through local port-forwards solely to issue the
non-interactive request and query Prometheus; the Prometheus data came from
running pods, not fixtures or local test doubles. Existing gateway, Loki, and
Jaeger artifacts remain the evidence for their already-executed rows.

## Acceptance status

- [x] Live coordinator round-trip with both specialists.
- [x] All five service metrics targets healthy.
- [x] Token, generation, TTFT, and PII metrics captured.
- [x] Agent, MCP-tool, and failure metrics captured.
- [x] Two evidence artifacts satisfy the eight-field contract.
- [x] Rows registered and matrix regenerated to 60/60 LLM rows and 100/100 points.
- [ ] Cluster hibernation is the final operational cleanup step after the strict gate.
