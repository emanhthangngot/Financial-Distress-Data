"""HTTP runtime for the three platform agents.

The runtime only assembles the tested agent classes with MCP and model
transports. Agent reasoning, scope enforcement and hop bounds remain in the
domain modules.
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from collections.abc import Awaitable, Callable
from contextlib import nullcontext
from typing import Any
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, Request, Response, status
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pydantic import BaseModel, ConfigDict, Field

from src.agents.coordinator import CoordinatorResponse
from src.agents.drift_agent import DriftAgent
from src.agents.feature_agent import FeatureAgent
from src.agents.langgraph_runtime import build_langgraph_coordinator, coordinate_langgraph
from src.agents.models import AgentFailure, SpecialistResponse
from src.llm.http_endpoint import HttpEndpoint, absolute_http_url, reject_redirect
from src.observability.telemetry import (
    CONTENT_TYPE_LATEST,
    Telemetry,
    metadata_from_headers,
    pii_finding_types,
)

LOGGER = logging.getLogger(__name__)


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    question: str = Field(min_length=1, max_length=10_000)


class McpFeatureToolClient:
    def __init__(self, endpoint: HttpEndpoint, telemetry: Telemetry | None = None) -> None:
        self.endpoint = endpoint
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
                async with httpx.AsyncClient(
                    headers=self.endpoint.headers(),
                    trust_env=self.endpoint.trust_env,
                    event_hooks={"response": [reject_redirect]},
                ) as http_client:
                    async with streamable_http_client(
                        self.endpoint.url, http_client=http_client
                    ) as (read, write, _):
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
    def __init__(self, endpoint: HttpEndpoint, telemetry: Telemetry | None = None) -> None:
        self.endpoint = endpoint
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
                async with httpx.AsyncClient(
                    headers=self.endpoint.headers(),
                    trust_env=self.endpoint.trust_env,
                    event_hooks={"response": [reject_redirect]},
                ) as http_client:
                    async with streamable_http_client(
                        self.endpoint.url, http_client=http_client
                    ) as (read, write, _):
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
        endpoint: HttpEndpoint,
        model: str,
        timeout_seconds: float = 30.0,
        telemetry: Telemetry | None = None,
    ) -> None:
        self.endpoint = endpoint.at("/chat/completions")
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
        request_headers = self.endpoint.headers()
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
                    trust_env=self.endpoint.trust_env,
                    event_hooks={"response": [reject_redirect]},
                    headers=request_headers,
                ) as client:
                    try:
                        async with client.stream(
                            "POST", self.endpoint.url, json=payload
                        ) as response:
                            if not response.is_success:
                                raise RuntimeError("model_unavailable")
                            chunks: list[bytes] = []
                            async for chunk in response.aiter_bytes():
                                if chunk:
                                    if first_response_at is None:
                                        first_response_at = time.monotonic()
                                    chunks.append(chunk)
                            body = b"".join(chunks)
                    except AttributeError:
                        # Keeps small test doubles and older HTTP clients compatible.
                        response = await client.post(self.endpoint.url, json=payload)
                        first_response_at = time.monotonic()
                        if not response.is_success:
                            raise RuntimeError("model_unavailable") from None
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
    def __init__(self, endpoint: HttpEndpoint, telemetry: Telemetry | None = None) -> None:
        self.endpoint = endpoint
        self.run_url = endpoint.at("/v1/run").url
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
                    trust_env=self.endpoint.trust_env,
                    event_hooks={"response": [reject_redirect]},
                    timeout=45.0,
                    headers=self.endpoint.headers(),
                ) as client:
                    response = await client.post(self.run_url, json=request)
                    if not response.is_success:
                        raise httpx.HTTPError("specialist_unavailable")
            return SpecialistResponse.model_validate(response.json())
        except (httpx.HTTPError, ValueError) as exc:
            if self.telemetry is not None:
                self.telemetry.observe_failure("agent.specialist_http.run", type(exc).__name__)
            raise OSError(f"specialist_unavailable:{self.endpoint.url}") from exc


def mcp_health_endpoint(url_key: str, endpoint: HttpEndpoint) -> HttpEndpoint | None:
    health_key = url_key.removesuffix("_URL") + "_HEALTH_URL"
    override = os.getenv(health_key)
    if override is None:
        parsed = urlsplit(endpoint.url)
        return HttpEndpoint(f"{parsed.scheme}://{parsed.netloc}/mcp-readyz", endpoint.token)
    url = absolute_http_url(override)
    if url is None:
        return None
    health = HttpEndpoint(url)
    return HttpEndpoint(url, endpoint.token) if health.origin == endpoint.origin else health


async def dependencies_ready(probes: tuple[HttpEndpoint, ...]) -> list[str]:
    """Probe only the configured dependencies needed by this role."""
    failures: list[str] = []
    for endpoint in probes:
        async with httpx.AsyncClient(
            timeout=2.0,
            trust_env=endpoint.trust_env,
            event_hooks={"response": [reject_redirect]},
        ) as client:
            try:
                response = await client.get(endpoint.url, headers=endpoint.headers())
                response.raise_for_status()
            except (httpx.HTTPError, httpx.InvalidURL):
                failures.append(endpoint.url)
    return failures


def create_app() -> FastAPI:
    role = os.getenv("AGENT_ROLE", "feature")
    telemetry = Telemetry(service=f"{role}-agent")
    failures: list[str] = []
    probes: tuple[HttpEndpoint, ...] = ()
    run_agent: (
        Callable[
            [dict[str, Any]], Awaitable[SpecialistResponse | CoordinatorResponse | AgentFailure]
        ]
        | None
    ) = None

    def configured(url_key: str, token_key: str) -> HttpEndpoint | None:
        endpoint = HttpEndpoint.from_env(url_key, token_key)
        if endpoint is None:
            failures.append(url_key)
        return endpoint

    if role in {"feature", "drift"}:
        mcp_key = f"{role.upper()}_MCP"
        mcp = configured(f"{mcp_key}_URL", f"{mcp_key}_TOKEN")
        model_endpoint = configured("MODEL_BASE_URL", "MODEL_API_TOKEN")
        if mcp is not None and model_endpoint is not None:
            health = mcp_health_endpoint(f"{mcp_key}_URL", mcp)
            if health is None:
                failures.append(f"{mcp_key}_HEALTH_URL")
            else:
                model = OpenAICompatibleRenderer(
                    model_endpoint,
                    os.getenv("MODEL_NAME", "qwen2.5-0.5b-instruct"),
                    telemetry=telemetry,
                )
                probes = (health, model_endpoint.at("/models"))
                if role == "feature":
                    run_agent = FeatureAgent(
                        McpFeatureToolClient(mcp, telemetry), model, telemetry=telemetry
                    ).run
                else:
                    run_agent = DriftAgent(
                        McpDriftToolClient(mcp, telemetry), model, telemetry=telemetry
                    ).run
    elif role == "coordinator":
        feature = configured("FEATURE_AGENT_URL", "FEATURE_AGENT_TOKEN")
        drift = configured("DRIFT_AGENT_URL", "DRIFT_AGENT_TOKEN")
        try:
            max_hops = int(os.getenv("MAX_AGENT_HOPS", "2"))
        except ValueError:
            max_hops = 0
        if max_hops < 1:
            failures.append("MAX_AGENT_HOPS")
        try:
            timeout_seconds = float(os.getenv("AGENT_TIMEOUT_SECONDS", "50.0"))
        except ValueError:
            timeout_seconds = 0.0
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            failures.append("AGENT_TIMEOUT_SECONDS")
        if feature is not None and drift is not None and not failures:
            probes = (feature.at("/readyz"), drift.at("/readyz"))
            graph = build_langgraph_coordinator(
                HttpSpecialistClient(feature, telemetry),
                HttpSpecialistClient(drift, telemetry),
                max_hops=max_hops,
                max_parallel=2,
            )

            async def run_coordinator(
                payload: dict[str, Any],
            ) -> CoordinatorResponse | AgentFailure:
                operation = "agent.coordinator.coordinate"
                telemetry.observe_agent_call("coordinator")
                try:
                    with telemetry.span(operation, {"agent": "coordinator"}):
                        result = await coordinate_langgraph(
                            graph, payload, timeout_seconds=timeout_seconds
                        )
                except Exception as exc:
                    telemetry.observe_failure(operation, type(exc).__name__)
                    raise
                if isinstance(result, AgentFailure):
                    telemetry.observe_failure(operation, result.error)
                    LOGGER.warning("coordinator agent failure: %s", result.error)
                return result

            run_agent = run_coordinator
    else:
        failures.append(f"unsupported_role:{role}")
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
        unavailable = failures or await dependencies_ready(probes)
        if unavailable:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready" if unavailable else "ready",
            "role": role,
            "failures": unavailable,
        }

    @application.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(content=telemetry.render(), media_type=CONTENT_TYPE_LATEST)

    @application.post("/v1/run")
    async def run(payload: dict[str, Any]) -> dict[str, Any]:
        RunRequest.model_validate(payload)
        result: SpecialistResponse | CoordinatorResponse | AgentFailure
        if run_agent is None:
            result = AgentFailure(
                error=(
                    "dependency_unavailable"
                    if role in {"feature", "drift", "coordinator"}
                    else f"unsupported agent role: {role}"
                )
            )
        else:
            result = await run_agent(payload)
        return result.model_dump()

    return application


app = create_app()
