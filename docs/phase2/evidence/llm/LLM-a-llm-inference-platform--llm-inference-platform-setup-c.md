# Evidence — LLM inference platform deployment

Proves `platform/inference/model-server.yaml` (financial-distress-gitops) is
a real, versioned KServe `InferenceService` — llama.cpp server, CPU,
OpenAI-compatible — reconciled from a GitOps commit by the `platform-inference`
Argo Application, routed through `agentgateway-proxy` (Gateway API) rather
than exposed directly.

- rubric_id: LLM-a-llm-inference-platform--llm-inference-platform-setup-c
- execution_timestamp: 2026-08-10T01:41:42+00:00
- source_sha: f59a5ef32c976eef88cb396f56f105305da4228f
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: KServe v0.14.1, Knative Serving, llama.cpp server (`ghcr.io/ggml-org/llama.cpp:server`), agentgateway v1.4.1, Gateway API v1.6.0
- command: `kubectl exec curl-test2 -n default -- curl -sS -X POST http://agentgateway-proxy.agentgateway-system.svc.cluster.local:8080/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"qwen2.5-0.5b-instruct","messages":[{"role":"user","content":"Say hello in exactly 3 words."}],"max_tokens":32,"temperature":0}'`
- expected_result: agentgateway routes the OpenAI-compatible request through its Gateway/HTTPRoute to the KServe `InferenceService`'s predictor pod and returns a real chat completion
- actual_result: `{"choices":[{"finish_reason":"stop","index":0,"message":{"role":"assistant","content":"Hello!"}}], ...}` — 200 OK, real generated text, not a stub
- redaction_status: reviewed — GitOps repository is private; no secrets in this request/response pair

## Command output (real run, through agentgateway)

```
$ kubectl exec curl-test2 -n default -- curl -sS -X POST \
    http://agentgateway-proxy.agentgateway-system.svc.cluster.local:8080/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"qwen2.5-0.5b-instruct","messages":[{"role":"user","content":"Say hello in exactly 3 words."}],"max_tokens":32,"temperature":0}'
{"choices":[{"finish_reason":"stop","index":0,"message":{"role":"assistant","content":"Hello!"}}],
 "created":1786326102,"model":"/models/qwen2.5-0.5b-instruct-q8_0.gguf",
 "object":"chat.completion",
 "usage":{"completion_tokens":3,"prompt_tokens":37,"total_tokens":40},
 "id":"chatcmpl-4xGFOzjx6rWQ8rIfQx8bDf1IjK7L1aMt"}
```

## Architecture actually deployed

```
kagent ModelConfig (fd-global-model-config, platform/agents/global-model-config.yaml)
  -> agentgateway-proxy Gateway (platform/agentgateway/gateway.yaml)
  -> HTTPRoute fd-chat-model-route (platform/agentgateway/httproute-fd-chat.yaml)
  -> Knative revision's direct-to-pod "-private" Service
  -> llama.cpp server (KServe InferenceService fd-chat-model)
```

Two real Knative-routing indirections were debugged live (full detail in
`httproute-fd-chat.yaml`'s comments): the predictor's public Service is
`ExternalName` (unresolvable by agentgateway's endpoint-based routing), and
the per-revision public Service requires Knative's Activator to see a
Host header naming the revision, which agentgateway does not rewrite. The
`AgentgatewayModel` CRD (`platform/agentgateway/model-fd-chat.yaml`) stays
declared as the AI-provider-format artifact but is honestly marked
non-load-bearing — its xDS control plane never pushed it into the running
proxy's config within the investigation window; the plain Gateway API
`HTTPRoute` is what actually carries traffic.

## llm-d note

llm-d is dropped per decision D-E3 (already recorded) and the pinned KServe
v0.14.1, which ships no `LLMInferenceService` CRD. KServe on Knative behind
agentgateway satisfies the row's literal text ("Deploy LLM inference
platform + setup custom model" naming an agent gateway).
