from __future__ import annotations

import asyncio

import pytest

from src.agents.coordinator import CoordinatorRequest
from src.agents.langgraph_runtime import LangGraphCoordinator
from src.agents.models import Citation, SpecialistResponse

pytestmark = pytest.mark.slow


class StubAgent:
    def __init__(self, response: SpecialistResponse | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls: list[dict] = []

    async def run(self, request: dict) -> SpecialistResponse:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


class SlowAgent(StubAgent):
    async def run(self, request: dict) -> SpecialistResponse:
        await asyncio.sleep(0.05)
        return await super().run(request)


def request() -> CoordinatorRequest:
    return CoordinatorRequest(
        question="What changed?",
        feature_request={
            "user_id": "alice",
            "feature_names": ["debt_to_asset"],
            "chunk_id": None,
            "scope": "tenant-a",
            "tool_budget": 1,
        },
        drift_request={
            "rows": [{"ticker": "AAA"}],
            "scenario": {"name": "baseline"},
            "scope": "tenant-a",
            "tool_budget": 1,
        },
    )


def specialist(name: str, uri: str) -> SpecialistResponse:
    return SpecialistResponse(
        specialist=name,
        answer=f"{name} answer",
        citations=[Citation(source_uri=uri, label=f"{name} source")],
    )


@pytest.mark.asyncio
async def test_langgraph_preserves_coordinator_success_contract() -> None:
    feature = StubAgent(specialist("feature", "feature://user/alice"))
    drift = StubAgent(specialist("drift", "drift://scenario/baseline"))
    coordinator = LangGraphCoordinator(feature, drift)

    result = await coordinator.coordinate(request())

    assert result.status == "ok"
    assert result.hops_used == 2
    assert [item.specialist for item in result.specialists] == ["feature", "drift"]
    assert [item.source_uri for item in result.citations] == [
        "feature://user/alice",
        "drift://scenario/baseline",
    ]
    assert len(feature.calls) == len(drift.calls) == 1


@pytest.mark.asyncio
async def test_langgraph_reports_incremental_hop_count() -> None:
    feature = StubAgent(specialist("feature", "feature://user/alice"))
    drift = StubAgent(specialist("drift", "drift://scenario/baseline"))
    coordinator = LangGraphCoordinator(feature, drift)

    result = await coordinator.coordinate(request().model_copy(update={"hop": 1}))

    assert result.status == "ok"
    assert result.hops_used == 2


@pytest.mark.asyncio
async def test_langgraph_stops_before_downstream_side_effect_on_provider_failure() -> None:
    feature = StubAgent(error=OSError("provider unavailable"))
    drift = StubAgent(specialist("drift", "drift://scenario/baseline"))
    coordinator = LangGraphCoordinator(feature, drift)

    result = await coordinator.coordinate(request())

    assert result.status == "failed"
    assert result.decision == "stop"
    assert result.error == "provider unavailable"
    assert len(feature.calls) == 1
    assert drift.calls == []


@pytest.mark.asyncio
async def test_langgraph_rejects_invalid_citation_scheme() -> None:
    feature = StubAgent(specialist("feature", "file:///secret"))
    drift = StubAgent(specialist("drift", "drift://scenario/baseline"))
    coordinator = LangGraphCoordinator(feature, drift)

    result = await coordinator.coordinate(request())

    assert result.status == "failed"
    assert result.error == "invalid_citations"


def test_langgraph_thread_id_is_tenant_scoped() -> None:
    feature = StubAgent(specialist("feature", "feature://user/alice"))
    drift = StubAgent(specialist("drift", "drift://scenario/baseline"))
    coordinator = LangGraphCoordinator(feature, drift)

    first = request()
    second = first.model_copy(
        update={
            "feature_request": {
                **first.feature_request,
                "user_id": "bob",
                "scope": "tenant-b",
            }
        }
    )

    assert coordinator._thread_id(first) == "tenant-a:alice"
    assert coordinator._thread_id(second) == "tenant-b:bob"
    assert coordinator._thread_id(first) != coordinator._thread_id(second)


def test_langgraph_rejects_persistent_checkpointer_without_authenticated_identity() -> None:
    feature = StubAgent(specialist("feature", "feature://user/alice"))
    drift = StubAgent(specialist("drift", "drift://scenario/baseline"))

    with pytest.raises(ValueError, match="authenticated thread identity"):
        LangGraphCoordinator(feature, drift, checkpointer=object())


@pytest.mark.asyncio
async def test_langgraph_timeout_stops_specialist_execution() -> None:
    feature = SlowAgent(specialist("feature", "feature://user/alice"))
    drift = StubAgent(specialist("drift", "drift://scenario/baseline"))
    coordinator = LangGraphCoordinator(feature, drift, timeout_seconds=0.001)

    result = await coordinator.coordinate(request())

    assert result.status == "failed"
    assert result.error == "feature_timeout"
    assert drift.calls == []
