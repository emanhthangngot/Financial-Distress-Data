from __future__ import annotations

import httpx
import pytest

from src.agents import runtime
from src.agents.models import AgentFailure


def test_runtime_reads_coordinator_timeout_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_ROLE", "coordinator")
    monkeypatch.setenv("AGENT_TIMEOUT_SECONDS", "47")
    captured: dict[str, float] = {}

    class RecordingCoordinator:
        def __init__(self, *args, **kwargs) -> None:
            del args
            captured["timeout_seconds"] = kwargs["timeout_seconds"]

    monkeypatch.setattr(runtime, "Coordinator", RecordingCoordinator)

    runtime.create_app()

    assert captured == {"timeout_seconds": 47.0}


@pytest.mark.asyncio
async def test_runtime_defaults_coordinator_timeout_above_specialist_budget(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_ROLE", "coordinator")
    monkeypatch.delenv("AGENT_TIMEOUT_SECONDS", raising=False)
    captured: dict[str, float] = {}

    class RecordingCoordinator:
        def __init__(self, *args, **kwargs) -> None:
            del args
            captured["timeout_seconds"] = kwargs["timeout_seconds"]

    monkeypatch.setattr(runtime, "Coordinator", RecordingCoordinator)

    runtime.create_app()

    assert captured["timeout_seconds"] > 45.0


@pytest.mark.asyncio
async def test_runtime_logs_coordinator_failure_at_warning(monkeypatch, caplog) -> None:
    monkeypatch.setenv("AGENT_ROLE", "coordinator")

    class FailureCoordinator:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        async def coordinate(self, payload):
            del payload
            return AgentFailure(error="drift tool timeout")

    monkeypatch.setattr(runtime, "Coordinator", FailureCoordinator)
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
