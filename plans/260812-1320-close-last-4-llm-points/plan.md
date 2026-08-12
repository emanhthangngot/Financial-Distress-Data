---
title: "Close Last 4 LLM Points"
description: "Fix the two defects that block the last 2 LLM observability rows (drift-mcp self-loopback call; three agent Deployments running images without /metrics), capture the two evidence files from a real coordinator round-trip, then hand a zero-cut strict gate to phase 6 of 260811-1627."
status: completed (60/60 LLM rows, 100/100 LLM points, strict zero-cut gate passed)
priority: P1
effort: "1.5 days — 0.5d code+CI (no cluster), 1 cluster window ≈ 3-4h, 0.25d evidence/gate"
branch: codex/phase06-llm-submission
tags: [phase2, llm, evidence, observability, agents, gke]
blockedBy: []
blocks: [260811-1627-close-llm-rubric-to-100]
created: 2026-08-12
---

# Close Last 4 LLM Points

Active phase: **explicit Phase 2**, LLM track only. Read `AGENTS.md`,
`docs/phase2/evidence-contract.md`, and
`plans/260811-1627-close-llm-rubric-to-100/reports/phase-04-window-log.md`
(items 8-10) before starting.

## Overview

At plan start, the LLM track was at **58/60 rows, 96/100 points**. The two
remaining rows were `design_only`, worth 4 points; both are now executed:

| Rubric ID | Points | What it needs |
|---|---|---|
| `LLM-observability-m-b-o-t-nh-t-c-c-metrics` | 2 | input/output/total token counts per request, total round-trip generation time, TTFT, frequency of prompts caught by PII safety |
| `LLM-observability-agent-tool-call-metrics` | 2 | per-agent call count, per-MCP-tool call count, per-call failure count |

**Every metric both rows need is already implemented and unit-tested in
`src/observability/telemetry.py`, and every emit site already exists in
committed source.** Nothing in this plan adds an observability feature. Two
defects stop those emit sites from ever running in the cluster, and one of them
also makes the gateway round-trip return an empty answer.

This plan owns those two defects, the evidence capture that follows, and the
handoff back to `plans/260811-1627-close-llm-rubric-to-100/phase-06`. It does
not redesign the gateway, the observability stack, or the evidence contract —
all three are built, Argo-wired, and (as of phase 5) live.

## The two defects, as measured in source

### Defect A — drift-mcp calls itself over HTTP and the call never lands

`apps/drift-mcp/app/mcp_server.py:193` defaults `DRIFT_API_BASE_URL` to
`http://127.0.0.1:8000`, and the live values file
(`apps/dev/drift-mcp/values.yaml` in the GitOps repo) sets exactly that. So the
MCP tool handler — running inside the `POST /mcp/` request of
`app.main:app` — issues `POST /v1/drift/report` back into **the same uvicorn
worker, same port** (`create_app(mount_mcp=True)` at
`apps/drift-mcp/app/main.py:140-243` serves both surfaces in one process).

Phase 4's window log recorded the live symptom: no access-log line for the
self-call, then `asyncio.wait_for(..., timeout=5.0)`
(`mcp_server.py:122-129`) returns `ToolResult(ok=False, error="timeout")` —
surfaced to the agent as `api_error`/`timeout`.

Consequences, in order:

1. `DriftAgent._run` (`src/agents/drift_agent.py:60-61`) raises `RuntimeError`
   on `ok=false`, **before** it ever calls the model renderer — so drift-agent
   emits no token, TTFT, or PII metric.
2. `Coordinator._coordinate` catches that as `RuntimeError` and returns
   `AgentFailure` (`src/agents/coordinator.py:89-90`).
3. `/v1/run` returns `AgentFailure.model_dump()` with **HTTP 200** and no
   `answer` field (`src/agents/runtime.py:380-391`), so the web route's
   `typeof payload.answer !== "string"` check fires and emits
   `MALFORMED_RESPONSE`
   (`apps/web/src/app/api/assistant/stream/route.ts:423-426`). That is the
   already-captured `LLM-routing-gateway-ui-test-agent` symptom — same bug, not
   a second one.

