from __future__ import annotations

import json

from src.agents.runtime import decode_model_response
from src.observability.telemetry import Telemetry, redact_fields, redact_text


def test_telemetry_redaction_keeps_correlation_metadata_only() -> None:
    raw = {
        "prompt": "What happened to user@example.com?",
        "document": "account 0912-345-678",
        "authorization": "Bearer secret-value",
        "raw_model_output": "private completion",
        "request_id": "req-123",
        "correlation_id": "corr-123",
        "release_id": "release-7",
        "session_id": "session-9",
        "operation": "model.generate",
    }

    encoded = json.dumps(redact_fields(raw))

    assert "user@example.com" not in encoded
    assert "0912-345-678" not in encoded
    assert "secret-value" not in encoded
    assert "private completion" not in encoded
    for field in ("request_id", "correlation_id", "release_id", "session_id", "operation"):
        assert raw[field] in encoded
    assert "private prompt" not in redact_text("prompt=private prompt")


def test_canonical_metrics_have_service_label_and_required_families() -> None:
    telemetry = Telemetry("feature-mcp")
    telemetry.observe_tokens("model-a", "input", 4)
    telemetry.observe_tokens("model-a", "output", 3)
    telemetry.observe_tokens("model-a", "total", 7)
    telemetry.observe_generation("model-a", 0.2)
    telemetry.observe_ttft("model-a", 0.05)
    telemetry.observe_pii_catch("feature-agent", "email")
    telemetry.observe_agent_call("feature-agent")
    telemetry.observe_tool_call("lookup_feature_context")
    telemetry.observe_failure("mcp.lookup_feature_context", "timeout")
    telemetry.observe_http("/healthz", 200, 0.01, "GET")

    exposition = telemetry.render().decode()

    for name in telemetry.canonical_metric_names:
        assert f"# TYPE {name} " in exposition
    assert (
        'fd_llm_tokens_total{direction="input",model="model-a",service="feature-mcp"}' in exposition
    )
    assert (
        'fd_web_api_requests_total{method="GET",route="/healthz",service="feature-mcp",status="200"}'
        in exposition
    )


def test_streaming_model_response_collects_first_token_payload_and_usage() -> None:
    response = decode_model_response(
        b'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
        b'data: {"choices":[{"delta":{"content":" world"}}]}\n\n'
        b'data: {"choices":[{"delta":{}}],"usage":{"prompt_tokens":2,"completion_tokens":2,'
        b'"total_tokens":4}}\n\n'
        b"data: [DONE]\n\n"
    )

    assert response["choices"][0]["message"]["content"] == "hello world"
    assert response["usage"]["total_tokens"] == 4
