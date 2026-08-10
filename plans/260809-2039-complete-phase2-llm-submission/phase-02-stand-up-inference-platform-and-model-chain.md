---
phase: 2
title: "Stand up inference platform and model chain"
status: done (4/5 criteria; hibernation-survival check deferred to end-of-session gcp-down/up)
priority: P1
effort: "1d"
dependencies: [1]
---

# Phase 2: Stand up inference platform and model chain

## Overview

Deploy the generation model server as a KServe `InferenceService` on the Knative
Serving already installed, route it through agentgateway, and create the global
kagent `ModelConfig` every agent will reference. Benchmark it, apply one real
optimization, and record a before/after table.

Rubric rows owned (8 points) — IDs and paths copied verbatim from
`docs/phase2/rubric-matrix.csv`:

| Points | rubric_id | artifact_path (authority) |
|---:|---|---|
| 2 | `LLM-a-llm-inference-platform--llm-inference-platform-setup-c` | gitops `platform/inference/model-server.yaml` — placeholder today |
| 2 | `LLM-a-llm-inference-platform--a-custom-model` | source `src/llm/model_server.py` |
| 2 | `LLM-a-llm-inference-platform--benchmark-model-server-and-opt` | source `src/llm/benchmark.py` |
| 2 | `LLM-1-global-model-config-c-c-1-global-model-config-c-c-agen` | gitops `platform/agents/global-model-config.yaml` — placeholder today |

Note the benchmark harness lives at `src/llm/benchmark.py`, **not**
`scripts/benchmark_model_server.py`, and the custom model server code at
`src/llm/model_server.py`. Those are the paths the generated requirement test
asserts.

## Requirements

- Functional: an OpenAI-compatible chat-completions endpoint served by a KServe
  `InferenceService` on CPU; an agentgateway AI backend route to it; one global
  kagent `ModelConfig` pointing at that backend; a benchmark harness producing
  TTFT, inter-token latency, throughput and memory for baseline and optimized
  configurations.
- Non-functional: deployed only through a GitOps commit reconciled by Argo CD —
  which now actually works, because phase 1 added the Applications that watch
  `platform/agents` and `platform/llm`. The model server is `ClusterIP` behind
  the default-deny NetworkPolicy, whose enforcement phase 1 turned on.

## Architecture

Chain, after the llm-d drop (see below):

```
kagent Agent -> kagent ModelConfig -> agentgateway AI backend
             -> KServe InferenceService (Knative Serving)
             -> vLLM-CPU or llama.cpp, OpenAI-compatible, Qwen2.5 0.5B class
```

**llm-d is dropped.** The unified plan restored it on the assumption of ~43 GB
allocatable; the real cluster is one `e2-standard-8`. Two independent facts
close it: this project's own decision **D-E3** already recorded "No llm-d in
this slice — expose the Knative Route directly", and the pinned KServe v0.14.1
(`platform/inference/VERSIONS.md`) ships no `LLMInferenceService` CRD for it to
attach to. The row's literal text is *"Deploy LLM inference platform + setup
custom model"* and names an agent gateway — KServe on Knative behind
agentgateway satisfies it as written. A request-aware router in front of a
single-replica CPU-served 0.5B model has nothing to schedule.

**Model size follows the phase-1 capacity budget, not ambition.** Start at
Qwen2.5 0.5B. The row asks for a benchmarked custom model server, not
GPU-class throughput, and phases 3-4 must still fit on the same node.

**Model weights get a PVC.** Phase 1 established that no PVC exists anywhere in
the GitOps tree and that the TEI embedding service caches to `emptyDir` with
`min-scale: 0` — so every hibernation cycle re-downloads. Create a PVC-backed
weights volume and a one-shot loader Job here, as a deliverable, not as a hope.

**The embedding path stays separate and untouched.** The TEI `InferenceService`
(`platform/inference/embedding-server.yaml`) serves phase-04's RAG vector
writes. Do not fold generation and embedding into one service.

**The optimization must be measured.** Quantization (Q4_K_M vs FP16), batching,
or KV-cache configuration, with identical prompt set and concurrency across both
runs. A config tweak with no before/after numbers does not score the row.

## Related Code Files

- Create: `src/llm/model_server.py` (the custom OpenAI-compatible server /
  its runtime configuration entrypoint)
