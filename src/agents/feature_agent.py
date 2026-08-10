"""Feature specialist with immutable caller scope and hostile RAG handling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from src.agents.models import Citation, SpecialistResponse
from src.observability.telemetry import Telemetry, current_telemetry

UNTRUSTED_CONTENT_START = "<UNTRUSTED_RAG_CONTENT>"
UNTRUSTED_CONTENT_END = "</UNTRUSTED_RAG_CONTENT>"


class FeatureToolClient(Protocol):
    async def lookup(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class AnswerRenderer(Protocol):
    async def render(self, question: str, context: str) -> str: ...


class FeatureAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=10_000)
    user_id: str = Field(min_length=1, max_length=128)
    feature_names: tuple[str, ...] = Field(min_length=1, max_length=64)
    chunk_id: str | None = Field(default=None, max_length=128)
    scope: str = Field(min_length=1, max_length=128)
    tool_budget: int = Field(default=1, ge=1, le=4)


def validate_non_widening(
    original: FeatureAgentRequest, candidate: dict[str, Any]
) -> dict[str, Any]:
    """Reject any candidate call that expands IDs, features, scope or budget."""
    allowed = {
        "user_id": original.user_id,
        "feature_names": original.feature_names,
        "chunk_id": original.chunk_id,
        "scope": original.scope,
    }
    normalized = dict(candidate)
    normalized["feature_names"] = tuple(normalized.get("feature_names", ()))
    if normalized != allowed:
        raise ValueError("tool request widens the caller's original scope")
    return normalized


def delimit_untrusted_content(text: str) -> str:
    escaped = text.replace(UNTRUSTED_CONTENT_START, "&lt;UNTRUSTED_RAG_CONTENT&gt;")
    escaped = escaped.replace(UNTRUSTED_CONTENT_END, "&lt;/UNTRUSTED_RAG_CONTENT&gt;")
    return f"{UNTRUSTED_CONTENT_START}\n{escaped}\n{UNTRUSTED_CONTENT_END}"


@dataclass
class FeatureAgent:
    tool: FeatureToolClient
    renderer: AnswerRenderer
    identity: str = "feature-agent"
    telemetry: Telemetry | None = None

    async def run(self, raw: FeatureAgentRequest | dict[str, Any]) -> SpecialistResponse:
        telemetry = self.telemetry or current_telemetry()
        telemetry.observe_agent_call(self.identity)
        try:
            with telemetry.span("agent.feature.run", {"agent": self.identity}):
                return await self._run(raw)
        except Exception as exc:
            telemetry.observe_failure("agent.feature.run", type(exc).__name__)
            raise

    async def _run(self, raw: FeatureAgentRequest | dict[str, Any]) -> SpecialistResponse:
        request = (
            raw if isinstance(raw, FeatureAgentRequest) else FeatureAgentRequest.model_validate(raw)
        )
        if request.tool_budget < 1:
            raise RuntimeError("tool budget exhausted")
        candidate = validate_non_widening(
            request,
            {
                "user_id": request.user_id,
                "feature_names": request.feature_names,
                "chunk_id": request.chunk_id,
                "scope": request.scope,
            },
        )
        result = await self.tool.lookup(
            {
                **candidate,
                "agent_identity": self.identity,
            }
        )
        if not result.get("ok"):
            raise RuntimeError(str(result.get("error", "feature tool failed")))
        data = result.get("data") or {}
        rag = data.get("rag") or {}
        chunk_text = str(rag.get("chunk_text", ""))
        context = f"features={data.get('features', {})}"
        citations: list[Citation] = []
        if chunk_text:
            context += "\n" + delimit_untrusted_content(chunk_text)
            citations.append(
                Citation(
                    source_uri=str(rag.get("source_uri", "")),
                    label=str(rag.get("chunk_id", request.chunk_id or "RAG chunk")),
                )
            )
        else:
            citations.append(
                Citation(source_uri=f"feature://user/{request.user_id}", label="features")
            )
        answer = await self.renderer.render(request.question, context)
        return SpecialistResponse(
            specialist="feature",
            answer=answer,
            citations=citations,
        )
