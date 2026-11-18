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

from src.llm.http_endpoint import HttpEndpoint, endpoint_ready, mcp_allowed_hosts, reject_redirect
from src.observability.telemetry import Telemetry, redact_fields

_DEFAULT_TELEMETRY = Telemetry("drift-mcp")


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
            json.dumps(
                redact_fields({"event": event, **attributes}),
                sort_keys=True,
            )
        )


class HttpxDriftApiClient:
    def __init__(self, endpoint: HttpEndpoint | None, timeout_seconds: float = 5.0) -> None:
        self._endpoint = endpoint
        self._timeout = timeout_seconds
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> HttpxDriftApiClient:
        if self._endpoint is not None:
            self._client = httpx.AsyncClient(
                base_url=self._endpoint.url,
                timeout=self._timeout,
                trust_env=self._endpoint.trust_env,
                event_hooks={"response": [reject_redirect]},
            )
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def ready(self) -> bool:
        return (
            self._client is not None
            and self._endpoint is not None
            and await endpoint_ready(self._client, self._endpoint.at("/readyz"))
        )

    async def report(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._client is None or self._endpoint is None:
            raise httpx.HTTPError("drift API client is unavailable")
        response = await self._client.post(
            "/v1/drift/report", json=payload, headers=self._endpoint.headers()
        )
        response.raise_for_status()
        return dict(response.json())


class InProcessDriftApiClient:
    """Call the drift domain function directly when MCP is co-located."""

    async def __aenter__(self) -> InProcessDriftApiClient:
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        return None

    async def ready(self) -> bool:
        return True

    async def report(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Keep this import lazy: main.py mounts the MCP application while it is
        # being imported, so an eager reverse import would create a cycle.
        from .main import DriftRequest, _calculate_drift

        try:
            request = DriftRequest.model_validate(payload)
        except ValueError as exc:
            raise httpx.HTTPError("drift API validation failed") from exc
        response = await asyncio.to_thread(_calculate_drift, request)
        return response.model_dump()


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
    telemetry: Telemetry | None = None

    async def invoke(self, raw: dict[str, Any]) -> ToolResult:
        telemetry = self.telemetry or _DEFAULT_TELEMETRY
        telemetry.observe_tool_call("build_realtime_drift_report")
        with telemetry.span(
            "drift_mcp.build_realtime_drift_report",
            {"tool": "build_realtime_drift_report"},
        ):
            return await self._invoke(raw, telemetry)

    async def _invoke(self, raw: dict[str, Any], telemetry: Telemetry) -> ToolResult:
        try:
            request = ToolRequest.model_validate(raw)
        except ValueError as exc:
            telemetry.observe_failure("mcp.build_realtime_drift_report", "validation_error")
            return ToolResult(ok=False, error=f"validation_error:{exc}")
        if request.scope not in self.grants.get(request.agent_identity, set()):
            telemetry.observe_failure("mcp.build_realtime_drift_report", "forbidden")
            return ToolResult(ok=False, error="forbidden")
        if self.max_calls < 1:
            telemetry.observe_failure("mcp.build_realtime_drift_report", "tool_budget_exhausted")
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
            telemetry.observe_failure("mcp.build_realtime_drift_report", "timeout")
            return ToolResult(ok=False, error="timeout")
        except httpx.HTTPError:
            telemetry.observe_failure("mcp.build_realtime_drift_report", "api_error")
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
            allowed_hosts=mcp_allowed_hosts(),
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
    api: HttpxDriftApiClient | InProcessDriftApiClient


def create_mcp_runtime(telemetry: Telemetry | None = None) -> McpRuntime:
    """Assemble transport dependencies without opening sockets or sessions."""
    api = (
        InProcessDriftApiClient()
        if os.getenv("DRIFT_API_BASE_URL") is None and not os.getenv("DRIFT_API_TOKEN")
        else HttpxDriftApiClient(HttpEndpoint.from_env("DRIFT_API_BASE_URL", "DRIFT_API_TOKEN"))
    )
    service = DriftMcpService(
        api=api,
        grants=_grants_from_env(),
        trace_sink=LoggingTraceSink(),
        telemetry=telemetry or _DEFAULT_TELEMETRY,
    )
    return McpRuntime(application=create_mcp_server(service).streamable_http_app(), api=api)
