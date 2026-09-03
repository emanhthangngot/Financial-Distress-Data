# Brainstorm review: target architecture + rebuild plan, production readiness

Date: 2026-08-21
Scope: excalidraw target diagram (live canvas, 459 elements) + `plans/260818-0832-rebuild-unified-ml-and-llm-platform/`
Mode: exploration only — no plan or diagram mutated.

## Contract

- **Outcome:** evidence-backed verdict on (a) whether the target setup is production-grade, (b) whether the plan is complete, (c) remaining concerns.
- **Constraints:** CPU-only (`GPUS_ALL_REGIONS`=0), 48 vCPU quota target, ~USD 223 credit to 2026-11-06, three rubrics / 161 rows, locked-decision table not relitigated without new evidence.
- **Non-goals:** editing the plan, redrawing the diagram, implementing anything.
- **Acceptance:** every claim carries a source (upstream doc or `file:line`).

## Verdict 1 — is the setup production-grade?

**Yes as a reference-grade MLOps topology; no as a production service.** The component
set, the GitOps-only deployment path, mesh mTLS + `AuthorizationPolicy`, Vault+ESO,
holdout-gated promotion, progressive delivery with an analysis gate and OTel-based
tracing are all what a real platform looks like. What is missing is the operational
half that no rubric row scores:

| Absent | Evidence |
|---|---|
| Backup / restore / DR for Postgres, MinIO, Vault, MLflow | grep across all phase files: `backup`, `disaster` = 0 hits; only `restore` appears (phase 4, meaning PVC survival across hibernate) |
| Runbooks, on-call, alerting policy (alerts, not dashboards) | `runbook`, `oncall` = 0 hits |
| SLOs as burn-rate alerts | `slo` appears in phases 2 and 5 as latency targets, never as an alerting contract |
| NetworkPolicy beyond the agent sandbox | `networkpolicy` only in phase 6 |
| Vault single-node, auto-unseal via KMS, no HA / no rotation policy | phase-04 step 7 |
| Postgres single instance carrying `ops`, `ml`, Iceberg REST catalog, Feast offline store, DataHub and (phase 9) the web app | phase 4 + phase 9 |

That last row is the real single point of failure: one Postgres is simultaneously the
lakehouse catalog, the feature store's offline half, the governance store and the app
database. Acceptable for coursework, not for production. Worth one sentence in the
write-up rather than a rebuild.

## Verdict 2 — is the plan complete?

Close, and unusually rigorous — the immature-label `NULL` rule, the frozen holdout, the
`label_horizon` single-source rule, the DataHub Kafka-emitter decision and the
Job-completion gate are all failure modes that normally get discovered mid-execution.
Four defects remain, three of them blocking.

### B1 (blocking) — `LLMInferenceService` needs Gateway API, which the plan forbids

KServe's llmisvc docs list the required dependencies: **Gateway API v1.2.1, Gateway API
Inference Extension (GIE) v0.3.0, Envoy Gateway v1.2.4 (default provider),
LeaderWorkerSet v0.6.2**. Knative is explicitly *not* a dependency; routing is
`Gateway`+`HTTPRoute`.

