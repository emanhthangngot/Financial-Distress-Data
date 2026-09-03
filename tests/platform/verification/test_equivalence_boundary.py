"""Equivalence-partition and boundary-value tests for both Web APIs.

The clients are fixtures backed by mocks so validation, error mapping, and
async boundaries are tested without requiring Feast, Postgres, or a cluster.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest

from tests.phase2.apps.conftest import load_app_module


@pytest.fixture()
def feature_clients() -> tuple[AsyncMock, AsyncMock]:
    features = AsyncMock()
    features.get_by_id.return_value = {"risk_score": 0.73}
    features.ready.return_value = True
    rag = AsyncMock()
    rag.get_by_id.return_value = {
        "chunk_id": "chunk-1",
        "chunk_text": "trusted fixture content",
        "source_uri": "fixture://annual-report",
    }
    rag.ready.return_value = True
    return features, rag


async def post_feature(
    payload: dict[str, Any], clients: tuple[AsyncMock, AsyncMock]
) -> httpx.Response:
    module = load_app_module("feature-mcp", "main")
    app = module.create_app(*clients, mount_mcp=False)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.post("/v1/features/by-id", json=payload)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "feature_names, expected_status",
    [
        pytest.param(["risk_score"], 200, id="valid-partition"),
        pytest.param(["risk_score"] * 64, 200, id="max-inclusive-boundary"),
        pytest.param([], 422, id="empty-partition"),
        pytest.param(["risk_score"] * 65, 422, id="max-exclusive-boundary"),
    ],
)
async def test_feature_name_partitions_and_limits(
    feature_names: list[str], expected_status: int, feature_clients: tuple[AsyncMock, AsyncMock]
) -> None:
    response = await post_feature(
        {"user_id": "AAA", "feature_names": feature_names}, feature_clients
    )
    assert response.status_code == expected_status


@pytest.mark.asyncio
async def test_unknown_but_well_formed_ticker_is_forwarded_to_the_store(
    feature_clients: tuple[AsyncMock, AsyncMock],
) -> None:
    feature_clients[0].get_by_id.return_value = {}
    response = await post_feature(
        {"user_id": "UNKNOWN", "feature_names": ["risk_score"]}, feature_clients
    )
    assert response.status_code == 200
    assert response.json() == {"user_id": "UNKNOWN", "features": {}}
    feature_clients[0].get_by_id.assert_awaited_once_with("UNKNOWN", ("risk_score",))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "start_quarter, expected_status",
    [
        pytest.param(1, 200, id="quarter-lower-boundary"),
        pytest.param(4, 200, id="quarter-upper-boundary"),
        pytest.param(0, 422, id="quarter-below-domain"),
        pytest.param(5, 422, id="quarter-above-domain"),
    ],
)
async def test_drift_quarter_boundaries(start_quarter: int, expected_status: int) -> None:
    module = load_app_module("drift-mcp", "main")
    app = module.create_app(mount_mcp=False)
    payload = {
        "rows": [{"ticker": "AAA", "close_price": 10.0}],
        "scenario": {
            "name": "market-stress",
            "seed": 7,
            "start_quarter": start_quarter,
            "affected_fraction": 1.0,
            "feature_shifts": {"close_price": {"mode": "multiplicative", "magnitude": 0.5}},
            "target_metric": "close_price",
            "observed_stat": "mean",
            "expected_direction": "increase",
            "threshold": 0.1,
        },
    }
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/v1/drift/report", json=payload)
    assert response.status_code == expected_status


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "row_count, expected_status",
    [
        pytest.param(1, 200, id="one-row-lower-boundary"),
        pytest.param(10_000, 200, id="max-rows-upper-boundary"),
        pytest.param(0, 422, id="empty-rows-partition"),
        pytest.param(10_001, 422, id="too-many-rows-partition"),
    ],
)
async def test_drift_row_limits(row_count: int, expected_status: int) -> None:
    module = load_app_module("drift-mcp", "main")
    app = module.create_app(mount_mcp=False)
    rows = [{"ticker": "AAA", "close_price": 10.0}] * row_count
    payload = {
        "rows": rows,
        "scenario": {
            "name": "market-stress",
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
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/v1/drift/report", json=payload)
    assert response.status_code == expected_status
