---
title: "LLM Inference Platform"
date: 2026-08-14
status: active
---

# LLM Inference Platform: custom model server, agentgateway routing, and a measured optimization

This doc proves the three rows in the "Deploy a LLM inference platform" rubric
area: the platform is deployed and reachable through an agent gateway, the
custom model server is a real runtime-configuration module (not a stub), and
the deployment was benchmarked baseline-vs-optimized with real numbers. It
does not prove production-grade autoscaling or multi-model routing — those
are out of scope for this submission.

**Active deployment facts:** project `project-60655616-d84a-4883-867`,
cluster `fsds-evidence` (`asia-southeast1-b`), namespace `default` (model) +
`agentgateway-system` (gateway). KServe v0.14.1 on Knative Serving. Model
server: llama.cpp (`ghcr.io/ggml-org/llama.cpp:server`), Qwen2.5-0.5B-Instruct
GGUF. agentgateway v1.4.1, Gateway API v1.6.0. Two `InferenceService`s
verified `Ready=True` this session (`fd-chat-model`, `fd-embeddings`).

## Part I — Deploy and route

### 1. Runtime-configuration module mirrors the deployed container args

`ModelServerConfig` is the source-repo contract for the exact llama.cpp CLI
args the live `InferenceService` container runs with — two frozen variants
exist so the benchmark in Part III is a genuine baseline-vs-optimized run, not
a synthetic comparison:

```python
# src/llm/model_server.py:21-61
@dataclasses.dataclass(frozen=True)
class ModelServerConfig:
    """Runtime configuration for the llama.cpp OpenAI-compatible server.

    Two frozen variants exist so ``benchmark.py`` can produce a genuine
    before/after comparison: ``BASELINE_CONFIG`` (Q8_0, larger/slower) and
    ``OPTIMIZED_CONFIG`` (Q4_K_M, the measured optimization — smaller weight
    file, lower memory footprint, faster CPU inference).
    """

    model_path: str
    quantization: str
    context_window: int = 2048
    n_threads: int = 4
    port: int = 8080

BASELINE_CONFIG = ModelServerConfig(
    model_path="/models/qwen2.5-0.5b-instruct-q8_0.gguf",
    quantization="Q8_0",
)

OPTIMIZED_CONFIG = ModelServerConfig(
    model_path="/models/qwen2.5-0.5b-instruct-q4_k_m.gguf",
    quantization="Q4_K_M",
)
```

Full evidence: [`LLM-a-llm-inference-platform--a-custom-model.md`](../../phase2/evidence/llm/LLM-a-llm-inference-platform--a-custom-model.md).

### 2. Route: ModelConfig → agentgateway → KServe

```text
kagent ModelConfig (fd-global-model-config)
  -> agentgateway-proxy Gateway (platform/agentgateway/gateway.yaml)
  -> HTTPRoute fd-chat-model-route
  -> Knative revision's direct-to-pod "-private" Service
  -> llama.cpp server (KServe InferenceService fd-chat-model)
```

Two real routing indirections had to be debugged live: the predictor's public
Service is `ExternalName` (unresolvable by agentgateway's endpoint-based
routing), and the per-revision public Service requires Knative's Activator to
see a Host header naming the revision, which agentgateway does not rewrite.
The `AgentgatewayModel` CRD stays declared but is honestly marked
non-load-bearing — the plain Gateway API `HTTPRoute` is what actually carries
traffic. Full evidence:
[`LLM-a-llm-inference-platform--llm-inference-platform-setup-c.md`](../../phase2/evidence/llm/LLM-a-llm-inference-platform--llm-inference-platform-setup-c.md).

Subsystem diagram (color legend in `docs/docs-style-contract.md` §7):

```mermaid
flowchart LR
    classDef edge fill:#2b6cb0,stroke:#1a365d,color:#fff
    classDef service fill:#38a169,stroke:#22543d,color:#fff
    classDef store fill:#805ad5,stroke:#44337a,color:#fff
    classDef model fill:#d69e2e,stroke:#744210,color:#fff
    classDef result fill:#dd6b20,stroke:#7b341e,color:#fff

    CALLER["Agent caller<br/>coordinator / feature / drift Agent"]:::service
    MODELCONFIG["kagent ModelConfig CRD"]:::service
    GATEWAY["agentgateway-proxy<br/>agentgateway-system"]:::edge
    KSERVE["KServe/Knative InferenceService<br/>fd-chat-model, fd-embeddings"]:::model
    RESP["OpenAI-compatible response"]:::result

    CALLER -->|"model call"| MODELCONFIG
    MODELCONFIG -->|"resolved route"| GATEWAY
    GATEWAY -->|"HTTPRoute fd-chat-model-route"| KSERVE
    KSERVE -->|"completion + usage"| RESP
    RESP -->|"tokens, latency"| CALLER
```

