"""Custom LLM model-server runtime configuration and OpenAI-compatible client.

The actual server binary is llama.cpp's OpenAI-compatible HTTP server,
deployed as a KServe ``InferenceService`` at
``platform/inference/model-server.yaml`` (financial-distress-gitops). This
module owns the runtime-configuration contract that container is launched
with (model path, context window, thread count) — keep the two in sync when
either changes — plus a thin client used by ``src/llm/benchmark.py`` and any
agent that needs to call the deployed server directly for testing.
"""

from __future__ import annotations

import dataclasses
import json
import time
import urllib.request
from typing import Any


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

    def to_llama_cpp_args(self) -> list[str]:
        """Render this config as the llama.cpp server CLI argv."""
        return [
            "--model",
            self.model_path,
            "--ctx-size",
            str(self.context_window),
            "--threads",
            str(self.n_threads),
            "--port",
            str(self.port),
            "--host",
            "0.0.0.0",
        ]


BASELINE_CONFIG = ModelServerConfig(
    model_path="/models/qwen2.5-0.5b-instruct-q8_0.gguf",
    quantization="Q8_0",
)

OPTIMIZED_CONFIG = ModelServerConfig(
    model_path="/models/qwen2.5-0.5b-instruct-q4_k_m.gguf",
    quantization="Q4_K_M",
)


def build_chat_completion_request(
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 128,
    temperature: float = 0.0,
    stream: bool = False,
) -> dict[str, Any]:
    """Build an OpenAI-compatible ``/v1/chat/completions`` request body."""
    return {
        "model": "qwen2.5-0.5b-instruct",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
    }


def call_chat_completion(
    base_url: str,
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 128,
    temperature: float = 0.0,
    timeout: float = 60.0,
) -> tuple[dict[str, Any], float]:
    """POST a real chat completion to a running server.

    Returns the parsed JSON response body and wall-clock elapsed seconds.
    Used to capture the request/response pair evidence records, and as the
    non-streaming path for the agentgateway reachability check.
    """
    payload = build_chat_completion_request(
        messages, max_tokens=max_tokens, temperature=temperature
    )
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read())
    elapsed = time.perf_counter() - started
    return body, elapsed
