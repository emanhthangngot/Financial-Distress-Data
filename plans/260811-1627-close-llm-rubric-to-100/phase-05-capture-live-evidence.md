---
phase: 5
title: "Capture the 13 live evidence artifacts"
status: pending
priority: P1
effort: "0.75d (cluster up)"
dependencies: [4]
---

# Phase 5: Capture the 13 live evidence artifacts

# 21 points

## Overview

With the stack live and one correlated scenario already run, capture the 7
Routing & Gateway rows (13 pts) and the 6 Observability rows (8 pts) as
contract-compliant evidence, then flip them in the generator.

## Requirements

- Functional: 13 files at `docs/phase2/evidence/llm/<rubric_id>.md`, each with
  the 8 contract fields, redacted per phase 1's proven template, and backed by raw
  command output; the 13 rows registered as executed against the artifact paths
  and assertion strings phase 1 fixed; matrix and requirement tests regenerated.
- Non-functional: proof comes from the routed, deployed system. Port-forwards,
  `helm template`, and local unit tests close nothing here.

## Architecture

**What each row must prove** — capture the full canonical CSV `requirement`
string recorded in phase 1's report, not a paraphrase:

| rubric_id | Pts | Capture |
|---|---:|---|
| `LLM-routing-gateway-c-c-service-c-n-c-hide-ng-sau-` | 2 | External attempt at a backend address/port fails; the gateway path succeeds |
| `LLM-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-` | 1 | The feature Web API served through the gateway, real request/response |
| `LLM-routing-gateway-ui-test-agent` | 2 | Agent-test UI over HTTPS through the gateway with a real signed-in round-trip |
| `LLM-routing-gateway-ui-cho-agent-registry` | 2 | Registry UI through the gateway, entries from the live registry adapter |
| `LLM-routing-gateway-authentication-cho-ui-test-age` | 2 | 401 without credentials, 200 with; rate-limit/429 if the manifest configures it |
| `LLM-routing-gateway-service-coi-log` | 2 | Log viewer through the gateway showing real application log lines |
| `LLM-routing-gateway-service-coi-trace` | 2 | Trace viewer through the gateway showing a real trace with spans |
| `LLM-observability-collect-v-visualize-metrics-v-` | 1 | Prometheus scraping + a Grafana dashboard rendering live series |
| `LLM-observability-m-b-o-t-nh-t-c-c-metrics` | 2 | Per-request input/output/total tokens, generation round-trip time, **TTFT**, and **PII-catch frequency** (the CSV names all of these) |
| `LLM-observability-agent-tool-call-metrics` | 2 | Per-agent call count, per-MCP-tool call count, per-call failures |
| `LLM-observability-web-api-metrics` | 1 | Web API request rate/latency/status for the feature and drift services |
| `LLM-observability-t-ng-t-cho-logs` | 1 | The same request's lines in Loki, queried live (via Grafana Explore if the raw route was dropped) |
| `LLM-observability-t-ng-t-cho-traces` | 1 | The same request's Jaeger trace, with the trace JSON persisted into the evidence |

**One scenario, one trace ID, seven rows.** The four metric rows plus logs and
traces derive from the single correlated coordinator run of phase 4 step 8. That
trace ID appears verbatim in every one of those evidence files — a cross-file
anchor a grader can check and a static file cannot cheaply fake.

**Jaeger keeps traces in memory** (`jaeger.yaml:17-24`, single replica, no PVC).
Persist the trace JSON (`/jaeger/api/traces/<id>`) into the evidence in the same
step that runs the scenario. A restart between capture steps otherwise loses the
trace that six other files reference.

**Redaction is a hard constraint, not advice.** Use phase 1's proven template:
substitute `<INGRESS_IP>` and `<GCP_PROJECT>`, drop or mangle `Authorization:`
header lines, and keep every base64 run under 200 chars. Run the auditor's body
scan after the **first** file, while the cluster is still up, before writing the
other twelve — a denylist failure discovered after teardown costs a new window.

**Liveness anchors.** Static markdown can imitate any of this, and the automated
gate cannot tell (its `validation_command` only checks file shape and a static
YAML token). Add two anchors that make the claim checkable after teardown: the
served TLS certificate's serial and `notBefore` in the gateway rows, and the
shared trace ID in the correlated rows.

**Flipping** uses the artifact paths and assertion strings fixed in phase 1:
register the 13 IDs in `EXECUTED_RUBRIC_IDS` and `EXECUTED_BEHAVIORAL_ASSERTIONS`
in `scripts/_phase2_rubric_items.py`, then regenerate:

```bash
.venv-phase2/bin/python scripts/generate_phase2_matrix.py
.venv-phase2/bin/python scripts/generate_phase2_requirement_tests.py
```

`tests/phase2/requirements/*` are generator-owned; never hand-edit.

