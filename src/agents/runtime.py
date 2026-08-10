"""HTTP runtime for the three Phase 2 agents.

The runtime only assembles the tested agent classes with MCP and model
transports. Agent reasoning, scope enforcement and hop bounds remain in the
domain modules.
"""

from __future__ import annotations

import json
import os
import time
from contextlib import nullcontext
from typing import Any
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, Request, Response, status
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pydantic import BaseModel, ConfigDict, Field

from src.agents.coordinator import Coordinator
from src.agents.drift_agent import DriftAgent
from src.agents.feature_agent import FeatureAgent
from src.agents.models import AgentFailure, SpecialistResponse
from src.observability.telemetry import (
    CONTENT_TYPE_LATEST,
    Telemetry,
    inject_trace_headers,
    metadata_from_headers,
    pii_finding_types,
)


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    question: str = Field(min_length=1, max_length=10_000)


class McpFeatureToolClient:
    def __init__(self, url: str, telemetry: Telemetry | None = None) -> None:
        self.url = url
        self.telemetry = telemetry

    async def lookup(self, payload: dict[str, Any]) -> dict[str, Any]:
        telemetry = self.telemetry
        span_context = (
            telemetry.span("mcp.feature.lookup_feature_context", {"tool": "lookup_feature_context"})
            if telemetry is not None
            else nullcontext()
        )
        try:
            with span_context:
                async with httpx.AsyncClient(headers=inject_trace_headers()) as http_client:
                    async with streamable_http_client(self.url, http_client=http_client) as (
                        read,
                        write,
                        _,
                    ):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            result = await session.call_tool(
                                "lookup_feature_context", {"request": payload}
                            )
            return result.structuredContent or {"ok": False, "error": "invalid_tool_response"}
        except Exception as exc:
            if telemetry is not None:
                telemetry.observe_failure("mcp.lookup_feature_context", type(exc).__name__)
            raise


class McpDriftToolClient:
    def __init__(self, url: str, telemetry: Telemetry | None = None) -> None:
        self.url = url
        self.telemetry = telemetry

    async def report(self, payload: dict[str, Any]) -> dict[str, Any]:
        telemetry = self.telemetry
        span_context = (
            telemetry.span(
                "mcp.drift.build_realtime_drift_report",
                {"tool": "build_realtime_drift_report"},
            )
            if telemetry is not None
            else nullcontext()
        )
        try:
            with span_context:
                async with httpx.AsyncClient(headers=inject_trace_headers()) as http_client:
                    async with streamable_http_client(self.url, http_client=http_client) as (
                        read,
                        write,
                        _,
                    ):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            result = await session.call_tool(
                                "build_realtime_drift_report", {"request": payload}
                            )
            return result.structuredContent or {"ok": False, "error": "invalid_tool_response"}
        except Exception as exc:
            if telemetry is not None:
                telemetry.observe_failure("mcp.build_realtime_drift_report", type(exc).__name__)
            raise


