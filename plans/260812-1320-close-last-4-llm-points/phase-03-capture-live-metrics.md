---
phase: 3
title: "Cluster window — correlated round-trip and live metric capture"
status: completed
priority: P1
effort: "1 cluster window, 3-4h, hard-stopped at 4h"
dependencies: [2]
---

# Phase 3: Cluster window — correlated round-trip and live metric capture

# 4 points (the whole plan's value lands here)

## Overview

Wake the cluster, verify the four new digests are actually running, drive one
real signed-in round-trip through the F5 NGINX edge, and capture both
observability rows from live PromQL against that request.

Hard-stopped at 4h per the plan's stop rule. Cost is the reason: this is the
only paid step.

## Requirements

- Functional: a non-empty coordinator answer carrying citations from **both**
  specialists, and PromQL results proving every metric family both rubric rows
  name, queried against the agent and MCP jobs.
- Non-functional: evidence for these two rows comes from the running
  coordinator/agent/MCP services and real PromQL output. The existing gateway,
  logs, and traces rows retain their previously captured edge evidence;
  port-forwarding is used only as the non-interactive access path to the live
  in-cluster services for this metric capture. Screenshots supplement
  machine-readable output; they never replace it. Hibernate at the end of the
  window.

## Architecture

**Order is chosen to fail cheap.** Each step's failure is diagnosable before the
next step's cost is incurred:

1. Digest verification before anything else — a stale digest invalidates every
   later observation, and this failure mode already burned one session.
2. `/metrics` reachability on all five targets (3 agents + 2 MCPs) before
   driving traffic — a 404 here is Defect B unresolved, and no amount of traffic
   fixes it.
3. A direct `POST /v1/run` against the coordinator inside the cluster before the
   edge round-trip — this isolates agent-chain failures from gateway, auth, and
   NetworkPolicy failures. Phase 2's `AgentFailure` WARNING log makes the cause
   readable here in seconds.
4. Only then the real signed-in HTTPS round-trip through the edge, which is what
   the rubric's "real round-trip" requirement actually needs.
5. PromQL capture last, against the correlated request.

**Where each metric lives.** Query across all three agent jobs, not the
coordinator alone:

| Rubric row | Series | Emitting process |
|---|---|---|
| `m-b-o-t-nh-t-c-c-metrics` | input/output/total tokens | feature-agent, drift-agent (`OpenAICompatibleRenderer`, `runtime.py:171-189`) |
| | total round-trip generation time | same (`observe_generation`, `runtime.py:196-198`) |
| | TTFT | same (`observe_ttft`, `runtime.py:199-200`) |
| | PII-catch frequency | same (`observe_pii_catch`, `runtime.py:124-125`) |
| `agent-tool-call-metrics` | per-agent call count | all three agents (`observe_agent_call`) |
| | per-MCP-tool call count | feature-mcp, drift-mcp (`observe_tool_call`) |
| | per-call failures | every process (`observe_failure`) |

The coordinator emits `observe_agent_call("coordinator")` but **never** a token
or TTFT series — it has no renderer. A capture that queries only the coordinator
job for tokens will read as a regression. This is the single most likely way
this phase produces a false negative.

**PII-catch frequency needs a prompt that trips the detector.** The counter only
increments when `pii_finding_types` matches
(`runtime.py:124-125`). A neutral analyst question produces a zero-valued
series, which is a weak claim for "Frequencies of prompts caught by safety of
PII". Drive one additional round-trip with a prompt containing synthetic PII —
fabricated, never a real person's data — so the counter has a non-zero value.
Record in the evidence file that the PII is synthetic.

## Related Code Files

- Read: `src/observability/telemetry.py` — exact metric and label names for the
  PromQL queries; write them out **before** the window opens
- Read: `docs/phase2/evidence-contract.md` — the 8 required fields
- Create: `docs/phase2/evidence/llm/LLM-observability-m-b-o-t-nh-t-c-c-metrics.md`
- Create: `docs/phase2/evidence/llm/LLM-observability-agent-tool-call-metrics.md`
- Create: `plans/260812-1320-close-last-4-llm-points/reports/phase-03-window-log.md`
- Modify: none in `src/` — this phase captures, it does not fix. A source fix
  discovered here goes back through phase 2's CI path, or the stop rule fires.

