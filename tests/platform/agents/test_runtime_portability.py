from __future__ import annotations

import json
from collections import Counter
from typing import Any

import httpx
import pytest

from src.agents.runtime import HttpSpecialistClient, McpFeatureToolClient, create_app
from src.llm.http_endpoint import HttpEndpoint

_RUN = {
    "question": "What does the evidence show?",
    "feature_request": {"user_id": "NVL", "feature_names": ["risk"], "scope": "features:read"},
    "drift_request": {"rows": [{"ticker": "NVL"}], "scenario": {}, "scope": "drift:read"},
}
_ENDPOINT_KEYS = (
    "MODEL_BASE_URL",
    "FEATURE_MCP_URL",
    "DRIFT_MCP_URL",
    "FEATURE_AGENT_URL",
    "DRIFT_AGENT_URL",
    "FEATURE_MCP_HEALTH_URL",
    "DRIFT_MCP_HEALTH_URL",
    "MODEL_API_TOKEN",
    "FEATURE_MCP_TOKEN",
    "DRIFT_MCP_TOKEN",
    "FEATURE_AGENT_TOKEN",
    "DRIFT_AGENT_TOKEN",
)


@pytest.fixture(autouse=True)
def clear_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (*_ENDPOINT_KEYS, "MAX_AGENT_HOPS", "AGENT_TIMEOUT_SECONDS"):
        monkeypatch.delenv(key, raising=False)


