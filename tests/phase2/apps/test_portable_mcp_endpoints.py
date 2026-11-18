from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from .conftest import load_app_module

_TOOL_CALLS = {
    "feature": (
        "lookup_feature_context",
        {"user_id": "NVL", "feature_names": ["risk"], "chunk_id": "c1"},
    ),
    "drift": ("build_realtime_drift_report", {"rows": [{"ticker": "NVL"}], "scenario": {}}),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["feature", "drift"])
@pytest.mark.parametrize("alternate", [False, True], ids=["loopback", "alternate-https"])
async def test_mcp_forwards_scoped_http_queries_to_configured_business_api(
    monkeypatch: pytest.MonkeyPatch, kind: str, alternate: bool
) -> None:
    origin = "https://mcp.example.test" if alternate else "http://127.0.0.1:8300"
    upstream_base = "https://api.example.test/regional" if alternate else "http://127.0.0.1:8400"
    module = load_app_module(f"{kind}-mcp", "main")
    monkeypatch.setenv(f"{kind.upper()}_API_BASE_URL", upstream_base)
    monkeypatch.setenv(f"{kind.upper()}_API_TOKEN", "transport-test" if alternate else "")
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", " mcp.example.test " if alternate else "")
    monkeypatch.setenv("MCP_AUTH_GRANTS", json.dumps({f"{kind}-agent": ["company:read"]}))
    app = module.create_app()
    client_type = httpx.AsyncClient
    routes = {
        "/v1/features/by-id": (
            {"user_id": "NVL", "feature_names": ["risk"]},
            {"features": {"risk": 0.5}},
        ),
        "/v1/rag/by-id": ({"chunk_id": "c1"}, {"chunk_id": "c1"}),
        "/v1/drift/report": ({"rows": [{"ticker": "NVL"}], "scenario": {}}, {"report": {}}),
    }
    calls: list[str] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        assert url.startswith(upstream_base + "/")
        if request.method == "GET":
            assert url == upstream_base + "/readyz"
            assert request.headers.get("Authorization") == (
                "Bearer transport-test" if alternate else None
            )
            return httpx.Response(200, json={"status": "ready"})
        assert request.method == "POST"
        expected_auth = "Bearer transport-test" if alternate else None
        assert request.headers.get("Authorization") == expected_auth
        path = url.removeprefix(upstream_base)
        expected, result = routes[path]
        assert json.loads(request.content) == expected
        calls.append(path)
        return httpx.Response(200, json=result)

    def outbound(**kwargs: Any) -> httpx.AsyncClient:
        return client_type(transport=httpx.MockTransport(upstream), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", outbound)
    tool, body = _TOOL_CALLS[kind]
    async with (
        app.router.lifespan_context(app),
        client_type(transport=httpx.ASGITransport(app=app), base_url=origin) as incoming,
    ):
        assert (await incoming.get("/mcp-readyz")).json() == {"status": "ready"}
        for headers, status in [("host", 421), ("origin", 403)]:
            rejected = await incoming.post(
                "/mcp/", headers={headers: "https://untrusted.example.test"}, json={}
            )
            assert rejected.status_code == status
        async with streamable_http_client(f"{origin}/mcp/", http_client=incoming) as (
            read,
            write,
            _,
        ):
            async with ClientSession(read, write) as session:
                await session.initialize()
                request = {**body, "agent_identity": f"{kind}-agent", "scope": "company:read"}
                forbidden = await session.call_tool(
                    tool, {"request": {**request, "scope": "other"}}
                )
                assert forbidden.structuredContent == {
                    "ok": False,
                    "data": None,
                    "error": "forbidden",
                }
                assert not calls
                result = await session.call_tool(tool, {"request": request})

    expected_calls = (
        ["/v1/features/by-id", "/v1/rag/by-id"] if kind == "feature" else ["/v1/drift/report"]
    )
    assert calls == expected_calls
    if kind == "feature":
        data = {"features": {"risk": 0.5}, "rag": {"chunk_id": "c1"}}
    else:
        data = {"report": {}}
    assert result.structuredContent == {"ok": True, "data": data, "error": None}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "url"),
    [
        ("feature", None),
        ("feature", "https://api.example.test:wrong"),
        ("drift", "https://api.example.test:wrong"),
        ("drift", ""),
    ],
)
async def test_mcp_api_configuration_failure_is_closed_before_outbound_io(
    monkeypatch: pytest.MonkeyPatch, kind: str, url: str | None
) -> None:
    url_key = f"{kind.upper()}_API_BASE_URL"
    if url is None:
        monkeypatch.delenv(url_key, raising=False)
    else:
        monkeypatch.setenv(url_key, url)
    monkeypatch.delenv(f"{kind.upper()}_API_TOKEN", raising=False)
    monkeypatch.setenv("MCP_AUTH_GRANTS", json.dumps({f"{kind}-agent": ["company:read"]}))
    app = load_app_module(f"{kind}-mcp", "main").create_app()
    client_type = httpx.AsyncClient

    def unexpected_outbound(**_kwargs: Any) -> httpx.AsyncClient:
        pytest.fail("invalid or absent API configuration must not create an outbound client")

    monkeypatch.setattr(httpx, "AsyncClient", unexpected_outbound)
    tool, body = _TOOL_CALLS[kind]
    origin = "http://127.0.0.1:8300"
    async with (
        app.router.lifespan_context(app),
        client_type(transport=httpx.ASGITransport(app=app), base_url=origin) as incoming,
    ):
        assert (await incoming.get("/mcp-readyz")).status_code == 503
        async with streamable_http_client(f"{origin}/mcp/", http_client=incoming) as (
            read,
            write,
            _,
        ):
            async with ClientSession(read, write) as session:
                await session.initialize()
                request = {**body, "agent_identity": f"{kind}-agent", "scope": "company:read"}
                result = await session.call_tool(tool, {"request": request})
    assert result.structuredContent == {"ok": False, "data": None, "error": "api_error"}
