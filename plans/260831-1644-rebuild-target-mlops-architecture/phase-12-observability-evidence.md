---
phase: 12
title: "Phase 12: Observability, 300-point evidence capture, freeze"
status: pending
priority: P1
effort: "8-12 days"
dependencies: ["phase-10-delivery.md", "phase-11-quality-engineering.md"]
owns: ["platform/observability/", "docs/", "scripts/run_unified_evidence_capture.py"]
---

# Phase 12: Observability, 300-point evidence capture, freeze

## Overview

Complete the observability stack, capture all 161 rubric rows in a single ordered window, verify the
target architecture against the finished cluster, rewrite the documentation, and freeze.
**This is the submission gate. Resident cost: 3-4 vCPU.**

Observability is **never cut** (plan §Schedule Reality): eight rubric rows and 14 points depend on
logs and traces being collected *and* viewable behind NGINX.

| Rows | Requirement | Points |
|---|---|---|
| ML 46; LLM 50 | Collect and visualize metrics with Prometheus + Grafana | 3 |
| ML 47; LLM 51 | Same for logs | 3 |
| ML 48; LLM 52 | Same for traces | 3 |
| ML 38-39; LLM 41-42 | Log viewer and trace viewer reachable only through NGINX (routing owned by P9) | 8 |
| ML 49-50 | ML telemetry: drift pipeline + Kubeflow retrain trigger (owned by P7) | 2 |
| LLM 53 | Token metrics: input, output and total tokens per request | 2 |
| LLM 54 | Agent metrics: calls per agent, calls per MCP tool | 2 |

## Requirements

- Functional:
  - Prometheus scrapes every target-image component with a metrics endpoint, including Kiali, Trino,
    Superset, MLflow, KFP, Ray, Flink, Kafka and Jenkins.
  - Grafana renders the ML gate (p99, error rate, drift) and the LLM gate (TTFT, tokens/s, KV-cache
    hit) with live data, plus the two-version model dashboard from P7.
  - Loki aggregates logs; Jaeger holds distributed traces; the OpenTelemetry Collector unifies
    ingestion; PushGateway receives the drift DAG's metrics.
  - LLM token metrics and agent/MCP call-count metrics are exported and dashboarded.
  - `scripts/verify_target_architecture.py` exits 0 against the finished cluster.
  - `scripts/verify_rubric_coverage.py` exits 0 — 161 rows, zero `design_only`.
  - `scripts/run_unified_evidence_capture.py` produces an artifact for every one of the 161 rows.
- Non-functional: capture is **incremental** — any completed phase can be captured immediately, and
  the final window only re-captures what changed; the frozen tree is the last write before
  submission; no document may still reference GitHub Actions, Supabase, sealed-secrets, a no-mesh
  runtime, or platform . platform .ocabulary.

## Architecture

```
ns: observability
  Prometheus     scrapes every component with a metrics endpoint
  Grafana        ML gate │ LLM gate │ two-version model │ agent + token metrics
  Loki           log aggregation
  Jaeger         distributed traces
  OTel Collector unified telemetry ingestion
  PushGateway    drift DAG metric push
  Kiali          Istio service-mesh visualization

  all of the above are ClusterIP; NGINX is the only path in (routed in P9)
```

### Capture ordering (plan R-5, corrected 2026-09-02)

`run_unified_evidence_capture.py` runs in dependency order. The 2026-09-01 ordering was
**track-first** (LLM → mini → ML) and asserted mini "depends only on P4 and P2". That is wrong:

| mini rows | Requirement | Real dependency |
|---|---|---|
| 20-24 | Flink baseline / burst / late arrival / other / window — **13 points** | **P5**, not P4 |
| 31-32 | DP3 offline feature table, ingest + validate — 4 points | **P5** |
| 37-38 | DP3 lineage + data contract — 4 points | **P5** |
| 41 | `feat_` tables with `event_timestamp` + `created_timestamp` — 2 points | **P2** + P5 materialization |

Running `--track mini` after P4 would have failed **≥ 25 of its 100 points**.

The ordering is now **runtime-first, not track-first** — capture what does not need a cluster before
the cluster exists, because that decouples 173 of the 300 points from the G0 quota gate:

1. **Wave 1 — local, after P2** (~40 pts): mini 26, 39-43, 44-45; ML 55-56; LLM 58-59.
   Runs on Docker Compose. No GKE, no G0 dependency.