class OpenAICompatibleRenderer:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 30.0,
        telemetry: Telemetry | None = None,
    ) -> None:
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.telemetry = telemetry

    async def render(self, question: str, context: str) -> str:
        telemetry = self.telemetry
        if telemetry is not None:
            for finding_type in pii_finding_types(f"{question}\n{context}"):
                telemetry.observe_pii_catch("model", finding_type)
        started = time.monotonic()
        first_response_at: float | None = None
        body: bytes
        request_headers = inject_trace_headers({"Authorization": "Bearer not-required-local-model"})
        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 256,
            "stream": True,
            "stream_options": {"include_usage": True},
            "messages": [
                {
                    "role": "system",
                    "content": "Answer only from the supplied evidence and preserve citations.",
                },
                {"role": "user", "content": f"{question}\n\nEvidence:\n{context}"},
            ],
        }
        span_context = (
            telemetry.span("model.generate", {"model": self.model})
            if telemetry is not None
            else nullcontext()
        )
        try:
            with span_context:
                async with httpx.AsyncClient(
                    timeout=self.timeout_seconds,
                    headers=request_headers,
                ) as client:
                    try:
                        async with client.stream("POST", self.url, json=payload) as response:
                            response.raise_for_status()
                            chunks: list[bytes] = []
                            async for chunk in response.aiter_bytes():
                                if chunk:
                                    if first_response_at is None:
                                        first_response_at = time.monotonic()
                                    chunks.append(chunk)
                            body = b"".join(chunks)
                    except AttributeError:
                        # Keeps small test doubles and older HTTP clients compatible.
                        response = await client.post(self.url, json=payload)
                        first_response_at = time.monotonic()
                        response.raise_for_status()
                        body = response.content
            decoded = decode_model_response(body)
            usage = decoded.get("usage") or {}
            if telemetry is not None:
                input_tokens = usage.get("prompt_tokens")
                output_tokens = usage.get("completion_tokens")
                total_tokens = usage.get("total_tokens")
                for direction, count in (
                    ("input", input_tokens),
                    ("output", output_tokens),
                    ("total", total_tokens),
                ):
                    if isinstance(count, int) and count >= 0:
                        telemetry.observe_tokens(self.model, direction, count)
                if (
                    total_tokens is None
                    and isinstance(input_tokens, int)
                    and isinstance(output_tokens, int)
                ):
                    telemetry.observe_tokens(self.model, "total", input_tokens + output_tokens)
            return str(decoded["choices"][0]["message"]["content"])
        except Exception as exc:
            if telemetry is not None:
                telemetry.observe_failure("model.generate", type(exc).__name__)
            raise
        finally:
            elapsed = time.monotonic() - started
            if telemetry is not None:
                telemetry.observe_generation(self.model, elapsed)
                if first_response_at is not None:
                    telemetry.observe_ttft(self.model, first_response_at - started)


def decode_model_response(body: bytes) -> dict[str, Any]:
    """Normalize JSON and OpenAI SSE responses to one usage/content shape."""

    try:
        decoded = json.loads(body)
        if isinstance(decoded, dict):
            return decoded
    except json.JSONDecodeError:
        pass

    content: list[str] = []
    usage: dict[str, Any] = {}
    for line in body.decode("utf-8", errors="replace").splitlines():
        if not line.startswith("data:"):
            continue
        raw = line[5:].strip()
        if raw == "[DONE]":
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and isinstance(event.get("usage"), dict):
            usage = event["usage"]
        choices = event.get("choices") if isinstance(event, dict) else None
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            continue
        delta = choices[0].get("delta")
        if isinstance(delta, dict) and isinstance(delta.get("content"), str):
            content.append(delta["content"])
        message = choices[0].get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            content.append(message["content"])
    return {"choices": [{"message": {"content": "".join(content)}}], "usage": usage}


class HttpSpecialistClient:
    def __init__(self, base_url: str, telemetry: Telemetry | None = None) -> None:
        self.base_url = base_url
        self.telemetry = telemetry

    async def run(self, request: dict[str, Any]) -> SpecialistResponse:
        try:
            span_context = (
                self.telemetry.span("agent.specialist_http.run", {"operation": "/v1/run"})
                if self.telemetry is not None
                else nullcontext()
            )
            with span_context:
                async with httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=45.0,
                    headers=inject_trace_headers(),
                ) as client:
                    response = await client.post("/v1/run", json=request)
                    response.raise_for_status()
        except httpx.HTTPError as exc:
            if self.telemetry is not None:
                self.telemetry.observe_failure("agent.specialist_http.run", type(exc).__name__)
            raise OSError(f"specialist_unavailable:{self.base_url}") from exc
        return SpecialistResponse.model_validate(response.json())