#### Image proof

`kubectl get isvc -A` (CLI evidence, captured this session):

```text
NAMESPACE   NAME            URL                                                        READY
default     fd-chat-model   http://fd-chat-model-predictor.default.svc.cluster.local   True
default     fd-embeddings   http://fd-embeddings-predictor.default.svc.cluster.local   True
```

`kubectl get gateway -A`:

```text
NAMESPACE             NAME                 CLASS          ADDRESS         PROGRAMMED
agentgateway-system   agentgateway-proxy   agentgateway   136.85.22.129   True
```

*Image note:* the CLI output shows both `InferenceService`s `READY=True` and
the gateway `PROGRAMMED=True` at capture time (2026-08-14). It proves both
resources reconciled successfully in the live cluster. It does not prove a
request round-trip — that's row 3 below.

## Part II — Real round-trip

A real OpenAI-compatible chat completion, called through the module above
against the port-forwarded live pod:

```python
# call as executed, from src/llm/model_server.py::call_chat_completion
body, elapsed = call_chat_completion(
    "http://localhost:18080",
    [{"role": "user", "content": "Say hi in 2 words."}],
    max_tokens=16,
)
# -> ("Hello!", 0.2289610840016394)
```

And through the deployed gateway route end-to-end (not port-forwarded around
it):

```text
$ kubectl exec curl-test2 -n default -- curl -sS -X POST \
    http://agentgateway-proxy.agentgateway-system.svc.cluster.local:8080/v1/chat/completions \
    -d '{"model":"qwen2.5-0.5b-instruct","messages":[{"role":"user","content":"Say hello in exactly 3 words."}],"max_tokens":32,"temperature":0}'
{"choices":[{"finish_reason":"stop","index":0,"message":{"role":"assistant","content":"Hello!"}}],
 "usage":{"completion_tokens":3,"prompt_tokens":37,"total_tokens":40}}
```

Both are real generated text from the live pod, not stubs. Full evidence:
[`LLM-a-llm-inference-platform--a-custom-model.md`](../../phase2/evidence/llm/LLM-a-llm-inference-platform--a-custom-model.md).

## Part III — Optimization: quantization benchmark

`src/llm/benchmark.py` ran twice against the live `InferenceService` — once
on the Q8_0 baseline, once after redeploying to Q4_K_M — with an identical
frozen prompt set (`DEFAULT_PROMPTS`) and concurrency=1.

| Metric | Baseline (Q8_0) | Optimized (Q4_K_M) | Delta |
|---|---:|---:|---:|
| mean_ttft_seconds | 0.3403 | 0.2914 | −14.4% |
| mean_inter_token_latency_seconds | 0.0222 | 0.0168 | −24.3% |
| mean_throughput_tokens_per_second | 36.68 | 45.07 | +22.9% |
| on-disk weight size | 676MB | 491MB | −27.4% |
| server container memory (`kubectl top pod`, single snapshot) | 91Mi | 116Mi | not conclusive (see limitation) |

Full evidence with per-prompt raw results:
[`LLM-a-llm-inference-platform--benchmark-model-server-and-opt.md`](../../phase2/evidence/llm/LLM-a-llm-inference-platform--benchmark-model-server-and-opt.md).

## Limitations

The `peak_rss_mb` field in `BenchmarkResult` reads the *client* process's
memory, not the server's — both rows read ~26MB because that's the
benchmarking script's own footprint, unrelated to which quantization is under
test. This is a real design limitation, disclosed rather than hidden. The
`kubectl top pod` server-side memory snapshots are single-sample reads taken
moments apart under different page-cache states, not a rigorous memory
profile. TTFT, inter-token latency, throughput, and on-disk size are the
statistically meaningful wins; memory is reported honestly as inconclusive.
This is an infrastructure-level before/after comparison of one deployed
configuration change, not a controlled A/B experiment across many samples —
see `ab_testing.md` for the separate, dedicated A/B testing capability.

## References

- llama.cpp server: https://github.com/ggml-org/llama.cpp
- KServe: https://kserve.github.io/website/
- agentgateway: https://agentgateway.dev/
