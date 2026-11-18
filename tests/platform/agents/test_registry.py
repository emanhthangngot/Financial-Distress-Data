from __future__ import annotations

import json

import httpx
import pytest

from src.agents.registry import create_app, load_registry


@pytest.mark.asyncio
async def test_registry_is_queryable_and_returns_registered_agent(tmp_path, monkeypatch) -> None:
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"agents": [{"name": "feature-agent", "status": "active"}]}))
    monkeypatch.setenv("AGENT_REGISTRY_PATH", str(path))
    assert load_registry()["agents"][0]["name"] == "feature-agent"
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/readyz")).json() == {"status": "ready", "agents": 1}
        assert (await client.get("/v1/agents/feature-agent")).json()["status"] == "active"
        assert (await client.get("/v1/agents/missing")).status_code == 404
