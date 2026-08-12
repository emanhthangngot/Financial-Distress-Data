# Evidence — Setup a custom model

Proves `src/llm/model_server.py` is the real runtime-configuration and
OpenAI-compatible client module for the custom chat model server —
`ModelServerConfig` mirrors the exact container args the deployed
`InferenceService` runs with, and `call_chat_completion` is the same request
builder that produced the live completion in the platform-deployment
evidence row.

- rubric_id: LLM-a-llm-inference-platform--a-custom-model
- execution_timestamp: 2026-08-10T01:41:42+00:00
- source_sha: 6c13197663dd6e2a11981167a19bd3ca21ce44ea
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: Python 3.11, llama.cpp server (Qwen2.5-0.5B-Instruct GGUF, Q8_0 baseline / Q4_K_M optimized)
- command: `.venv-phase2/bin/python3 -c "from src.llm.model_server import call_chat_completion; print(call_chat_completion('http://localhost:18080', [{'role':'user','content':'Say hi in 2 words.'}], max_tokens=16))"` (port-forwarded to the live `fd-chat-model-predictor-00001-private` Service)
- expected_result: `call_chat_completion` POSTs a well-formed OpenAI-compatible request and returns the parsed JSON body plus elapsed seconds for a real running server
- actual_result: `("Hello!", 0.2289610840016394)` — real generated text, real latency, from the live pod (not a mock)
- redaction_status: reviewed — no secrets in the module or the request/response pair

## Command output (real run)

```
$ .venv-phase2/bin/python3 -c "
from src.llm.model_server import call_chat_completion
body, elapsed = call_chat_completion('http://localhost:18080', [{'role':'user','content':'Say hi in 2 words.'}], max_tokens=16)
print(body['choices'][0]['message']['content'], elapsed)
"
Hello! 0.2289610840016394
```

## What this module owns

`ModelServerConfig` (`BASELINE_CONFIG` = Q8_0, `OPTIMIZED_CONFIG` = Q4_K_M)
mirrors `platform/inference/model-server.yaml`'s container `args` exactly —
the GitOps manifest's own comment says to keep the two in sync.
`build_chat_completion_request` and `call_chat_completion` are reused
unmodified by `src/llm/benchmark.py`'s streaming harness (see the
benchmark row's evidence), so this is the one request-construction path
both the smoke test and the benchmark run through.
