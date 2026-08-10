from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from .conftest import load_app_module


class FeatureClient:
    async def get_by_id(self, user_id: str, feature_names: tuple[str, ...]) -> dict[str, Any]:
        return {name: f"{user_id}:{name}" for name in feature_names}

    async def ready(self) -> bool:
        return True


class RagClient:
    async def get_by_id(self, chunk_id: str) -> dict[str, Any] | None:
        return {
            "chunk_id": chunk_id,
            "chunk_text": "trusted financial statement excerpt",
            "source_uri": "s3://reports/fpt.pdf",
        }

    async def ready(self) -> bool:
        return True


class Metrics:
    def __init__(self) -> None:
        self.observed: list[tuple[str, int]] = []

    def observe(self, route: str, status_code: int, elapsed_seconds: float) -> None:
        assert elapsed_seconds >= 0
        self.observed.append((route, status_code))


@pytest.mark.asyncio
async def test_feature_api_is_async_validated_and_ready() -> None:
    module = load_app_module("feature-mcp", "main")
    metrics = Metrics()
    app = module.create_app(FeatureClient(), RagClient(), metrics)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/healthz")).json() == {"status": "ok"}
        assert (await client.get("/readyz")).json() == {"status": "ready"}
        response = await client.post(
            "/v1/features/by-id",
            json={"user_id": "u-1", "feature_names": ["risk_score"]},
        )
        assert response.status_code == 200
        assert response.json() == {
            "user_id": "u-1",
            "features": {"risk_score": "u-1:risk_score"},
        }
        invalid = await client.post(
            "/v1/features/by-id", json={"user_id": "bad id", "feature_names": []}
        )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
    assert ("/v1/features/by-id", 200) in metrics.observed


@pytest.mark.asyncio
async def test_production_feature_app_fails_closed_without_config(monkeypatch) -> None:
    monkeypatch.delenv("FEAST_REPO_PATH", raising=False)
    monkeypatch.delenv("RAG_DATABASE_URL", raising=False)
    module = load_app_module("feature-mcp", "main")
    app = module.create_app(mount_mcp=False)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        ready = await client.get("/readyz")
        lookup = await client.post(
            "/v1/features/by-id",
            json={"user_id": "AAA", "feature_names": ["view:risk_score"]},
        )
    assert ready.status_code == 503
    assert lookup.status_code == 503
    assert lookup.json()["error"]["code"] == "dependency_unavailable"


@pytest.mark.asyncio
async def test_feast_adapter_maps_user_id_to_ticker_and_offloads(monkeypatch) -> None:
    module = load_app_module("feature-mcp", "main")
    calls: dict[str, Any] = {}

    class Result:
        def to_dict(self) -> dict[str, list[Any]]:
            return {"ticker": ["AAA"], "risk_score": [0.73]}

    class Store:
        def get_online_features(self, *, features, entity_rows):
            calls["features"] = features
            calls["entity_rows"] = entity_rows
            return Result()

    async def to_thread(function, *args):
        calls["offloaded"] = True
        return function(*args)

    monkeypatch.setattr(module.asyncio, "to_thread", to_thread)
    adapter = module.FeastOnlineFeatureClient("feature_repo/structured")
    adapter._store = Store()
    result = await adapter.get_by_id("AAA", ("company_features:risk_score",))
    assert result == {"risk_score": 0.73}
    assert calls["entity_rows"] == [{"ticker": "AAA"}]
    assert calls["features"] == ["company_features:risk_score"]
    assert calls["offloaded"] is True


@pytest.mark.asyncio
async def test_metrics_and_mcp_mount_are_exposed() -> None:
    module = load_app_module("feature-mcp", "main")
    app = module.create_app(FeatureClient(), RagClient())
    assert any(getattr(route, "path", None) == "/mcp" for route in app.routes)
    app.state.metrics.observe_tokens("test-model", "input", 3)
    app.state.metrics.observe_ttft("test-model", 0.05)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.get("/healthz")
        metrics = await client.get("/metrics")
    assert metrics.status_code == 200
    assert 'fd_http_requests_total{route="/healthz",status="200"} 1.0' in metrics.text
    assert 'fd_model_tokens_total{direction="input",model="test-model"} 3.0' in metrics.text
    assert 'fd_model_ttft_seconds_count{model="test-model"} 1.0' in metrics.text


class Api:
    def __init__(self, delay: float = 0) -> None:
        self.calls = 0
        self.delay = delay

    async def feature_by_id(self, user_id: str, names: tuple[str, ...]) -> dict[str, Any]:
        self.calls += 1
        await asyncio.sleep(self.delay)
        return {"user": user_id, "names": names}

    async def rag_by_id(self, chunk_id: str) -> dict[str, Any]:
        self.calls += 1
        return {"chunk_id": chunk_id}


class Trace:
    def emit(self, event: str, attributes: dict[str, Any]) -> None:
        assert event == "feature_mcp.invoke"
        assert attributes["scope"] == "portfolio:a"


@pytest.mark.asyncio
async def test_feature_mcp_authorizes_bounds_and_times_out() -> None:
    module = load_app_module("feature-mcp", "mcp_server")
    api = Api()
    service = module.FeatureMcpService(
        api=api,
        grants={"feature-agent": {"portfolio:a"}},
        trace_sink=Trace(),
        max_calls=1,
    )
    payload = {
        "agent_identity": "feature-agent",
        "scope": "portfolio:a",
        "user_id": "u1",
        "feature_names": ["risk"],
        "chunk_id": "c1",
    }
    assert (await service.invoke(payload)).error == "tool_budget_exhausted"
    assert api.calls == 0
    payload["chunk_id"] = None
    payload["scope"] = "portfolio:b"
    assert (await service.invoke(payload)).error == "forbidden"
    assert api.calls == 0

    timeout_service = module.FeatureMcpService(
        api=Api(delay=0.02),
        grants={"feature-agent": {"portfolio:a"}},
        trace_sink=Trace(),
        timeout_seconds=0.001,
    )
    payload["scope"] = "portfolio:a"
    assert (await timeout_service.invoke(payload)).error == "timeout"