**Root cause is not yet proven at the mechanism level.** The code alone does not
explain the hang: `feature-mcp` uses the identical loopback shape
(`apps/feature-mcp/app/mcp_server.py:220`) and was never reported hanging, and a
single-worker async uvicorn normally serves a concurrent self-call fine because
the outer handler is `await`-ing. Candidate mechanisms — an `httpx.AsyncClient`
opened in the parent lifespan but used from the mounted MCP sub-app's task
group; uvicorn connection handling under `stateless_http=True`; CPU throttling
at the 500m limit; a listen-address mismatch — are distinguishable only by
running it. Phase 1 exists to settle that **before** any code is edited.

The fix direction is nonetheless independent of the mechanism and is the one
phase 4 already named: **stop making the loopback call**. A service must not
HTTP-call its own process to reach a pure function that is already imported
into it (`_calculate_drift`, `main.py:130-137`). Removing the hop deletes the
5s timeout, one serialization round-trip, and this entire failure class.
Phase 1 still runs first, because if the local reproduction shows the hang is
environmental (NetworkPolicy, DNS, listen address) the same removal is still
correct but the cluster needs a second fix too — and shipping only the code
change would burn a cluster window discovering that.

### Defect B — three agent Deployments run images built before `/metrics` existed

`src/agents/runtime.py:376-378` serves `/metrics`. The coordinator,
feature-agent and drift-agent pods run images ~17h older than that commit, so
Prometheus scrapes 404. The MCP images (`feature-mcp`, `drift-mcp`) were already
rebuilt and digest-bumped in the previous session; the three agent images were
not.

Cost is smaller than it looks. All three workflows
(`.github/workflows/phase2-agent-{coordinator,feature,drift}.yaml`) trigger on
`paths: src/agents/**`. The Defect A fix touches `src/agents/coordinator.py`
(see phase 2), so a **single push to `dev` fires all three in parallel** — one
CI round, three digest-bump PRs, not three sequential rounds.

### Defect C (found while planning) — coordinator timeout budget is inverted

`Coordinator.timeout_seconds` defaults to `10.0`
(`src/agents/coordinator.py:49`) and `create_app` never overrides it
(`runtime.py:326-331`). Downstream of that 10s ceiling sit an
`HttpSpecialistClient` with a 45s timeout (`runtime.py:254`) and a model
renderer with a 30s timeout (`runtime.py:113`) generating up to 256 tokens from
`qwen2.5-0.5b-instruct` on CPU.

So even with Defect A fixed, a generation slower than 10s makes
`asyncio.wait_for` (`coordinator.py:82-88`) raise `TimeoutError` → `AgentFailure`
→ the same empty-answer `MALFORMED_RESPONSE`. Fixing A without C risks spending
a cluster window to reproduce a near-identical symptom. Both ship together in
phase 2.

## Which defect closes which row

Recording this because the two rows are not symmetric, and it determines what
phase 3 must capture:

- `agent-tool-call-metrics` needs **Defect B** (agent `/metrics` reachable) plus
  a request that reaches all three agents and both MCP tools. Per-call failures
  come from `observe_failure`, which is emitted on every failure path already.
- `m-b-o-t-nh-t-c-c-metrics` needs the model renderer to actually run. That
  renderer lives in the **feature-agent and drift-agent** processes, never the
  coordinator (`runtime.py:308-325`) — the coordinator only fans out over HTTP.
  So token/TTFT/PII series appear on the specialists' `/metrics`, and drift's
  half of them is unreachable until Defect A is fixed.