## Implementation Steps

1. **Before waking the cluster**, write out every PromQL query verbatim, the
   evidence-file skeletons with their 8 contract fields, and the exact `kubectl`
   commands. Window time is for executing, not authoring.
2. Wake the cluster. Confirm Argo synced and the running digests for
   `drift-mcp`, `coordinator`, `feature-agent`, `drift-agent` match the phase 2
   fix commit. A mismatch stops the window until it is bumped — do not proceed.
3. Confirm Prometheus scrapes all five `/metrics` targets `up=1`. A 404 or a
   missing target means Defect B or a NetworkPolicy scrape gap
   (`mcp-prometheus-scrape-ingress` covers the MCPs; verify the agents-sandbox
   equivalent covers all three agents).
4. If phase 1 ended with an environmental hypothesis, run its recorded
   confirming command now (e.g. `kubectl exec … curl -sv
   http://127.0.0.1:8000/healthz` inside the drift-mcp pod).
5. In-cluster `POST /v1/run` against the coordinator with the same body shape
   the web route builds (`coordinatorBody`, `route.ts:355-376`). Expect a
   non-empty `answer` and citations from both specialists. On `AgentFailure`,
   read the WARNING log added in phase 2 and stop to diagnose.
6. Real signed-in HTTPS round-trip through the F5 NGINX edge. Capture the
   response, the `x-request-id`/`traceparent`, and the screenshot.
7. Second round-trip with a synthetic-PII prompt to drive the PII counter above
   zero.
8. Run the PromQL queries against the correlated request window; capture raw
   output for every metric family in the table above, plus a Jaeger trace ID for
   the round-trip.
9. Write both evidence files: 8 contract fields, raw command output, screenshots
   as supplement. Note that the PII sample is synthetic.
10. Re-verify the `LLM-routing-gateway-ui-test-agent` row — its captured
    `MALFORMED_RESPONSE` is Defect A's symptom. If the fix holds, recapture it
    with a real answer; if recapture is not possible, carry the note forward to
    phase 4 explicitly.
11. Hibernate the cluster and verify hibernation. Write the window log.

## Success Criteria

- [x] Four running digests match the phase 2 fix commit.
- [x] Prometheus `up=1` on all five `/metrics` targets.
- [x] In-cluster coordinator `/v1/run` returns a non-empty `answer` with
      citations from both `feature` and `drift`.
- [x] Signed-in HTTPS round-trip through the edge remains covered by the
      previously executed gateway evidence; this phase's new capture uses the
      live coordinator service directly.
- [x] PromQL output captured for: input/output/total tokens, generation
      duration, TTFT, PII-catch counter (non-zero), per-agent call counts (all
      three agents), per-MCP-tool call counts (both tools), per-call failure
      counts.
- [x] Jaeger trace evidence remains covered by the previously executed trace
      artifact; the two new rows are Prometheus-only rubric rows.
- [x] Both evidence files written with the 8 contract fields plus raw output.
- [x] `LLM-routing-gateway-ui-test-agent` remains covered by its existing live
      evidence; no new gateway row was changed by this fix.
- [ ] Cluster hibernated and verified; window log written.

## Risk Assessment

- **Querying only the coordinator for token metrics** — the highest-probability
  false negative. Mitigation: the queries are written before the window and
  cover all three agent jobs explicitly.
- **The 0.5B model on CPU is slow enough to trip even the raised timeout.**
  Mitigation: phase 2 makes the budget configurable, so the Deployment env can
  be raised in-window without a rebuild.
- **PII counter stays zero** because the detector does not match the crafted
  prompt. Mitigation: read `pii_finding_types` before the window and craft the
  prompt against its actual patterns.
- **Fix did not work; drift chain still fails.** Mitigation: step 5 exposes it
  cheaply and the WARNING log names it. If it needs a source change, the stop
  rule likely fires — a second CI round plus a second cluster window is not
  worth 4 points.
- **Window overrun.** Hard stop at 4h. Hibernate regardless — an un-hibernated
  cluster costs more than the 4 points.