2. **Wave 2 — local, after P4** (~60 pts): mini 4-19, 25, 27-30, 33-36; ML 15-17; LLM 31-33.
3. **Wave 3 — local, after P5** (~30 pts): mini 20-24, 31-32, 37-38; ML 18-21; LLM 38-39.
4. **Wave 4 — local, after P11** (~22 pts): mini 2-3; ML 10-13; LLM 26-29.
5. **Wave 5 — cluster, after P8** (~68 pts): the LLM rows that need serving. These were `executed`
   before the purge, so they are the highest-confidence and highest-risk-of-loss set — capture them
   the moment P8 closes. This bounds R-5.
6. **Wave 6 — cluster, after P7 + P9 + P10** (~80 pts): the ML rows plus the load test. Newly
   executed; most likely to need a re-run.

Per-row error isolation: a failing row records `status=failed` and the sweep continues. The summary
names every failed row so only those are re-run.

`--track` is retained for repair runs, but `--wave` is the primary selector because waves, not
tracks, match the dependency graph.

## Related Code Files

- Restore from archive: `platform/observability/eck-otel-values.yaml`
- Modify: `platform/observability/prometheus-scrape-config.yaml` — add Kiali, Trino, Superset,
  MLflow, KFP, Ray, Flink, Kafka, Jenkins targets
- Modify: `platform/observability/grafana-dashboards.yaml` — ML gate, LLM gate, two-version model,
  token metrics, agent/MCP call metrics
- Create: `platform/observability/pushgateway.yaml`
- Modify: `src/observability/telemetry.py` — token counters and agent/MCP call counters
- Create: `scripts/run_unified_evidence_capture.py`
- Modify: `docs/coursework.md`, `docs/system-architecture.md`, `docs/architecture/target.md`,
  `README.md`, `AGENTS.md`

## Implementation Steps

1. **Namespace and stack** (1 d) — confirm `observability` (renamed in P1); deploy Prometheus,
   Grafana, Loki, Jaeger, the OTel Collector and PushGateway; confirm all are `ClusterIP` behind the
   P9 NGINX routes.
2. **Scrape targets** (2 d) — add Kiali, Trino, Superset, MLflow, KFP, Ray, Flink, Kafka and Jenkins;
   verify each target is `UP`.
3. **LLM and agent telemetry** (1-2 d) — export input/output/total token counts per request, calls
   per agent and calls per MCP tool from `src/observability/telemetry.py`; verify the metric names
   with a Prometheus query before building panels.
4. **Dashboards** (2 d) — ML gate (p99, error rate, drift), LLM gate (TTFT, tokens/s, KV-cache hit),
   the P7 two-version model dashboard, and the token/agent panels — all with live data.
5. **Capture script** (2-3 d) — `run_unified_evidence_capture.py` executes each row's
   `validation_command`, writes the artifact to its `evidence_path`, records pass/fail per row, and
   supports `--track` and `--only-failed` for incremental and repair runs.
6. **Verify the architecture** (1 d) — `scripts/verify_target_architecture.py` against the finished
   cluster; it must exit 0 with every one of the 83 components mapped to a live resource.
7. **Full capture window** (1-2 d) — run the sweep in the track order above; all 161 rows captured;
   zero `design_only`.
8. **Documentation rewrite** (1 d) — `docs/coursework.md`, `docs/system-architecture.md`,
   `docs/architecture/target.md`, `README.md`, `AGENTS.md`. Include the honest gap table: any target
   component not built, and why.
9. **Freeze** (1 d) — `make validate` in the GitOps repository; `scripts/run_quality_gates.py` in
   source; Argo CD SHA convergence; zero uncommitted changes in either repository.

## Success Criteria

- [ ] AC-P12-1 **(ML 46; LLM 50)**: Prometheus → lists scrape targets → every target-image component
      with a metrics endpoint is `UP`, including Kiali, Trino, Superset, MLflow, KFP, Ray, Flink,
      Kafka and Jenkins
- [ ] AC-P12-2 **(ML 47; LLM 51)**: Operator → queries Loki through the NGINX route → returns log
      lines from `api-serving`, `agents` and `dataflow` within the retention window
- [ ] AC-P12-3 **(ML 48; LLM 52)**: Operator → opens Jaeger through the NGINX route → finds a trace
      spanning coordinator → MCP → api-serving → kserve
- [ ] AC-P12-4: Grafana → loads the platform dashboard → renders the ML gate (p99, error rate, drift)
      and the LLM gate (TTFT, tokens/s, KV-cache hit) with live data
- [ ] AC-P12-5 **(LLM 53)**: Prometheus → queries token metrics → input, output and total tokens per
      request are present and non-zero after a served prompt