- Create: `src/llm/benchmark.py` (TTFT, inter-token latency, throughput, memory;
  reused by phase 5's A/B and warm-up rows)
- Modify (GitOps): `platform/inference/model-server.yaml` (placeholder today →
  real `InferenceService`), `platform/agents/global-model-config.yaml`
  (placeholder today → real kagent `ModelConfig` + agentgateway backend)
- Create (GitOps): `platform/inference/model-weights-pvc.yaml`,
  `platform/inference/model-loader-job.yaml`
- Create: 4 evidence files under `docs/phase2/evidence/llm/`
- Regenerate (never hand-edit): `tests/phase2/requirements/test_llm_ac_01_inference.py`,
  `test_llm_ac_02_model_config.py`

## Implementation Steps

1. `make gcp-up`; record the credit balance. Confirm Knative Serving and the
   KServe controller are `Ready`, and that the phase-1 capacity budget still
   holds with the embedding pod running.
2. Choose the runtime and model within that budget. Create the weights PVC and
   loader Job so the download happens once, not once per session.
3. Commit the `InferenceService` to GitOps; let Argo sync it. Do not hand-apply
   — phase 1 made the Application exist precisely so this is real.
4. Verify the OpenAI-compatible route with a real chat completion. Capture the
   request and response.
5. Create the agentgateway AI backend route, then the global kagent
   `ModelConfig` pointing at it. Add a negative test proving a workload in
   `agents-sandbox` cannot reach the model service directly, bypassing
   agentgateway — with NetworkPolicy now enforced, this negative is meaningful.
6. Run the baseline benchmark via `src/llm/benchmark.py`: TTFT, inter-token
   latency, throughput at fixed concurrency, peak RSS. Freeze the prompt set and
   concurrency.
7. Apply the optimization, redeploy through GitOps, re-run the identical
   benchmark, write the before/after table naming the parameters that changed.
8. Write the four evidence files, each recording the GitOps manifest path, the
   Argo sync revision, and the reproduction command. Then flip these four rows
   to `executed` in `scripts/_phase2_rubric_items.py`, regenerate the CSV and
   the requirement tests, and re-run the audit.
9. `make gcp-down` if the next session is not immediate; record the delta.

## Success Criteria

- [x] Reviewer -> inspects the running `InferenceService` -> sees a versioned custom model server reconciled from a GitOps commit by an Argo Application that actually watches that path. (revision `fd-chat-model-predictor-00002`, real chat completion verified)
- [~] Agent runtime -> resolves the global `ModelConfig` -> reaches the model only through the agentgateway AI backend; a direct-to-model call from the sandbox is refused by an enforced NetworkPolicy. (ModelConfig deployed and reachable through agentgateway; the sandbox negative test is phase 3 scope — no `agents-sandbox` namespace exists yet)
- [x] Benchmarker -> runs `src/llm/benchmark.py` twice with identical inputs -> produces baseline and optimized rows with TTFT, inter-token latency, throughput and memory, and a named optimization between them. (real before/after table, quantization change; memory RSS caveat documented honestly in the evidence file)
- [ ] Operator -> hibernates and restores the cluster -> the model server starts from the PVC without re-downloading weights. **Deferred** — cluster stays up across phases 2-6 this session (user decision); verify at the actual end-of-session `gcp-down`/`gcp-up` cycle.
- [x] Auditor -> runs the four rows' regenerated requirement tests -> each asserts a real artifact at its declared path and a behavioral claim, not a placeholder file. (79 requirement tests pass with `PHASE2_GITOPS_ROOT` set)

## Risk Assessment

- **This is the highest-variance day.** A KServe or runtime-image mismatch can
  eat it. Mitigation: the operators are installed and healthy; the documented
  fallback is a plain vLLM-CPU Deployment behind agentgateway, costing ~2 points
  on the deploy row — invoke it rather than losing the day.
- **CPU inference may be too slow for downstream agent captures.** Mitigation:
  0.5B first, cap `max_tokens` in agent calls, treat TTFT as the benchmark
  headline.
- **The node is shared with everything else.** Mitigation: the phase-1 capacity
  budget is a hard input here; if the model does not fit alongside the
  observability stack, phase 4 runs its captures in a separate window with the
  model scaled down, and that is stated in the evidence.
- **An optimization that moves nothing measurable** fails the row. Mitigation:
  pick quantization, which moves memory and TTFT visibly on CPU.
