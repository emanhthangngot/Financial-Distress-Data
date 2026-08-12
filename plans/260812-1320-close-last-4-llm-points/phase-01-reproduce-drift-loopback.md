---
phase: 1
title: "Reproduce and prove the drift-mcp loopback failure"
status: complete
priority: P1
effort: "3h, no cluster, time-boxed"
dependencies: []
---

# Phase 1: Reproduce and prove the drift-mcp loopback failure

# 0 points (unblocks 4)

## Overview

Settle the mechanism of the drift-mcp self-loopback hang locally, before any
source edit, so phase 2 ships a fix that is known to work and phase 3's cluster
window is not spent re-diagnosing.

Time-boxed to 3h. Exceeding the box triggers the plan's stop rule.

## Requirements

- Functional: an executed local reproduction that either (a) hangs the same way
  the cluster does, or (b) succeeds — which proves the cause is environmental
  and forces a named cluster-side hypothesis before phase 2 begins.
- Non-functional: read-only on `src/` and `apps/` — this phase writes no
  production code. Any diagnostic scaffolding lives under the scratchpad or a
  test file, never in a shipped module.

## Architecture

The reproduction target is the exact deployed topology in one process:
`app.main:app` with `mount_mcp=True`, uvicorn on `0.0.0.0:8000`,
`DRIFT_API_BASE_URL=http://127.0.0.1:8000`, `MCP_AUTH_GRANTS` matching the live
pod value `{"drift-agent":["financial-distress:drift"]}`. The call under test is
an MCP `build_realtime_drift_report` invocation with a valid scope, which is the
only path that triggers the self-call.

Container parity matters for two of the four candidate mechanisms (CPU limit,
listen address), so the reproduction runs twice: bare uvicorn first (fast, rules
in/out the pure-async mechanisms), then the built image under
`docker run --cpus 0.5 -m 512m` if bare uvicorn succeeds.

Candidate mechanisms to discriminate, each with its distinguishing signal:

| Hypothesis | Distinguishing signal |
|---|---|
| `httpx.AsyncClient` bound to the parent lifespan's loop/context, used from the mounted sub-app's task group | Bare uvicorn hangs; no access-log line for `/v1/drift/report`; hang is deterministic on the first call |
| Uvicorn/ASGI self-call serialization under `stateless_http=True` | Bare uvicorn hangs; access log shows the request accepted but never completing |
| CPU throttling at the 500m limit | Bare uvicorn succeeds; `docker run --cpus 0.5` exceeds 5s; access-log line **is** present |
| Listen address / port mismatch in the pod | Both local runs succeed; the call fails only in-cluster; `kubectl exec … curl 127.0.0.1:8000/healthz` is the cluster-side check |

The same reproduction is run once against `feature-mcp`, whose identical
loopback shape (`apps/feature-mcp/app/mcp_server.py:220`) was never reported
hanging. If feature-mcp hangs too, the earlier "feature path works" reading was
wrong and the fix must cover both services; if it does not hang, the difference
between the two handlers is itself the strongest lead.

## Related Code Files

- Read: `apps/drift-mcp/app/main.py` (`create_app`, `_calculate_drift`,
  `drift_report`), `apps/drift-mcp/app/mcp_server.py`
  (`HttpxDriftApiClient`, `DriftMcpService._invoke`, `create_mcp_runtime`)
- Read: `apps/feature-mcp/app/mcp_server.py` (comparison)
- Read: `apps/drift-mcp/Dockerfile`,
  `~/Studying/FSDS/financial-distress-gitops/apps/dev/drift-mcp/values.yaml`,
  `~/Studying/FSDS/financial-distress-gitops/platform/data/network-policies.yaml`
- Create (scratchpad only): a probe script that opens an MCP client session
  against the running app and calls the tool once
- Create: `plans/260812-1320-close-last-4-llm-points/reports/phase-01-repro.md`
- Modify: none

## Implementation Steps

1. Capture the exact live pod configuration for drift-mcp — env, container port,
   resource limits, and whether an access-log line exists for
   `/v1/drift/report` in the retained logs. If the cluster is hibernated, use
   the recorded values in `phase-04-window-log.md` item 9 and the GitOps values
   file, and mark the phase-01 report accordingly.
2. Run `app.main:app` under bare uvicorn locally with the live env values.
   Confirm `/healthz` and a direct `POST /v1/drift/report` both work — this
   establishes the route itself is fine.
3. Drive one MCP `build_realtime_drift_report` call with a valid scope from a
   separate process. Record: wall time, whether an access-log line appears for
   the self-call, and the returned `ToolResult`.
4. If step 3 hangs — mechanism is in-process. Discriminate the two in-process
   hypotheses by re-running with `DRIFT_API_BASE_URL` pointed at a **second**
   uvicorn instance of the same app on another port. Success there isolates the
   fault to same-process self-calling; failure there points at the httpx client
   lifecycle instead.
5. If step 3 succeeds — rebuild the image and repeat under
   `docker run --cpus 0.5 -m 512m` to test throttling. If that also succeeds,
   the cause is environmental; write the cluster-side hypothesis and the exact
   `kubectl exec` command that will confirm it in phase 3, and note that phase 2
   ships the loopback removal anyway (it is correct regardless) plus whatever
   the environmental hypothesis requires.
6. Repeat step 3 once against feature-mcp and record whether it hangs.
7. Write the phase-01 report: mechanism (or named exclusion), the evidence for
   it, and the go/no-go against the plan's stop rule.

## Success Criteria

- [ ] Live (or last-recorded) drift-mcp pod config captured verbatim in the
      report.
- [ ] Bare-uvicorn MCP tool call executed; wall time, access-log presence, and
      `ToolResult` recorded.
- [ ] Same-process vs two-process discrimination run (step 4) or containerized
      throttling run (step 5) executed, whichever branch applies.
- [ ] feature-mcp comparison run recorded.
- [ ] Report states one of: proven in-process mechanism / proven container-limit
      mechanism / environmental with a named cluster-side hypothesis and the
      command that will confirm it / **not reproduced and not explained** →
      stop rule fires, plan abandoned at 96/100.
- [ ] No file under `src/` or `apps/` modified by this phase.

## Risk Assessment

- **The cluster is hibernated, so live drift-mcp logs may be gone.** Mitigation:
  the window log already records the decisive observations (no access-log line,
  5s timeout); treat them as the cluster-side facts and say so in the report
  rather than pretending to re-observe them.
- **Local reproduction succeeds and the cause is environmental.** This is a real
  outcome, not a failure — but it moves diagnosis into the paid cluster window.
  Mitigation: step 5 requires the confirming `kubectl exec` command to be
  written down in advance, so phase 3 spends minutes, not hours.
- **Time-box overrun.** 3h box, then the stop rule. Do not extend to "one more
  hypothesis" — the whole plan is worth 4 points.
- **Probe scaffolding leaks into the repo.** Mitigation: scratchpad only; the
  phase's own success criteria assert a clean `src/`/`apps/` diff.
