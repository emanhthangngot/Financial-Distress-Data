---
title: "Global Model Config"
date: 2026-08-14
status: active
---

# Global Model Config: one shared kagent ModelConfig every agent references

This doc proves the single row in the "1 global model config" rubric area:
one kagent `ModelConfig` CRD instance, referenced by every agent, routed
through agentgateway rather than directly at the model server. It does not
prove per-agent model overrides — every agent in this submission shares the
same config by design.

**Active deployment facts:** namespace `kagent`, kagent 0.9.12 (kagent-crds +
kagent Helm charts, kmcp disabled), resource `fd-global-model-config`.

## Part I — Deploy

### 1. One ModelConfig, one provider, one baseUrl

```text
$ kubectl get modelconfig -n kagent
NAME                     PROVIDER   MODEL
default-model-config     Ollama     llama3.2
fd-global-model-config   OpenAI     qwen2.5-0.5b-instruct

$ kubectl get modelconfig fd-global-model-config -n kagent -o jsonpath='{.spec}'
{"apiKeySecret":"kagent-fd-chat-model","apiKeySecretKey":"API_KEY","model":"qwen2.5-0.5b-instruct",
 "openAI":{"baseUrl":"http://agentgateway-proxy.agentgateway-system.svc.cluster.local:8080/v1"},
 "provider":"OpenAI"}
```

`openAI.baseUrl` points at `agentgateway-proxy.agentgateway-system` — the
same route proven reachable in
[`llm_inference_platform.md`](./llm_inference_platform.md), never directly at
the KServe `InferenceService`. This is deliberate: a sandboxed agent's
NetworkPolicy can allow egress to `agentgateway-system` only, never to the
model namespace directly.

`default-model-config` (provider Ollama) is the kagent Helm chart's own
baked-in default, rendered because `providers.default` was not overridden —
it references a nonexistent Ollama host and is inert. It does not affect
`fd-global-model-config`, which every real agent in this submission
references.

Full evidence:
[`LLM-1-global-model-config-c-c-1-global-model-config-c-c-agen.md`](../../platform/evidence/llm/LLM-1-global-model-config-c-c-1-global-model-config-c-c-agen.md).

## Limitations

`apiKeySecret` references a placeholder Secret
(`kagent-fd-chat-model`/`API_KEY` = `"not-required-local-model"`) — the
internal model server needs no auth, so this is not a real credential
rotation story. A production deployment reaching an external model provider
would need real secret rotation, which this submission does not exercise.

## References

- kagent ModelConfig CRD: https://kagent.dev/docs
