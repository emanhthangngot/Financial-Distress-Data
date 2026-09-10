---
phase: 12
title: "Phase 12: Observability, 300-point evidence capture, freeze"
status: pending
priority: P1
effort: "8-12 days"
dependencies: ["phase-10-delivery.md", "phase-11-quality-engineering.md"]
owns: ["platform/observability/", "docs/", "scripts/run_unified_evidence_capture.py"]
---

# Phase 12: Observability, incremental evidence and freeze

## Overview

Capture all 161 rubric rows / 300 points with real outputs, traceable revisions and required UI
screenshots. Instrumentation is built early enough for P8/P10; final freeze waits for P10/P11.
No 83-component image parity or always-on observability stack is required. Required metrics/logs/
traces remain. Existing Prometheus/Grafana, Loki, Jaeger and OTel are reused, not replaced by a paid
or duplicate hosted observability platform.

## Requirements and architecture

Instrument selected required services, jobs, models, agents, MCP and APIs. Include request rate,
count and failures; input/output/total token usage and round-trip time; agent/MCP calls and failures;
ML drift and retrain trigger; real model version comparison. TTFT and tokens/s use real token usage
or the exact model tokenizer, never SSE event/line counts. Hosted-only opaque KV-cache metrics are
unavailable, not zeros or invented measurements. Local-serving metrics describe that serving path.

Correlate request_id/trace with principal-scoped session, tool call, provider/model, prompt/corpus
revision, data cutoff and source vintage. Raw session IDs/questions/content and secrets do not go
into high-cardinality public metric labels; use scoped/redacted logs and traces with bounded
retention. Free-provider fallback and throttling are separate outcomes, not successful primary calls.

Evidence manifest per row includes source_sha/gitops_sha, data/model/prompt/corpus/dependency
revisions where applicable, command, runtime (local/Kaggle/Kubernetes/cloud), resource-window ID,
started/finished times, result, artifact hashes and known limitations. A schema listing or kernel
COMPLETE without validated outputs is not an executed assertion. Optional experiment deferral is
not a missing rubric capability and must not fabricate a successful model result.

## Capture ordering

Build an explicit row-level prerequisites graph from the unified matrix and producing ACs. Do not
hardcode guessed point totals by wave or assume all mini rows are available after P4.

1. P2/P3 schema/constraint/docs proof after actual corresponding outputs exist.
2. P4 batch/generator/Spark DP1/DP2 outputs and their governance/lineage proof.
3. P5 Flink/streaming/DP3/Feast outputs, not captured before P5 producers exist.
4. P11 deterministic quality and benchmark reports once their tested artifacts are available.
5. P7/P8/P9/P10 live inference/API/agents/CI/cloud capabilities during approved windows.
6. Final integrated path, consistency audit, only-failed/changed-row repair and freeze.

A row may be captured when its producing ACs pass even if unrelated ACs in the same phase are still
open; final submission requires every owning phase's required ACs. This avoids making early P12
metrics depend on its own final freeze. A failing row records failure and does not erase successful
rows. Final command exits nonzero if any required row is missing/failed/blocked/stale.

## Ownership and implementation

Own `src/observability/telemetry.py`, observability deployments, evidence capture runner and final
human docs. P8 proposes instrumentation events, P10 consumes baseline metrics, P12 integrates early
without concurrent edits. P3 owns matrix/ADR definitions; P12 updates execution fields after proof.

1. Define telemetry names/labels with P8/P10 and deploy the minimal selected stack in an approved window.
2. Verify actual metric samples and end-to-end trace before dashboards; check failure counters too.
3. Implement/update capture runner, per-row prerequisites, failure isolation, `--only-failed` and
   changed-revision invalidation. New commands are planned until implemented, not claimed runnable.
4. Capture required UI screenshots through protected P9 NGINX routes plus raw machine results.
5. Verify selected architecture inventory, rubric counts/owners/ACs and executed evidence; refuse
   local/Kaggle artifacts for rows requiring actual cloud or Kubernetes deployment.
6. Re-run affected row assertions after source/data/model/prompt changes. Retain immutable historical
   evidence and baseline tag; do not copy old numbers under a new SHA.
7. Update README/current architecture/contracts/evidence navigation to actual implementation and
   session-only access instructions. Keep working GitHub Actions/Supabase accurately documented.
