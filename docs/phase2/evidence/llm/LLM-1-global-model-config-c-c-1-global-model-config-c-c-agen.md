# Evidence — 1 global model config for Agents

Proves `platform/agents/global-model-config.yaml` (financial-distress-gitops)
deploys a real kagent `ModelConfig` CRD instance, `fd-global-model-config`,
that every kagent Agent references — pointed at the custom chat model
through agentgateway (not directly at the KServe `InferenceService`), so a
future sandboxed agent's NetworkPolicy can allow egress to
`agentgateway-system` only.

- rubric_id: LLM-1-global-model-config-c-c-1-global-model-config-c-c-agen
- execution_timestamp: 2026-08-10T01:59:00+00:00
- source_sha: f09d391bb7bd8f51561477b619ae4b1c5a88011c
- gitops_sha: 921bdc1075ef8335e0f509747bd64db2d525f73e
- versions: kagent 0.9.12 (kagent-crds + kagent Helm charts, kmcp disabled)
- command: `kubectl get modelconfig fd-global-model-config -n kagent -o jsonpath='{.spec}'`
- expected_result: one `ModelConfig` resource, provider `OpenAI`, model `qwen2.5-0.5b-instruct`, `openAI.baseUrl` pointing at `agentgateway-proxy.agentgateway-system.svc.cluster.local:8080/v1` — the same endpoint proven reachable in the inference-platform-deployment evidence row
- actual_result: `{"apiKeySecret":"kagent-fd-chat-model","apiKeySecretKey":"API_KEY","model":"qwen2.5-0.5b-instruct","openAI":{"baseUrl":"http://agentgateway-proxy.agentgateway-system.svc.cluster.local:8080/v1"},"provider":"OpenAI"}` — accepted by the K8s API, matches the deployed manifest exactly
- redaction_status: reviewed — GitOps repository is private; `apiKeySecret` references a placeholder Secret (`kagent-fd-chat-model`/`API_KEY` = `"not-required-local-model"`), not a real credential — the internal model server needs no auth

## Command output (real run)

```
$ kubectl get modelconfig -n kagent
NAME                     PROVIDER   MODEL
default-model-config     Ollama     llama3.2
fd-global-model-config   OpenAI     qwen2.5-0.5b-instruct

$ kubectl get modelconfig fd-global-model-config -n kagent -o jsonpath='{.spec}'
{"apiKeySecret":"kagent-fd-chat-model","apiKeySecretKey":"API_KEY","model":"qwen2.5-0.5b-instruct",
 "openAI":{"baseUrl":"http://agentgateway-proxy.agentgateway-system.svc.cluster.local:8080/v1"},
 "provider":"OpenAI"}
```

## Note on the second ModelConfig

`default-model-config` (provider Ollama) is the kagent Helm chart's own
baked-in default, rendered because `providers.default` was not overridden.
It references a nonexistent Ollama host and is inert — it does not affect
`fd-global-model-config`, which is the row's real deliverable and what
phase 3's coordinator/data-pulling agents will reference.
