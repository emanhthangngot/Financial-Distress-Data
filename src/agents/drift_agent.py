"""Drift specialist with one scoped MCP call per request."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from src.agents.models import Citation, SpecialistResponse


class DriftToolClient(Protocol):
    async def report(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class AnswerRenderer(Protocol):
    async def render(self, question: str, context: str) -> str: ...


class DriftAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=10_000)
    rows: list[dict[str, Any]] = Field(min_length=1, max_length=10_000)
    scenario: dict[str, Any]
    scope: str = Field(min_length=1, max_length=128)
    tool_budget: int = Field(default=1, ge=1, le=1)


@dataclass
class DriftAgent:
    tool: DriftToolClient
    renderer: AnswerRenderer
    identity: str = "drift-agent"

    async def run(self, raw: DriftAgentRequest | dict[str, Any]) -> SpecialistResponse:
        request = (
            raw if isinstance(raw, DriftAgentRequest) else DriftAgentRequest.model_validate(raw)
        )
        result = await self.tool.report(
            {
                "agent_identity": self.identity,
                "scope": request.scope,
                "rows": request.rows,
                "scenario": request.scenario,
            }
        )
        if not result.get("ok"):
            raise RuntimeError(str(result.get("error", "drift tool failed")))
        data = result.get("data") or {}
        report = data.get("report", data)
        answer = await self.renderer.render(request.question, f"drift_report={report}")
        scenario_name = str(report.get("scenario", request.scenario.get("name", "unknown")))
        return SpecialistResponse(
            specialist="drift",
            answer=answer,
            citations=[
                Citation(
                    source_uri=f"drift://scenario/{scenario_name}",
                    label=f"drift report: {scenario_name}",
                )
            ],
        )