async def dependencies_ready(role: str) -> tuple[bool, list[str]]:
    """Probe only dependencies needed by this role, with a strict time bound."""
    model_url = os.getenv(
        "MODEL_BASE_URL",
        "http://agentgateway-proxy.agentgateway-system.svc.cluster.local:8080/v1",
    ).rstrip("/")

    def service_health(url: str) -> str:
        parsed = urlsplit(url)
        return f"{parsed.scheme}://{parsed.netloc}/healthz"

    if role == "feature":
        urls = [
            service_health(os.getenv("FEATURE_MCP_URL", "http://feature-mcp/mcp/")),
            f"{model_url}/models",
        ]
    elif role == "drift":
        urls = [
            service_health(os.getenv("DRIFT_MCP_URL", "http://drift-mcp/mcp/")),
            f"{model_url}/models",
        ]
    elif role == "coordinator":
        urls = [
            os.getenv("FEATURE_AGENT_URL", "http://feature-agent").rstrip("/") + "/readyz",
            os.getenv("DRIFT_AGENT_URL", "http://drift-agent").rstrip("/") + "/readyz",
        ]
    else:
        return False, [f"unsupported_role:{role}"]
    failures: list[str] = []
    async with httpx.AsyncClient(timeout=2.0, headers=inject_trace_headers()) as client:
        for url in urls:
            try:
                response = await client.get(url)
                response.raise_for_status()
            except httpx.HTTPError:
                failures.append(url)
    return not failures, failures


def create_app() -> FastAPI:
    role = os.getenv("AGENT_ROLE", "feature")
    telemetry = Telemetry(service=f"{role}-agent")
    model = OpenAICompatibleRenderer(
        os.getenv(
            "MODEL_BASE_URL",
            "http://agentgateway-proxy.agentgateway-system.svc.cluster.local:8080/v1",
        ),
        os.getenv("MODEL_NAME", "qwen2.5-0.5b-instruct"),
        telemetry=telemetry,
    )
    feature = FeatureAgent(
        McpFeatureToolClient(os.getenv("FEATURE_MCP_URL", "http://feature-mcp/mcp/"), telemetry),
        model,
        telemetry=telemetry,
    )
    drift = DriftAgent(
        McpDriftToolClient(os.getenv("DRIFT_MCP_URL", "http://drift-mcp/mcp/"), telemetry),
        model,
        telemetry=telemetry,
    )
    coordinator = Coordinator(
        HttpSpecialistClient(os.getenv("FEATURE_AGENT_URL", "http://feature-agent"), telemetry),
        HttpSpecialistClient(os.getenv("DRIFT_AGENT_URL", "http://drift-agent"), telemetry),
        max_hops=int(os.getenv("MAX_AGENT_HOPS", "2")),
        telemetry=telemetry,
    )
    application = FastAPI(title=f"{role}-agent", version="1.0.0")
    application.state.telemetry = telemetry

    @application.middleware("http")
    async def telemetry_middleware(request: Request, call_next):
        started = time.monotonic()
        route = request.url.path
        telemetry.request_in_flight(route, 1)
        metadata = metadata_from_headers(request.headers).as_attributes()
        try:
            with telemetry.span(
                f"{role}.http_request",
                {**metadata, "operation": route, "method": request.method},
                headers=request.headers,
            ) as span:
                try:
                    response = await call_next(request)
                except Exception:
                    telemetry.observe_http(route, 500, time.monotonic() - started, request.method)
                    telemetry.observe_failure("http.request", "exception")
                    raise
                if span is not None:
                    span.set_attribute("status_code", response.status_code)
                telemetry.observe_http(
                    route,
                    response.status_code,
                    time.monotonic() - started,
                    request.method,
                )
                return response
        finally:
            telemetry.request_in_flight(route, -1)

    @application.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "role": role}

    @application.get("/readyz")
    async def readyz(response: Response) -> dict[str, Any]:
        ready, failures = await dependencies_ready(role)
        if not ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "ready" if ready else "not_ready", "role": role, "failures": failures}

    @application.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(content=telemetry.render(), media_type=CONTENT_TYPE_LATEST)

    @application.post("/v1/run")
    async def run(payload: dict[str, Any]) -> dict[str, Any]:
        RunRequest.model_validate(payload)
        if role == "feature":
            result: SpecialistResponse | AgentFailure = await feature.run(payload)
        elif role == "drift":
            result = await drift.run(payload)
        elif role == "coordinator":
            result = await coordinator.coordinate(payload)
        else:
            result = AgentFailure(error=f"unsupported agent role: {role}")
        return result.model_dump()

    return application


app = create_app()
