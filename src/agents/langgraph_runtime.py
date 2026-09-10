"""LangGraph coordinator pilot with the existing specialist contracts.

The graph replaces orchestration plumbing only; MCP clients, Pydantic response
models, telemetry, authorization and provider policy remain owned by the
existing agent modules. Imports are lazy so the fast runtime does not require
LangChain until this path is selected.
"""

from __future__ import annotations

import asyncio
from typing import Any, TypedDict

from src.agents.coordinator import CoordinatorRequest, CoordinatorResponse, citations_are_valid
from src.agents.models import AgentFailure, SpecialistResponse


class CoordinatorState(TypedDict, total=False):
    request: CoordinatorRequest
    feature: SpecialistResponse
    drift: SpecialistResponse
    result: CoordinatorResponse | AgentFailure


def build_langgraph_coordinator(
    feature_agent: Any,
    drift_agent: Any,
    *,
    max_hops: int = 2,
    max_parallel: int = 2,
) -> Any:
    """Compile one bounded coordinator graph around existing specialists."""
    if max_hops < 1 or max_parallel < 1:
        raise ValueError("max_hops and max_parallel must be positive")
    from langchain_core.runnables import RunnableLambda
    from langgraph.graph import END, START, StateGraph

    semaphore = asyncio.Semaphore(max_parallel)

    async def validate(state: CoordinatorState) -> CoordinatorState:
        request = state["request"]
        if request.hop + 1 > max_hops:
            return {"result": AgentFailure(error="hop_limit_exceeded")}
        return {}

    async def invoke_feature(state: CoordinatorState) -> SpecialistResponse:
        request = state["request"]
        async with semaphore:
            return await feature_agent.run(
                {"question": request.question, **request.feature_request}
            )

    async def invoke_drift(state: CoordinatorState) -> SpecialistResponse:
        request = state["request"]
        async with semaphore:
            return await drift_agent.run({"question": request.question, **request.drift_request})

    feature_runnable = RunnableLambda(invoke_feature)
    drift_runnable = RunnableLambda(invoke_drift)

    async def feature(state: CoordinatorState) -> CoordinatorState:
        return {"feature": await feature_runnable.ainvoke(state)}

    async def drift(state: CoordinatorState) -> CoordinatorState:
        return {"drift": await drift_runnable.ainvoke(state)}

    async def answer(state: CoordinatorState) -> CoordinatorState:
        if "result" in state:
            return {}
        specialists = [state["feature"], state["drift"]]
        citations = [citation for item in specialists for citation in item.citations]
        if not citations_are_valid(citations):
            return {"result": AgentFailure(error="invalid_citations")}
        return {
            "result": CoordinatorResponse(
                answer="\n\n".join(f"[{item.specialist}] {item.answer}" for item in specialists),
                specialists=specialists,
                citations=citations,
                hops_used=state["request"].hop + 1,
            )
        }

    def route_after_validate(state: CoordinatorState) -> str | list[str]:
        return END if "result" in state else ["feature", "drift"]

    graph = StateGraph(CoordinatorState)
    graph.add_node("validate", validate)
    graph.add_node("feature", feature)
    graph.add_node("drift", drift)
    graph.add_node("answer", answer)
    graph.add_edge(START, "validate")
    graph.add_conditional_edges(
        "validate",
        route_after_validate,
        {"feature": "feature", "drift": "drift", END: END},
    )
    graph.add_edge("feature", "answer")
    graph.add_edge("drift", "answer")
    graph.add_edge("answer", END)
    return graph.compile()


async def coordinate_langgraph(
    graph: Any,
    raw: CoordinatorRequest | dict[str, Any],
    *,
    timeout_seconds: float = 50.0,
) -> CoordinatorResponse | AgentFailure:
    """Run the pilot with the unchanged external request/response contract."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    request = raw if isinstance(raw, CoordinatorRequest) else CoordinatorRequest.model_validate(raw)
    try:
        result = await asyncio.wait_for(
            graph.ainvoke({"request": request}),
            timeout=timeout_seconds,
        )
    except (OSError, RuntimeError, TimeoutError, ValueError) as exc:
        return AgentFailure(error=str(exc))
    return result["result"]