A capture that queries only the coordinator's `/metrics` for token counts will
find nothing and will look like a regression. Phase 3 queries PromQL across all
three agent jobs.

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | Prove the drift-mcp loopback mechanism by local reproduction before editing code | P1 |
| 2 | Remove the self-loopback and correct the coordinator timeout budget, with tests | P1 |
| 3 | Ship drift-mcp + 3 agent images through CI and digest-bump GitOps | P1 |
| 4 | Capture a real correlated coordinator round-trip and both evidence files from live PromQL | P1 |
| 5 | Register both rows executed, regenerate the matrix, pass the strict gate with `--accept-design-only` empty | P1 |
| 6 | Hand off to `260811-1627` phase 6 with 60/60 rows and 100/100 points | P1 |

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Reproduce and prove the drift-mcp loopback failure](./phase-01-reproduce-drift-loopback.md) | Complete — local reproduction succeeded; cluster mechanism remains unresolved |
| 2 | [Fix the loopback and the coordinator timeout budget, ship through CI](./phase-02-fix-and-ship-images.md) | Complete — source tests, CI images, signed digests, and GitOps rollout verified |
| 3 | [Cluster window — correlated round-trip and live metric capture](./phase-03-capture-live-metrics.md) | Complete — live coordinator response and aggregate Prometheus metrics captured |
| 4 | [Register rows, regenerate matrix, zero-cut strict gate](./phase-04-close-rows-and-gate.md) | Complete — 60/60 rows, LLM 100/100, no design-only cuts |

## Non-goals

- No new observability feature, metric, exporter, or dashboard. Every series
  both rows need already exists in `src/observability/telemetry.py`.
- No change to Phase 1 code, DAGs, or pipelines (`AGENTS.md` "Don't Touch").
- No AWS/EKS/Argo asset added to this repo — platform changes land in
  `financial-distress-gitops`.
- No rewrite of an evidence claim to match observed reality. If a row cannot be
  captured, it stays `design_only` and gets named in `--accept-design-only` and
  in `docs/submission/README.md` (see the stop rule below).
- No `--amend` on any commit after evidence stamping.

## The fallback rule (not taken)

This plan was worth 4 points and cost one cluster window. It would have been
abandoned, not extended, if any of these had held:

- Phase 1 cannot reproduce the hang locally **and** cannot name a concrete
  cluster-side cause within its 3h box.
- Phase 3's cluster window passes 4h without a successful coordinator
  round-trip.
- Any fix would require editing a Phase 1 DAG, a pipeline, or an evidence file's
  claim.

On abandonment, the fallback would have been to revert nothing that already
passed CI, keep the two rows in
`--accept-design-only`, record the reason in `docs/submission/README.md`, and go
straight to `260811-1627` phase 6 at 96/100. A submitted 96 beats an unsubmitted
100.

## Success Criteria

- [x] Local reproduction (or a written, evidence-backed exclusion) names the
      drift-mcp loopback mechanism before any source edit — phase 1.
- [x] `pytest tests -k "drift_mcp or coordinator"` green, then full
      `.venv/bin/python -m pytest tests` green, plus
      `scripts/run_stage1_quality_gates.py` exit 0 — phase 2.
- [x] `drift-mcp`, `coordinator`, `feature-agent`, `drift-agent` all running
      digests built from the fix commit; all four `/metrics` return 200 to
      Prometheus — phase 2/3.
- [x] One signed-in HTTPS round-trip through the F5 NGINX edge returns a
      non-empty `answer` with citations from **both** specialists — phase 3.
- [x] Live PromQL shows, for that round-trip: token counts (input/output/total),
      generation duration, TTFT, PII-catch counter, per-agent call counts,
      per-MCP-tool call counts, per-call failure counts — phase 3.
- [x] Both evidence files written with the 8 contract fields plus raw command
      output; both rubric IDs added to `EXECUTED_RUBRIC_IDS`
      (`scripts/_phase2_rubric_items.py:1159`); matrix regenerated — phase 4.
- [x] Strict two-repo gate exits 0 with **no** `--accept-design-only` argument,
      60/60 rows, LLM 100/100 — phase 4.
- [x] `plans/260811-1627-close-llm-rubric-to-100/phase-06` unblocked, with the
      `LLM-routing-gateway-ui-test-agent` `MALFORMED_RESPONSE` note resolved or
      explicitly carried forward — phase 4.

<!-- slug: close-last-4-llm-points -->