8. Freeze checksums/revisions, source and GitOps validation, actual Argo convergence and integrated
   demo results. Export artifacts before session shutdown and verify no residual-cost resources.

## Success criteria

- [ ] AC-P12-1: Prometheus -> scrapes selected required components -> healthy targets and real samples; optional omitted image components not counted as failures.
- [ ] AC-P12-2: Authorized operator -> queries logs through NGINX -> real API/agent/dataflow logs with redacted secrets and scoped retention.
- [ ] AC-P12-3: Authorized operator -> opens trace viewer -> follows one actual analyst -> agent -> MCP -> API -> inference/data call with coherent request correlation.
- [ ] AC-P12-4: Grafana -> displays actual ML/LLM runs -> latency/error/drift and token metrics with model/provider revisions, no invented opaque-cache data.
- [ ] AC-P12-5: Evaluator -> compares token counters with provider usage or exact tokenizer -> input/output/total per-request usage accurate; SSE chunks never treated as tokens.
- [ ] AC-P12-6: Evaluator -> runs successful and failed agent/MCP calls -> call/failure counters and round-trip timing reflect both outcomes.
- [ ] AC-P12-7: Architecture verifier -> checks selected inventory -> required real capabilities present, image-only omissions documented without mandatory component-count parity.
- [ ] AC-P12-8: Rubric verifier -> checks final matrix and artifacts -> 161 rows / 300 points, zero unexecuted required rows, valid owner/AC and attribution for each.
- [ ] AC-P12-9: Capture runner -> executes only ready row prerequisites and then final sweep -> isolated failures retained, stale revisions rejected, no guessed local-wave point total.
- [ ] AC-P12-10: Naming verifier -> scans final active surfaces -> no unintended legacy tokens, historical records and applied migrations preserved.
- [ ] AC-P12-11: Schema evidence builder -> checks real populated outputs -> full grain, temporal intervals, zero forbidden orphans, nullable-FK ceilings and all P2 Gold datasets validated.
- [ ] AC-P12-12: Reviewer -> follows current docs and demo access -> actual architecture, supported states, free-tier/cloud blockers and session schedule accurately described.
- [ ] AC-P12-13: Release operator -> runs full source gate, GitOps checks and integrated demo -> version convergence and evidence hashes verified, no unrelated dirty work falsely attributed to release.
- [ ] AC-P12-COST: Operator -> exports evidence and ends window -> approved persistent evidence retained, remaining resources reconciled and no additional spend assumed away.

## Submission freeze checklist

- [ ] All 161 primary row assertions pass in their required runtime, with screenshots where asked.
- [ ] Source `.venv/bin/python scripts/run_lakehouse_quality_gates.py` and applicable GitOps validation pass.
- [ ] Temporal leakage, session isolation, provider failures and historical corrections exercised.
- [ ] Current source/GitOps/data/model/prompt/corpus revisions match evidence manifests.
- [ ] Cloud Terraform, real VM Ansible, Kubernetes deployment and trusted domain HTTPS proved separately.
- [ ] Human-reviewed eval and optional fine-tuning decision recorded without inflated rubric claims.
- [ ] Baseline tag and prior evidence retained; current artifact hashes sealed before teardown.
- [ ] No 24/7 or image-fidelity claim; blocked cloud/free-tier prerequisites remain visible until resolved.

## Risks

A complete-looking dashboard can hide absent failures or fabricated token counts: compare underlying
samples to real requests. A late final-only telemetry phase deadlocks release validation: deliver the
early interface slice first. A successful subset is not 300 points; final gate rejects missing rows.

## Rubric Citations (phase-03 R-12 closure, appended 2026-09-05)

Every rubric row this phase owns per `docs/rubric-matrix-unified.csv`'s `owning_phase` column, cited so `scripts/verify_rubric_coverage.py` can resolve ownership to an assertion (R-12). Each line names the row's real `rubric_id`, its stated requirement, and its proof artifact/deliverable — the row's own matrix columns, not invented text. Rows whose capability is not yet implemented are forward specs, matching this file's other `AC-P12-*` entries.

