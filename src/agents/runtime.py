"""HTTP runtime for the three Phase 2 agents.

The runtime only assembles the tested agent classes with MCP and model
transports. Agent reasoning, scope enforcement and hop bounds remain in the
domain modules.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, Response, status
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pydantic import BaseModel, ConfigDict, Field

from src.agents.coordinator import Coordinator
from src.agents.drift_agent import DriftAgent
from src.agents.feature_agent import FeatureAgent
from src.agents.models import AgentFailure, SpecialistResponse


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    question: str = Field(min_length=1, max_length=10_000)


class McpFeatureToolClient:
    def __init__(self, url: str) -> None:
        self.url = url

    async def lookup(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with streamable_http_client(self.url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("lookup_feature_context", {"request": payload})
        return result.structuredContent or {"ok": False, "error": "invalid_tool_response"}


class McpDriftToolClient:
    def __init__(self, url: str) -> None:
        self.url = url

    async def report(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with streamable_http_client(self.url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "build_realtime_drift_report", {"request": payload}
                )
        return result.structuredContent or {"ok": False, "error": "invalid_tool_response"}


class OpenAICompatibleRenderer:
    def __init__(self, base_url: str, model: str, timeout_seconds: float = 30.0) -> None:
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def render(self, question: str, context: str) -> str:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                self.url,
                headers={"Authorization": "Bearer not-required-local-model"},
                json={
                    "model": self.model,
                    "temperature": 0,
                    "max_tokens": 256,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Answer only from the supplied evidence and preserve citations."
                            ),
                        },
                        {"role": "user", "content": f"{question}\n\nEvidence:\n{context}"},
                    ],
                },
            )
            response.raise_for_status()
        return str(response.json()["choices"][0]["message"]["content"])


class HttpSpecialistClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    async def run(self, request: dict[str, Any]) -> SpecialistResponse:
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=45.0) as client:
                response = await client.post("/v1/run", json=request)
                response.raise_for_status()
        except httpx.HTTPError as exc:
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
    async with httpx.AsyncClient(timeout=2.0) as client:
        for url in urls:
            try:
                response = await client.get(url)
                response.raise_for_status()
            except httpx.HTTPError:
                failures.append(url)
    return not failures, failures


def create_app() -> FastAPI:
    role = os.getenv("AGENT_ROLE", "feature")
    model = OpenAICompatibleRenderer(
        os.getenv(
            "MODEL_BASE_URL",
            "http://agentgateway-proxy.agentgateway-system.svc.cluster.local:8080/v1",
        ),
        os.getenv("MODEL_NAME", "qwen2.5-0.5b-instruct"),
    )
    feature = FeatureAgent(
        McpFeatureToolClient(os.getenv("FEATURE_MCP_URL", "http://feature-mcp/mcp/")), model
    )
    drift = DriftAgent(
        McpDriftToolClient(os.getenv("DRIFT_MCP_URL", "http://drift-mcp/mcp/")), model
    )
    coordinator = Coordinator(
        HttpSpecialistClient(os.getenv("FEATURE_AGENT_URL", "http://feature-agent")),
        HttpSpecialistClient(os.getenv("DRIFT_AGENT_URL", "http://drift-agent")),
        max_hops=int(os.getenv("MAX_AGENT_HOPS", "2")),
    )
    application = FastAPI(title=f"{role}-agent", version="1.0.0")

    @application.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "role": role}

    @application.get("/readyz")
    async def readyz(response: Response) -> dict[str, Any]:
        ready, failures = await dependencies_ready(role)
        if not ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "ready" if ready else "not_ready", "role": role, "failures": failures}

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