- [ ] AC-P12-6 **(LLM 54)**: Prometheus → queries agent metrics → total calls per agent and total
      calls per MCP tool are present and increment on an agent invocation
- [ ] AC-P12-7 **(O-1)**: `scripts/verify_target_architecture.py` → runs against the finished
      cluster → exits 0 with all 83 components mapped to a live resource
- [ ] AC-P12-8 **(O-2)**: `scripts/verify_rubric_coverage.py` → runs against the unified matrix →
      exits 0; 161 rows, 300 points, zero `design_only`, every row has an artifact
- [ ] AC-P12-9: `scripts/run_unified_evidence_capture.py` → runs waves 1-6 in order → produces
      artifacts for all 161 rows; waves 1-4 (~152 points) complete **without any cluster resource**;
      the script refuses a row whose `owning_phase` is not marked complete
- [ ] AC-P12-10 **(O-3)**: `scripts/verify_naming_cutover.py` → runs on the frozen tree → exits 0
- [ ] AC-P12-11 **(O-5)**: `scripts/build_schema_evidence.py` → runs against real Gold output →
      every declared FK resolves with zero orphans; every table reports `row_count > 0`; every
      nullable FK column is below its NULL-rate ceiling; all **12** Gold datasets are covered
- [ ] AC-P12-12: Reviewer → reads `docs/coursework.md` and `docs/system-architecture.md` → finds the
      target architecture described with no residual claim of GitHub Actions, Supabase,
      sealed-secrets, a no-mesh runtime, or platform . platform .ocabulary — plus an honest gap table
- [ ] AC-P12-13: GitOps operator → `make validate` passes; `scripts/run_quality_gates.py` passes in
      source; Argo CD shows all Applications `Synced/Healthy`; zero uncommitted changes

## Submission freeze checklist

- [ ] `scripts/verify_target_architecture.py` exits 0
- [ ] `scripts/verify_rubric_coverage.py` exits 0
- [ ] `scripts/verify_naming_cutover.py` exits 0
- [ ] `scripts/run_unified_evidence_capture.py` exits 0; all 161 rows captured; 300 points
- [ ] `scripts/build_schema_evidence.py` exits 0 against real Gold output
- [ ] `make validate` passes in `financial-distress-gitops`
- [ ] `scripts/run_quality_gates.py` passes in source
- [ ] Leakage guard fails on the seeded restatement and passes with the vintage filter
- [ ] No uncommitted changes in either repository
- [ ] Argo CD shows all Applications `Synced/Healthy`

## Risk Assessment

**Risk:** the capture window is reached with phases incomplete (plan R-1). Signal: the 60 % date
passes with less than 30 % slack. Mitigation: capture is incremental and **wave-ordered** — run
`--wave 1` as soon as P2 closes, `--wave 2` after P4, `--wave 3` after P5, `--wave 4` after P11,
`--wave 5` after P8, `--wave 6` last. Waves 1-4 total ~152 points and need no cluster, so they are
immune to a G0 delay. Response: what is captured counts; do not defer everything to one window.

**Risk:** a wave is run before its dependency closes and its rows fail for the wrong reason. Signal:
`--wave 2` reports failures on mini 20-24, which belong to wave 3. Mitigation: the script reads
`owning_phase` from the unified matrix and refuses to run a row whose owning phase is not marked
complete. Response: fix the wave assignment in the matrix, not in the script.

**Risk:** a single row fails and breaks the sweep. Signal: the script exits on the first error.
Mitigation: per-row error isolation with `status=failed` and a summary. Response: re-run with
`--only-failed` after fixing the component.

**Risk:** Grafana panels show no data because of missing metric labels. Signal: empty panels with
`UP` targets. Mitigation: verify every metric name with a Prometheus query before building the panel.
Response: fix the label selectors in the dashboard JSON and re-import.

**Risk:** `make validate` fails on a stale SHA or uncommitted Terraform state. Signal: validation
error at freeze. Mitigation: run the Argo CD SHA convergence check before `make validate`. Response:
bump the stale SHAs and commit before freezing.

**Risk:** the documentation rewrite claims components that were cut. Signal: `docs/` describes a
component that `verify_target_architecture.py` reports missing. Mitigation: AC-P12-12 requires an
honest gap table. Response: move the component into the gap table with its reason — a documented gap
scores better than an undocumented false claim, and it is the same principle applied to ticker reuse
in ADR-017 and to source data in ADR-020.

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