- AC-P12-RUBRIC-1: `LLM-observability-agent-tool-call-metrics` — platform_operator -> delivers "Đảm bảo ít nhất các metrics; + total num of times each agent is called; + total num of times each MCP tool is called; + total failures cho m..." -> Capture màn hình thể hiện các data đã được capture, có thể coi trên các dashboard (evidence: `docs/platform/evidence/llm/LLM-observability-agent-tool-call-metrics.md`)
- AC-P12-RUBRIC-2: `LLM-observability-collect-v-visualize-metrics-v-` — platform_operator -> delivers "Collect và visualize metrics với Prometheus + Grafana (hoặc tool tương tự)" -> Capture màn hình thể hiện các data đã được capture, có thể coi trên các dashboard (evidence: `docs/platform/evidence/llm/LLM-observability-collect-v-visualize-metrics-v-.md`)
- AC-P12-RUBRIC-3: `LLM-observability-m-b-o-t-nh-t-c-c-metrics` — platform_operator -> delivers "Đảm bảo ít nhất các metrics; + token metrics (count of input tokens, output tokens and total tokens per req); + total round-trip time for a..." -> Capture màn hình thể hiện các data đã được capture, có thể coi trên các dashboard (evidence: `docs/platform/evidence/llm/LLM-observability-m-b-o-t-nh-t-c-c-metrics.md`)
- AC-P12-RUBRIC-4: `LLM-observability-t-ng-t-cho-logs` — platform_operator -> delivers "Tương tự cho logs" -> Capture màn hình thể hiện các data đã được capture, có thể coi trên các dashboard (evidence: `docs/platform/evidence/llm/LLM-observability-t-ng-t-cho-logs.md`)
- AC-P12-RUBRIC-5: `LLM-observability-t-ng-t-cho-traces` — platform_operator -> delivers "Tương tự cho traces" -> Capture màn hình thể hiện các data đã được capture, có thể coi trên các dashboard (evidence: `docs/platform/evidence/llm/LLM-observability-t-ng-t-cho-traces.md`)
- AC-P12-RUBRIC-6: `LLM-observability-web-api-metrics` — platform_operator -> delivers "Observability — Web API metrics" -> Capture màn hình thể hiện các data đã được capture, có thể coi trên các dashboard (evidence: `docs/platform/evidence/llm/LLM-observability-web-api-metrics.md`)
- AC-P12-RUBRIC-7: `ML-observability-airflow-data-drift-pipeline-to` — data_engineer -> delivers "Airflow data drift pipeline to periodically pull data from offline feature store and compare with groundtruth and update to Grafana dashboar..." -> Capture màn hình thể hiện các data đã được capture, có thể coi trên các dashboard (evidence: `docs/platform/evidence/ml/ML-observability-airflow-data-drift-pipeline-to.md`)
- AC-P12-RUBRIC-8: `ML-observability-collect-v-visualize-metrics-v-` — platform_operator -> delivers "Collect và visualize metrics với Prometheus + Grafana (hoặc tool tương tự)" -> Capture màn hình thể hiện các data đã được capture, có thể coi trên các dashboard (evidence: `docs/platform/evidence/ml/ML-observability-collect-v-visualize-metrics-v-.md`)
- AC-P12-RUBRIC-9: `ML-observability-t-ng-t-cho-logs` — platform_operator -> delivers "Tương tự cho logs" -> Capture màn hình thể hiện các data đã được capture, có thể coi trên các dashboard (evidence: `docs/platform/evidence/ml/ML-observability-t-ng-t-cho-logs.md`)
- AC-P12-RUBRIC-10: `ML-observability-t-ng-t-cho-traces` — platform_operator -> delivers "Tương tự cho traces" -> Capture màn hình thể hiện các data đã được capture, có thể coi trên các dashboard (evidence: `docs/platform/evidence/ml/ML-observability-t-ng-t-cho-traces.md`)
- AC-P12-RUBRIC-11: `ML-observability-trigger-retrain-by-calling-kub` — ml_engineer -> delivers "Trigger retrain by calling Kubeflow API (you can design by adding one step at the end of the Airflow data drift pipeline)" -> Capture màn hình thể hiện các data đã được capture, có thể coi trên các dashboard (evidence: `docs/platform/evidence/ml/ML-observability-trigger-retrain-by-calling-kub.md`)
- AC-P12-RUBRIC-12: `ML-observability-web-api-metrics` — platform_operator -> delivers "Observability — Web API metrics" -> Capture màn hình thể hiện các data đã được capture, có thể coi trên các dashboard (evidence: `docs/platform/evidence/ml/ML-observability-web-api-metrics.md`)