**Gate expectation in this phase.** Run the audit with `--require-executed
--run-validations --track LLM`, but expect frozen-revision errors on rows whose
`gitops_sha` predates this window's GitOps commits — that is the mechanism
described in phase 1, and it clears only after the freeze phase stamps. What must
be clean here: every one of the 60 rows is `executed`, every artifact exists,
every behavioral assertion passes, every validation command passes, and the
denylist reports zero hits.

## Related Code Files

- Create: 13 × `docs/phase2/evidence/llm/<rubric_id>.md` (IDs copied from the CSV)
- Modify: `scripts/_phase2_rubric_items.py` (`EXECUTED_RUBRIC_IDS`, `EXECUTED_BEHAVIORAL_ASSERTIONS`)
- Regenerate: `docs/phase2/rubric-matrix.csv`, `tests/phase2/requirements/test_llm_ac_13_routing.py`, `test_llm_ac_15_observability.py`
- Modify: `docs/submission/routing_gateway.md`, `docs/submission/observability.md`, `docs/phase2/evidence/index.md`

## Implementation Steps

1. Capture one file first — the unauthenticated 401 negative — apply the
   redaction template, and run the auditor's body scan on it. Iterate until zero
   denylist hits. Only then continue.
2. Capture the remaining gateway negatives: 401 on all five protected routes and
   the hide-services proof (external attempt at a backend address fails, gateway
   path succeeds), plus the TLS certificate serial/`notBefore` anchor.
3. Capture the two UI rows through the gateway with a signed-in session: the
   agent-test round-trip and the registry page rendering live-adapter entries.
   Record the underlying response payloads, not only screenshots.
4. Capture the feature Web API through the gateway and the authenticated 200s.
5. From phase 4's correlated run, capture and record: token in/out/total,
   generation round-trip time, TTFT, PII-catch frequency, per-agent and
   per-MCP-tool call counts and failures (PromQL + raw results), the Grafana
   dashboard view, the Loki query result, and the persisted Jaeger trace JSON.
   Every one of these files carries the same trace ID.
6. Write all 13 evidence files: the 8 contract fields, a non-interactive
   reproduction command (curl through the gateway, not "click the UI"), expected
   vs actual, and an accurate redaction status. Rows whose artifact lives in the
   private GitOps repo must not claim `none — public repo`.
7. Register the 13 IDs with their phase-1 assertion strings and regenerate the
   matrix and the two requirement test files.
8. Run the audit as described above; fix any gap by fixing the system and
   re-capturing that scenario atomically. Never soften an `expected_result`.
9. Update `docs/submission/routing_gateway.md`, `observability.md` and
   `docs/phase2/evidence/index.md` to link the new files.
10. Only when every capture is written and re-verified: hibernate — pools to
    zero, evidence VM stopped — and record the closing credit balance for the
    freeze phase to commit.

## Success Criteria

- [ ] Reviewer -> opens each of the 13 files -> all 8 contract fields populated, raw output behind every screenshot, redaction status accurate.
- [ ] Auditor -> runs the body scan over all evidence -> zero denylist hits.
- [ ] Auditor -> runs `--require-executed --run-validations --track LLM` -> 60 executed rows, all artifacts present, all assertions and validation commands passing; only the expected frozen-revision errors remain.
- [ ] Reviewer -> reads the six correlated files -> they cite one identical trace ID, and the traces file contains the persisted trace JSON.
- [ ] Reviewer -> reads the token-metrics file -> it covers tokens, round-trip time, TTFT and PII-catch frequency, matching the canonical CSV requirement.
- [ ] Reviewer -> reads the gateway files -> they cite the served certificate's serial and `notBefore`.
- [ ] Maintainer -> diffs `tests/phase2/requirements/` -> matches generator output exactly.
- [ ] Cost owner -> runs `make gcp-status` -> both pools at 0 nodes, evidence VM stopped.

## Risk Assessment

- **A required series does not exist** (no per-tool counter, no PII-catch metric)
  → the row cannot be honestly claimed. Mitigation: phase 4 step 8 verifies the
  series before capture starts; a missing one is a source fix through CI + Argo
  inside the window, or a named cut.
- **Denylist rejection discovered after teardown** → new window or dishonest
  editing. Mitigation: step 1's single-file dry run.
- **Trace lost to a Jaeger restart** → six files cite an unresolvable ID.
  Mitigation: persist the trace JSON in step 5, immediately.
- **Window ends mid-capture** → temptation to fill the rest from manifests.
  Mitigation: capture order puts negatives and correlated data first; anything
  uncaptured stays `design_only` and is named as a cut.
- **Screenshot-only evidence** → fails the contract. Mitigation: every file
  carries its query and raw result.
- Rollback: a wrong evidence file is replaced atomically by a fresh capture of
  the same scenario; its row returns to `design_only` until the replacement
  exists.