@pytest.mark.asyncio
@pytest.mark.parametrize("alternate", [False, True], ids=["loopback", "alternate-https"])
async def test_agents_use_configured_transports_and_preserve_answers(
    monkeypatch: pytest.MonkeyPatch, alternate: bool
) -> None:
    model_origin = "https://model.example.test" if alternate else "http://127.0.0.1:8100"
    mcp_origin = "https://mcp.example.test" if alternate else "http://127.0.0.1:8200"
    agent_origin = "https://agents.example.test" if alternate else "http://127.0.0.1:8300"
    monitor_url = "https://probe.example.test/ready" if alternate else f"{mcp_origin}/mcp-readyz"
    model_base = f"{model_origin}/model/v1"
    feature_mcp = f"{mcp_origin}/features/mcp/"
    drift_mcp = f"{mcp_origin}/drift/mcp/"
    feature_agent = f"{agent_origin}/features"
    drift_agent = f"{agent_origin}/drift"
    for key, value in {
        "MODEL_BASE_URL": model_base,
        "FEATURE_MCP_URL": feature_mcp,
        "DRIFT_MCP_URL": drift_mcp,
        "FEATURE_AGENT_URL": feature_agent,
        "DRIFT_AGENT_URL": drift_agent,
    }.items():
        monkeypatch.setenv(key, value)
    if alternate:
        monkeypatch.setenv("FEATURE_MCP_HEALTH_URL", monitor_url)
        for key in (
            "MODEL_API_TOKEN",
            "FEATURE_MCP_TOKEN",
            "DRIFT_MCP_TOKEN",
            "FEATURE_AGENT_TOKEN",
            "DRIFT_AGENT_TOKEN",
        ):
            monkeypatch.setenv(key, key.lower())

    for role in ("feature", "drift", "coordinator"):
        monkeypatch.setenv("AGENT_ROLE", role)
        if role == "feature":
            feature_app = create_app()
        elif role == "drift":
            drift_app = create_app()
        else:
            coordinator_app = create_app()

    specialists = {
        feature_agent: (
            httpx.ASGITransport(app=feature_app, raise_app_exceptions=False),
            "feature_agent_token",
        ),
        drift_agent: (
            httpx.ASGITransport(app=drift_app, raise_app_exceptions=False),
            "drift_agent_token",
        ),
    }
    called: Counter[tuple[str, str]] = Counter()
    tools_available = True

    def check_auth(request: httpx.Request, token: str | None) -> None:
        expected = f"Bearer {token}" if alternate and token else None
        assert request.headers.get("Authorization") == expected

    async def upstream(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        called[(request.method, url)] += 1
        for base, (transport, token) in specialists.items():
            if url in {f"{base}/readyz", f"{base}/v1/run"}:
                check_auth(request, token)
                return await transport.handle_async_request(
                    httpx.Request(
                        request.method,
                        request.url.copy_with(path=url.removeprefix(base)),
                        headers=request.headers,
                        content=await request.aread(),
                    )
                )
        if url == monitor_url and alternate:
            check_auth(request, None)
            return httpx.Response(200, json={"status": "ok"})
        if url == f"{mcp_origin}/mcp-readyz":
            check_auth(request, "drift_mcp_token")
            return httpx.Response(200, json={"status": "ok"})
        if url in {f"{model_base}/models", f"{model_base}/chat/completions"}:
            check_auth(request, "model_api_token")
            if request.method == "GET":
                return httpx.Response(200, json={"data": []})
            body = json.loads(request.content)
            assert body["stream"] is True
            assert "Evidence:" in body["messages"][-1]["content"]
            return httpx.Response(200, json={"choices": [{"message": {"content": "Evidence"}}]})
        assert url in {feature_mcp, drift_mcp} and request.method == "POST"
        check_auth(request, "feature_mcp_token" if url == feature_mcp else "drift_mcp_token")
        body = json.loads(request.content)
        result: dict[str, Any]
        if body["method"] == "initialize":
            result = {
                "protocolVersion": body["params"]["protocolVersion"],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "portable-mock", "version": "1"},
            }
        elif body["method"] == "notifications/initialized":
            return httpx.Response(202)
        elif body["method"] == "tools/list":
            result = {
                "tools": [
                    {"name": name, "inputSchema": {"type": "object"}}
                    for name in ("lookup_feature_context", "build_realtime_drift_report")
                ]
            }
        else:
            assert body["method"] == "tools/call"
            tool_name = body["params"]["name"]
            arguments = body["params"]["arguments"]["request"]
            if url == feature_mcp:
                assert tool_name == "lookup_feature_context"
                assert arguments["user_id"] == "NVL"
                assert arguments["scope"] == "features:read"
                data = {"features": {"risk": 0.5}}
            else:
                assert tool_name == "build_realtime_drift_report"
                assert arguments["scope"] == "drift:read"
                data = {"report": {"scenario": "portable"}}
            result = {
                "content": [],
                "structuredContent": (
                    {"ok": True, "data": data}
                    if tools_available
                    else {"ok": False, "error": "api_error"}
                ),
            }
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": result})

    client_type = httpx.AsyncClient
    mock_transport = httpx.MockTransport(upstream)

    def outbound(**kwargs: Any) -> httpx.AsyncClient:
        return client_type(transport=mock_transport, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", outbound)
    async with client_type(
        transport=httpx.ASGITransport(app=coordinator_app), base_url="http://runtime.test"
    ) as application:
        ready = await application.get("/readyz")
        response = await application.post("/v1/run", json=_RUN)
        tools_available = False
        unavailable = await application.post("/v1/run", json=_RUN)

    assert ready.json() == {"status": "ready", "role": "coordinator", "failures": []}
    assert response.status_code == 200
    result = response.json()
    assert result["answer"] == "[feature] Evidence\n\n[drift] Evidence"
    assert result["hops_used"] == 1
    assert [citation["source_uri"] for citation in result["citations"]] == [
        "feature://user/NVL",
        "drift://scenario/portable",
    ]
    assert unavailable.status_code == 200
    failed = unavailable.json()
    assert failed["status"] == "failed"
    assert failed["decision"] == "stop"
    assert failed["error"].startswith("specialist_unavailable:")
    assert "answer" not in failed
    assert called[("POST", f"{model_base}/chat/completions")] == 2
    assert called[("GET", monitor_url)] == (1 if alternate else 2)
    assert called[("POST", feature_mcp)] >= 2
    assert called[("POST", drift_mcp)] >= 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "env", "missing"),
    [
        ("feature", {}, ["FEATURE_MCP_URL", "MODEL_BASE_URL"]),
        ("drift", {"DRIFT_MCP_URL": "http://127.0.0.1:8200/mcp/"}, ["MODEL_BASE_URL"]),
        (
            "feature",
            {
                "FEATURE_MCP_URL": "http://127.0.0.1:8200/mcp/",
                "MODEL_BASE_URL": "https://region.example.test:invalid/v1",
            },
            ["MODEL_BASE_URL"],
        ),
        (
            "feature",
            {
                "FEATURE_MCP_URL": "http://127.0.0.1:8200/mcp/",
                "MODEL_BASE_URL": "http://999.1.2.3/v1",
            },
            ["MODEL_BASE_URL"],
        ),
        (
            "feature",
            {
                "FEATURE_MCP_URL": "http://127.0.0.1:8200/mcp/",
                "MODEL_BASE_URL": "http://model.example.test/v1",
                "MODEL_API_TOKEN": "transport-fixture-only",
            },
            ["MODEL_BASE_URL"],
        ),
        (
            "feature",
            {
                "FEATURE_MCP_URL": "http://127.0.0.1:8200/mcp/",
                "MODEL_BASE_URL": "http://127.0.0.1:8100/v1",
                "FEATURE_MCP_HEALTH_URL": "file:///etc/host",
            },
            ["FEATURE_MCP_HEALTH_URL"],
        ),
        (
            "coordinator",
            {"FEATURE_AGENT_URL": "https://feature.region.example.test"},
            ["DRIFT_AGENT_URL"],
        ),
        (
            "coordinator",
            {
                "FEATURE_AGENT_URL": "https://feature.region.example.test",
                "DRIFT_AGENT_URL": "https://drift.region.example.test",
                "MAX_AGENT_HOPS": "0",
                "AGENT_TIMEOUT_SECONDS": "nan",
            },
            ["MAX_AGENT_HOPS", "AGENT_TIMEOUT_SECONDS"],
        ),
    ],
)
async def test_roles_fail_closed_before_transport_when_configuration_is_incomplete(
    monkeypatch: pytest.MonkeyPatch, role: str, env: dict[str, str], missing: list[str]
) -> None:
    monkeypatch.setenv("AGENT_ROLE", role)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    app = create_app()
    client_type = httpx.AsyncClient

    def unexpected_outbound(**_kwargs: Any) -> httpx.AsyncClient:
        pytest.fail("incomplete configuration must not create an outbound client")

    monkeypatch.setattr(httpx, "AsyncClient", unexpected_outbound)
    async with client_type(
        transport=httpx.ASGITransport(app=app), base_url="http://app.test"
    ) as client:
        assert (await client.get("/healthz")).json() == {"status": "ok", "role": role}
        ready = await client.get("/readyz")
        payload = (
            _RUN
            if role == "coordinator"
            else {"question": _RUN["question"], **_RUN[f"{role}_request"]}
        )
        response = await client.post("/v1/run", json=payload)

    assert ready.status_code == 503
    assert ready.json() == {"status": "not_ready", "role": role, "failures": missing}
    assert response.status_code == 200
    assert response.json() == {
        "status": "failed",
        "decision": "stop",
        "error": "dependency_unavailable",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("token", [None, "test-fixture"])
async def test_plaintext_transports_are_direct_and_do_not_expose_redirects(
    monkeypatch, token: str | None
) -> None:
    base = "http://127.0.0.1:8300"
    destination = f"{base}/unexpected?signature=not-for-diagnostics"
    calls: list[str] = []
    client_type = httpx.AsyncClient

    def redirect(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        assert request.headers.get("Authorization") == (f"Bearer {token}" if token else None)
        return httpx.Response(307, headers={"Location": destination})

    def outbound(**kwargs: Any) -> httpx.AsyncClient:
        assert kwargs["trust_env"] is False
        return client_type(transport=httpx.MockTransport(redirect), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", outbound)
    specialist = HttpSpecialistClient(HttpEndpoint(base, token))
    with pytest.raises(OSError, match="specialist_unavailable") as blocked:
        await specialist.run(_RUN)
    assert "not-for-diagnostics" not in str(blocked.value.__cause__)
    mcp = McpFeatureToolClient(HttpEndpoint(base + "/mcp/", token))
    with pytest.raises(ExceptionGroup) as refused:
        await mcp.lookup(_RUN)
    assert "not-for-diagnostics" not in repr(refused.value)
    assert calls == [base + "/v1/run", base + "/mcp/"]