The plan installs none of them. `phase-04:36,131` installs the `llmisvc` controller
under Knative Serving with `net-istio` and assumes that is sufficient. Meanwhile
`plan.md:325-331` rules out Gateway API entirely ("a second edge splits TLS, auth and
rate limiting across two data planes") and mandates `trafficRouting.nginx` for **both**
tracks. As written, the LLM half of the serving stack cannot be installed.

The live diagram is the artifact that is *right* here — its label
`"commit: canaryTrafficPercent 10→25→50 + llm HTTPRoute weight"` matches the real
mechanism; the plan's review item 2 does not.

Cheapest fix: keep one NGINX Ingress as the only `LoadBalancer`, and use **Istio as the
Gateway API provider** (already installed mesh-wide) instead of Envoy Gateway, with the
`Gateway` as `ClusterIP` behind NGINX. Costs one `GatewayClass`, GIE and LWS; avoids a
second Envoy data plane. Add GIE + LWS to the capacity budget — neither appears in it.

### B2 (blocking) — Argo Rollouts cannot own a KServe workload

`phase-05:39-40` requires the ML A/B to be an Argo Rollouts canary with
`trafficRouting.nginx`. Argo Rollouts drives pods through a `Rollout` (or `workloadRef`
to a Pod-template workload, documented as Deployment). A KServe `InferenceService` in
serverless mode is a Knative Service whose Deployment is owned by the Knative
controller; Rollouts has nothing it can own. KServe's own canary is
`canaryTrafficPercent`, and its docs state canary is **only supported in serverless
deployment mode** — RawDeployment cannot do it either.

So exactly one of these is true, and the plan has to pick:

1. **KServe-native canary** (`canaryTrafficPercent`, serverless) + the analysis gate
   driven from Jenkins/Prometheus. Matches the diagram, matches the rubric wording
   ("Inference Engine ví dụ KServe"), loses the Argo Rollouts row's mechanism.
2. **Argo Rollouts owns plain Deployments** running Triton directly, no KServe in the
   serving path for the A/B models. Keeps Rollouts + `AnalysisTemplate`, weakens the
   KServe row.
3. Both, on different services — Rollouts on `feature-api`/`drift-api`/web (real
   Deployments), KServe-native canary on the models. **Recommended**: every rubric row
   keeps a real mechanism and nothing is claimed that cannot be demonstrated.

`phase-04:74` compounds it by stating Rollouts uses Istio `VirtualService` for canary
weights, contradicting `plan.md:326-331` (NGINX annotation) and `phase-05:40`. Three
documents, three routers.

### B3 (blocking, cost-of-being-wrong) — the CPU LLM bet has thinner cover than stated

vLLM's own documentation says it is "not intended for CPU-based inference and has not
been optimized for CPU performance", and llm-d/`LLMInferenceService` is GPU-centric
throughout its docs (the quick example requests `nvidia.com/gpu: "1"`). The plan's
fallback — `phase-04:133`, "switch the backend to an OpenAI-compatible llama.cpp server
behind the same `LLMInferenceService`" — assumes llama.cpp slots into llmisvc. There is
no shipped llama.cpp ServingRuntime: KServe issue #5334 (April 2026) is a *proposal*.
A realistic fallback is llama.cpp behind a plain `InferenceService` with a custom
ServingRuntime, which drops llm-d — and with it KV-cache-aware routing, the plan's
headline LLM optimization evidence.

Consequence: phase 4 step 11 is not a "benchmark and decide" step, it is a **fork
between two architectures**, and the fallback branch loses a rubric row. Budget a day
for it and write the fallback's evidence story now, not at phase 6.

### B4 (non-blocking) — stale ambient text

`phase-04:141` justifies the OTel Collector with "Istio **ambient** emits L4 per-hop
spans only". Decision 9 moved to mesh-wide sidecars; the conclusion (application
instrumentation is required for real traces) still holds, the premise is stale.
`plan.md:94` likewise still calls the A/B mechanism `VirtualService`.

## Verdict 3 — remaining concerns

1. **Schedule has zero slack.** Credit expires 2026-11-06 = 77 days from today. The plan
   is 10 weeks = 70 days and every phase is still `todo`/`pending`. Three days of the
   buffer are already spent. Any one of the Vault migration, the Jenkins cutover or the
   B1/B2 forks can eat the remaining week.
2. **Capacity budget omits the Gateway API stack** (GIE, LWS, and a gateway provider),
   and `plan.md` already admits everything-resident is 34-51 vCPU against 48.
3. **Diagram vs plan drift** (separate report earlier this session): DataHub, Debezium,
   schema registry, Flink, Redis, Vault, Kiali, `inference_log` and the guardrail hop
   have no text on the canvas, and 27 of 47 logos carry no adjacent label — which by the
   plan's own rule ("Diagram labels are evidence", `plan.md:341-349`) scores nothing.
4. **DataHub is windowed but lineage is emitted continuously.** The Kafka-emitter
   decision solves this correctly; make sure topic retention outlives the longest
   DataHub down-window, or lineage still evaporates.

## Recommendation

Do not re-open the locked stack. Amend three things before phase 4 starts:

1. Resolve the router question once, in `plan.md`, and propagate to `phase-04:74` and
   `phase-05:40` — recommended split in B2 option 3.
2. Add the Gateway API + GIE + LWS dependency (Istio as provider) to phase 4 and to the
   capacity table; restate `plan.md:325-331` as "one **LoadBalancer**", not "no Gateway
   API".
3. Make phase 4 step 11 an explicit architecture fork with a written fallback evidence
   story, not a benchmark.

## Unresolved questions

- Which B2 option does the user want? It changes phase 5 and phase 7 acceptance criteria.
- Is losing KV-cache-aware routing acceptable if vLLM CPU fails the phase-4 benchmark, or
  should the LLM optimization row be re-based on quantization alone from the start?
- Should the target diagram be exported into `images/architecture/` and tracked, so
  `tests/test_deployment_diagram_assets.py` covers it?

## Sources

- https://kserve.github.io/website/docs/model-serving/generative-inference/llmisvc/llmisvc-dependencies
- https://kserve.github.io/website/docs/model-serving/generative-inference/llmisvc/llmisvc-overview
- https://kserve.github.io/website/docs/model-serving/predictive-inference/rollout-strategies/canary
- https://argo-rollouts.readthedocs.io/en/stable/features/specification/
- https://github.com/kserve/kserve/issues/5334
- https://docs.vllm.ai/en/stable/deployment/integrations/kserve/
- https://istio.io/latest/blog/2023/native-sidecars/
