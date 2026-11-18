from __future__ import annotations

import httpx
import pytest

from src.agents import runtime
from src.agents.models import AgentFailure


@pytest.fixture(autouse=True)
def configure_specialists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATURE_AGENT_URL", "http://feature.test")
    monkeypatch.setenv("DRIFT_AGENT_URL", "http://drift.test")


@pytest.mark.asyncio
@pytest.mark.parametrize(("configured", "expected"), [("47", 47.0), (None, 50.0)])
async def test_runtime_uses_coordinator_timeout(monkeypatch, configured, expected) -> None:
    monkeypatch.setenv("AGENT_ROLE", "coordinator")
    if configured is None:
        monkeypatch.delenv("AGENT_TIMEOUT_SECONDS", raising=False)
    else:
        monkeypatch.setenv("AGENT_TIMEOUT_SECONDS", configured)
    recorded: list[float] = []
    graph = object()

    async def record_timeout(compiled, _payload, *, timeout_seconds):
        assert compiled is graph
        recorded.append(timeout_seconds)
        return AgentFailure(error="fixture")

    monkeypatch.setattr(runtime, "build_langgraph_coordinator", lambda *_args, **_kwargs: graph)
    monkeypatch.setattr(runtime, "coordinate_langgraph", record_timeout)

    application = runtime.create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application), base_url="http://test"
    ) as client:
        await client.post("/v1/run", json={"question": "q"})

    assert recorded == [expected]
    if configured is None:
        assert recorded[0] > 45.0


@pytest.mark.asyncio
async def test_runtime_logs_coordinator_failure_at_warning(monkeypatch, caplog) -> None:
    monkeypatch.setenv("AGENT_ROLE", "coordinator")

    async def fail(_graph, _payload, *, timeout_seconds):
        assert timeout_seconds > 0
        return AgentFailure(error="drift tool timeout")

    monkeypatch.setattr(runtime, "build_langgraph_coordinator", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(runtime, "coordinate_langgraph", fail)
    application = runtime.create_app()

    with caplog.at_level("WARNING", logger=runtime.__name__):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://test"
        ) as client:
            response = await client.post("/v1/run", json={"question": "q"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "failed",
        "error": "drift tool timeout",
        "decision": "stop",
    }
    assert "drift tool timeout" in caplog.text
