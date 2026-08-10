"""Thin MCP orchestration wrapper for the feature/RAG HTTP API."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field


class FeatureApiClient(Protocol):
    async def feature_by_id(
        self, user_id: str, feature_names: tuple[str, ...]
    ) -> dict[str, Any]: ...

    async def rag_by_id(self, chunk_id: str) -> dict[str, Any]: ...


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


class HttpxFeatureApiClient:
    """Async transport adapter to the FastAPI business API boundary."""

    def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
        self._base_url = base_url
        self._timeout = timeout_seconds
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> HttpxFeatureApiClient:
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout)
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _active_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("feature API client is not running")
        return self._client

    async def feature_by_id(self, user_id: str, feature_names: tuple[str, ...]) -> dict[str, Any]:
        response = await self._active_client().post(
            "/v1/features/by-id",
            json={"user_id": user_id, "feature_names": list(feature_names)},
        )
        response.raise_for_status()
        return dict(response.json()["features"])

    async def rag_by_id(self, chunk_id: str) -> dict[str, Any]:
        response = await self._active_client().post("/v1/rag/by-id", json={"chunk_id": chunk_id})
        response.raise_for_status()
        return dict(response.json())


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_identity: str = Field(min_length=1, max_length=128)
    scope: str = Field(min_length=1, max_length=128)
    user_id: str = Field(min_length=1, max_length=128)
    feature_names: tuple[str, ...] = Field(min_length=1, max_length=64)
    chunk_id: str | None = Field(default=None, max_length=128)


class ToolResult(BaseModel):
    ok: bool
    data: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class FeatureMcpService:
    api: FeatureApiClient
    grants: dict[str, set[str]]
    trace_sink: TraceSink
    timeout_seconds: float = 5.0
    max_calls: int = 2

    async def invoke(self, raw: dict[str, Any]) -> ToolResult:
        try:
            request = ToolRequest.model_validate(raw)
        except ValueError as exc:
            return ToolResult(ok=False, error=f"validation_error:{exc}")
        if request.scope not in self.grants.get(request.agent_identity, set()):
            return ToolResult(ok=False, error="forbidden")
        required_calls = 1 + int(request.chunk_id is not None)
        if required_calls > self.max_calls:
            return ToolResult(ok=False, error="tool_budget_exhausted")
        self.trace_sink.emit(
            "feature_mcp.invoke",
            {"agent_identity": request.agent_identity, "scope": request.scope},
        )
        try:
            features = await asyncio.wait_for(
                self.api.feature_by_id(request.user_id, request.feature_names),
                timeout=self.timeout_seconds,
            )
            data: dict[str, Any] = {"features": features}
            if request.chunk_id is not None:
                data["rag"] = await asyncio.wait_for(
                    self.api.rag_by_id(request.chunk_id), timeout=self.timeout_seconds
                )
            return ToolResult(ok=True, data=data)
        except (TimeoutError, httpx.TimeoutException):
            return ToolResult(ok=False, error="timeout")
        except httpx.HTTPError:
            return ToolResult(ok=False, error="api_error")


def create_mcp_server(service: FeatureMcpService):
    """Create the SDK server explicitly; importing this module has no side effects."""
    from mcp.server.fastmcp import FastMCP
    from mcp.server.fastmcp.server import Settings
    from mcp.server.transport_security import TransportSecuritySettings

    Settings.model_rebuild()
    server = FastMCP(
        "feature-rag-tools",
        streamable_http_path="/",
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            allowed_hosts=[
                "feature-mcp",
                "feature-mcp:*",
                "feature-mcp.phase2-data.svc.cluster.local",
                "feature-mcp.phase2-data.svc.cluster.local:*",
                "127.0.0.1:*",
                "localhost:*",
            ],
            allowed_origins=[],
        ),
    )

    @server.tool()
    async def lookup_feature_context(request: dict[str, Any]) -> dict[str, Any]:
        """Validate and forward a scoped feature/RAG lookup."""
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
    api: HttpxFeatureApiClient


def create_mcp_runtime() -> McpRuntime:
    """Assemble transport dependencies without opening sockets or sessions."""
    base_url = os.getenv("FEATURE_API_BASE_URL", "http://127.0.0.1:8000")
    api = HttpxFeatureApiClient(base_url)
    service = FeatureMcpService(
        api=api,
        grants=_grants_from_env(),
        trace_sink=LoggingTraceSink(),
    )
    return McpRuntime(application=create_mcp_server(service).streamable_http_app(), api=api)
