"""Thin MCP orchestration wrapper for the drift HTTP API."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field


class DriftApiClient(Protocol):
    async def report(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class TraceSink(Protocol):
    def emit(self, event: str, attributes: dict[str, Any]) -> None: ...


class NoopTraceSink:
    def emit(self, event: str, attributes: dict[str, Any]) -> None:
        del event, attributes


class LoggingTraceSink:
    """Emit a structured, redaction-safe MCP audit event to container logs."""

    def emit(self, event: str, attributes: dict[str, Any]) -> None:
        logging.getLogger("phase2.mcp.audit").info(
            json.dumps({"event": event, **attributes}, sort_keys=True)
        )


class HttpxDriftApiClient:
    def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
        self._base_url = base_url
        self._timeout = timeout_seconds
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> HttpxDriftApiClient:
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout)
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def report(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("drift API client is not running")
        response = await self._client.post("/v1/drift/report", json=payload)
        response.raise_for_status()
        return dict(response.json())


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_identity: str = Field(min_length=1, max_length=128)
    scope: str = Field(min_length=1, max_length=128)
    rows: list[dict[str, Any]] = Field(min_length=1, max_length=10_000)
    scenario: dict[str, Any]


class ToolResult(BaseModel):
    ok: bool
    data: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class DriftMcpService:
    api: DriftApiClient
    grants: dict[str, set[str]]
    trace_sink: TraceSink
    timeout_seconds: float = 5.0
    max_calls: int = 1

    async def invoke(self, raw: dict[str, Any]) -> ToolResult:
        try:
            request = ToolRequest.model_validate(raw)
        except ValueError as exc:
            return ToolResult(ok=False, error=f"validation_error:{exc}")
        if request.scope not in self.grants.get(request.agent_identity, set()):
            return ToolResult(ok=False, error="forbidden")
        if self.max_calls < 1:
            return ToolResult(ok=False, error="tool_budget_exhausted")
        self.trace_sink.emit(
            "drift_mcp.invoke",
            {"agent_identity": request.agent_identity, "scope": request.scope},
        )
        try:
            data = await asyncio.wait_for(
                self.api.report({"rows": request.rows, "scenario": request.scenario}),
                timeout=self.timeout_seconds,
            )
            return ToolResult(ok=True, data=data)
        except (TimeoutError, httpx.TimeoutException):
            return ToolResult(ok=False, error="timeout")
        except httpx.HTTPError:
            return ToolResult(ok=False, error="api_error")


def create_mcp_server(service: DriftMcpService):
    """Create the SDK server explicitly; importing this module has no side effects."""
    from mcp.server.fastmcp import FastMCP
    from mcp.server.fastmcp.server import Settings
    from mcp.server.transport_security import TransportSecuritySettings

    Settings.model_rebuild()
    server = FastMCP(
        "drift-tools",
        streamable_http_path="/",
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            allowed_hosts=[
                "drift-mcp",
                "drift-mcp:*",
                "drift-mcp.phase2-data.svc.cluster.local",
                "drift-mcp.phase2-data.svc.cluster.local:*",
                "127.0.0.1:*",
                "localhost:*",
            ],
            allowed_origins=[],
        ),
    )

    @server.tool()
    async def build_realtime_drift_report(request: dict[str, Any]) -> dict[str, Any]:
        """Validate and forward a scoped drift-report request."""
        return (await service.invoke(request)).model_dump()

    return server


def _grants_from_env() -> dict[str, set[str]]:
    raw = os.getenv("MCP_AUTH_GRANTS")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return {}
        return {
            str(identity): {str(scope) for scope in scopes}
            for identity, scopes in parsed.items()
            if isinstance(scopes, list)
        }
    except (TypeError, ValueError):
        return {}


@dataclass(frozen=True)
class McpRuntime:
    application: Any
    api: HttpxDriftApiClient


def create_mcp_runtime() -> McpRuntime:
    """Assemble transport dependencies without opening sockets or sessions."""
    base_url = os.getenv("DRIFT_API_BASE_URL", "http://127.0.0.1:8000")
    api = HttpxDriftApiClient(base_url)
    service = DriftMcpService(
        api=api,
        grants=_grants_from_env(),
        trace_sink=LoggingTraceSink(),
    )
    return McpRuntime(application=create_mcp_server(service).streamable_http_app(), api=api)
