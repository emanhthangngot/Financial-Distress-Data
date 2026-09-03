"""Executable checks for the Phase 05 repository-design implementations."""

from __future__ import annotations

import pytest

from src.llm.contracts import (
    BoundedAgentOrchestrationService,
    BoundedMcpToolService,
    InMemoryAgentReleaseService,
    InMemoryEmbeddingRegistry,
)


def digest(char: str = "a") -> str:
    return f"sha256:{char * 64}"


def test_embedding_registry_validates_versions_and_hot_swaps() -> None:
    registry = InMemoryEmbeddingRegistry()
    first = registry.register_version("e5-small", 384, digest())
    second = registry.register_version("e5-small", 384, digest("b"))
    assert registry.resolve_active() == first
    assert registry.compatibility_check(first, second)
    result = registry.hot_swap(second)
    assert result["active_version"] == second
    assert registry.resolve_active() == second


def test_embedding_registry_rejects_incompatible_dimensions() -> None:
    registry = InMemoryEmbeddingRegistry()
    first = registry.register_version("e5-small", 384, digest())
    second = registry.register_version("large", 768, digest("b"))
    assert not registry.compatibility_check(first, second)
    with pytest.raises(ValueError, match="dimensions"):
        registry.hot_swap(second)


def test_embedding_registry_rejects_invalid_registration_and_unknown_state() -> None:
    registry = InMemoryEmbeddingRegistry()
    with pytest.raises(LookupError, match="no active"):
        registry.resolve_active()
    with pytest.raises(ValueError, match="model_name"):
        registry.register_version("", 384, digest())
    with pytest.raises(ValueError, match="dims"):
        registry.register_version("model", 0, digest())
    with pytest.raises(ValueError, match="digest"):
        registry.register_version("model", 384, "not-a-digest")
    with pytest.raises(KeyError, match="unknown"):
        registry.hot_swap("missing")


def test_agent_release_service_requires_real_warm_measurements() -> None:
    calls: list[tuple[str, int]] = []

    def benchmark(agent: str, replicas: int) -> dict[str, float]:
        calls.append((agent, replicas))
        return {
            "cold_start_seconds": 4.0,
            "warm_start_seconds": 1.0,
            "cold_ttft_seconds": 2.0,
            "warm_ttft_seconds": 0.5,
        }

    service = InMemoryAgentReleaseService(benchmark=benchmark, revision_provider=lambda: "r" * 40)
    release = service.register("feature-agent", "v1", {"model": "fd-chat-model"})
    assert len(release) == 16
    experiment = service.canary("feature-agent", "v2", 0.1)
    assert len(experiment) == 16
    assert service.warm_up("feature-agent", 2)["warm_ttft_seconds"] < 2.0
    assert calls == [("feature-agent", 2)]
    assert service.promote_or_rollback("feature-agent", "promote") == "r" * 40


def test_agent_release_service_rejects_invalid_canary_and_measurements() -> None:
    service = InMemoryAgentReleaseService(
        benchmark=lambda _agent, _replicas: {}, revision_provider=lambda: "r" * 40
    )
    service.register("feature-agent", "v1", {})
    with pytest.raises(ValueError, match="fraction"):
        service.canary("feature-agent", "v2", 1.0)
    with pytest.raises(ValueError, match="missing measurements"):
        service.warm_up("feature-agent", 1)


def test_agent_release_service_rejects_unknown_and_invalid_release_inputs() -> None:
    service = InMemoryAgentReleaseService(
        benchmark=lambda _agent, _replicas: {}, revision_provider=lambda: "r" * 40
    )
    with pytest.raises(ValueError, match="agent and version"):
        service.register("", "v1", {})
    with pytest.raises(KeyError, match="not registered"):
        service.canary("missing", "v2", 0.1)
    with pytest.raises(KeyError, match="not registered"):
        service.warm_up("missing", 1)
    with pytest.raises(KeyError, match="not registered"):
        service.promote_or_rollback("missing", "promote")
    service.register("agent", "v1", {})
    with pytest.raises(ValueError, match="replicas"):
        service.warm_up("agent", 0)
    with pytest.raises(ValueError, match="decision"):
        service.promote_or_rollback("agent", "hold")


def test_bounded_mcp_service_enforces_validation_authorization_budget_and_trace() -> None:
    traces: list[tuple[str, dict, object]] = []
    service = BoundedMcpToolService(
        handlers={"echo": lambda payload: payload["value"]},
        validators={"echo": lambda payload: payload},
        grants={"echo": {("agent", "scope")}},
        trace_sink=lambda tool, request, result: traces.append((tool, request, result)),
        max_calls=1,
    )
    request = {"value": "ok", "agent_identity": "agent", "scope": "scope"}
    assert service.invoke("echo", request).value == "ok"
    assert service.invoke("echo", request).error == "tool_budget_exhausted"
    assert service.invoke("unknown", request).error == "unknown tool: unknown"
    assert service.invoke("echo", {**request, "scope": "other"}).error == "forbidden"
    assert len(traces) == 4
    with pytest.raises(ValueError, match="max_calls"):
        BoundedMcpToolService(handlers={}, validators={}, grants={}, max_calls=0)


def test_bounded_agent_orchestration_service_handles_hops_errors_and_citations() -> None:
    service = BoundedAgentOrchestrationService(
        {"feature": lambda task: {"task": task, "citations": ["feature://1"]}}, max_hops=1
    )
    assert service.coordinate("q", ["feature", "feature"]) == {
        "status": "ok",
        "results": {"feature": {"task": "q", "citations": ["feature://1"]}},
        "hops": 1,
    }
    assert service.coordinate("q", ["feature", "missing"])["decision"] == "stop"
    assert service.coordinate("q", ["feature", "other"])["error"] == "hop_limit_exceeded"
    assert service.check_citations(None) == ["response_not_mapping"]
    assert service.check_citations({}) == ["missing_citations"]
    assert service.check_citations({"citations": ["", 3]}) == ["", 3]
    with pytest.raises(ValueError, match="max_hops"):
        BoundedAgentOrchestrationService({}, max_hops=0)


def test_bounded_agent_orchestration_service_stops_on_handler_and_citation_errors() -> None:
    def raises(_task: str) -> dict[str, object]:
        raise RuntimeError("specialist unavailable")

    failed = BoundedAgentOrchestrationService({"feature": raises})
    assert failed.coordinate("q", ["feature"]) == {
        "status": "failed",
        "decision": "stop",
        "error": "specialist unavailable",
    }

    invalid = BoundedAgentOrchestrationService({"feature": lambda _task: {"citations": ["   "]}})
    assert invalid.coordinate("q", ["feature"]) == {
        "status": "failed",
        "decision": "stop",
        "error": "invalid_citations:feature",
    }
