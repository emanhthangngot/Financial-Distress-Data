from __future__ import annotations

from typing import Any

import httpx
import pytest

from .conftest import load_app_module


def request_payload() -> dict[str, Any]:
    return {
        "rows": [
            {"ticker": "AAA", "close_price": 10.0},
            {"ticker": "BBB", "close_price": 20.0},
        ],
        "scenario": {
            "name": "market_stress",
            "seed": 7,
            "start_quarter": 1,
            "affected_fraction": 1.0,
            "feature_shifts": {"close_price": {"mode": "multiplicative", "magnitude": 0.5}},
            "target_metric": "close_price",
            "observed_stat": "mean",
            "expected_direction": "increase",
            "threshold": 0.1,
        },
    }


@pytest.mark.asyncio
async def test_drift_api_uses_domain_logic_off_thread_and_is_idempotent(monkeypatch) -> None:
    module = load_app_module("drift-mcp", "main")
    offloaded: list[str] = []

    async def to_thread(function, *args):
        offloaded.append(function.__name__)
        return function(*args)

    monkeypatch.setattr(module.asyncio, "to_thread", to_thread)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=module.create_app()), base_url="http://test"
    ) as client:
        assert (await client.get("/healthz")).status_code == 200
        assert (await client.get("/readyz")).json() == {"status": "ready"}
        first = await client.post("/v1/drift/report", json=request_payload())
        second = await client.post("/v1/drift/report", json=request_payload())
        invalid = await client.post(
            "/v1/drift/report", json={**request_payload(), "rows": [{"close_price": 10}]}
        )
    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["report"]["passed"] is True
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
    assert offloaded == ["_calculate_drift", "_calculate_drift"]


@pytest.mark.asyncio
async def test_drift_metrics_and_mcp_mount_are_exposed() -> None:
    module = load_app_module("drift-mcp", "main")
    app = module.create_app()
    assert any(getattr(route, "path", None) == "/mcp" for route in app.routes)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.get("/readyz")
        metrics = await client.get("/metrics")
    assert 'fd_http_requests_total{route="/readyz",status="200"} 1.0' in metrics.text


class Api:
    def __init__(self) -> None:
        self.calls = 0

    async def report(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        return {"report": payload["scenario"]}


class Trace:
    def emit(self, event: str, attributes: dict[str, Any]) -> None:
        assert event == "drift_mcp.invoke"


@pytest.mark.asyncio
async def test_drift_mcp_rejects_unauthorized_request_without_api_call() -> None:
    module = load_app_module("drift-mcp", "mcp_server")
    api = Api()
    service = module.DriftMcpService(
        api=api,
        grants={"drift-agent": {"portfolio:a"}},
        trace_sink=Trace(),
    )
    result = await service.invoke(
        {
            "agent_identity": "drift-agent",
            "scope": "portfolio:b",
            **request_payload(),
        }
    )
    assert result.error == "forbidden"
    assert api.calls == 0
