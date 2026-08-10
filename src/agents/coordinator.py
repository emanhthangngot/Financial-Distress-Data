"""Bounded parallel coordinator for the feature and drift specialists."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

from src.agents.models import AgentFailure, Citation, SpecialistResponse


class Specialist(Protocol):
    async def run(self, request: dict[str, Any]) -> SpecialistResponse: ...


class CoordinatorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=10_000)
    feature_request: dict[str, Any]
    drift_request: dict[str, Any]
    hop: int = Field(default=0, ge=0)


class CoordinatorResponse(BaseModel):
    status: str = "ok"
    answer: str
    specialists: list[SpecialistResponse]
    citations: list[Citation]
    hops_used: int


def citations_are_valid(citations: list[Citation]) -> bool:
    allowed_schemes = {"https", "http", "s3", "feature", "drift"}
    return bool(citations) and all(
        urlparse(citation.source_uri).scheme in allowed_schemes for citation in citations
    )


@dataclass
class Coordinator:
    feature_agent: Specialist
    drift_agent: Specialist
    max_hops: int = 2
    max_parallel: int = 2
    timeout_seconds: float = 10.0

    async def coordinate(
        self, raw: CoordinatorRequest | dict[str, Any]
    ) -> CoordinatorResponse | AgentFailure:
        request = (
            raw if isinstance(raw, CoordinatorRequest) else CoordinatorRequest.model_validate(raw)
        )
        if request.hop + 1 > self.max_hops:
            return self.failure_policy("hop_limit_exceeded")
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def invoke(agent: Specialist, payload: dict[str, Any]) -> SpecialistResponse:
            async with semaphore:
                return await agent.run({"question": request.question, **payload})

        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    invoke(self.feature_agent, request.feature_request),
                    invoke(self.drift_agent, request.drift_request),
                ),
                timeout=self.timeout_seconds,
            )
        except (OSError, RuntimeError, TimeoutError, ValueError) as exc:
            return self.failure_policy(exc)
        citations = [citation for result in results for citation in result.citations]
        if not citations_are_valid(citations):
            return self.failure_policy("invalid_citations")
        answer = "\n\n".join(f"[{result.specialist}] {result.answer}" for result in results)
        return CoordinatorResponse(
            answer=answer,
            specialists=results,
            citations=citations,
            hops_used=request.hop + 1,
        )

    @staticmethod
    def failure_policy(error: Any) -> AgentFailure:
        return AgentFailure(error=str(error))
