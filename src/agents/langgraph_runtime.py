"""LangGraph orchestration adapter for the existing specialist contract.

The graph is deliberately transport-neutral: it invokes the repository-owned feature and
 drift specialists, preserves ``CoordinatorResponse``/``AgentFailure``, and never performs
 provider fallback after a specialist has emitted a response.  LangGraph is imported lazily
 so fixture-only collection and the existing API remain import-safe when the optional platform
 dependency is absent.
"""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, TypedDict

from src.agents.coordinator import CoordinatorRequest, CoordinatorResponse, citations_are_valid
from src.agents.models import AgentFailure, SpecialistResponse
from src.observability.telemetry import Telemetry, current_telemetry


class GraphState(TypedDict, total=False):
    request: CoordinatorRequest
    feature: SpecialistResponse
    drift: SpecialistResponse
    result: CoordinatorResponse | AgentFailure
    failure: AgentFailure
    started_at: str


class LangGraphUnavailableError(RuntimeError):
    """Raised when the optional LangGraph platform dependency is not installed."""


class LangGraphCoordinator:
    """Run one bounded feature/drift graph behind the existing coordinator port.

    ``checkpointer`` is injected rather than constructed here.  Production can provide a
    PostgreSQL saver; local runs use no persistence and therefore cannot accidentally imply
    multi-replica recovery.  ``thread_id`` is derived from the caller's scope and identity,
    keeping checkpoint namespaces tenant-scoped without adding fields to the public request.
    A persistent checkpointer MUST only be supplied by an authenticated deployment boundary.
    """

    def __init__(
        self,
        feature_agent: Any,
        drift_agent: Any,
        *,
        max_hops: int = 2,
        checkpointer: Any | None = None,
        telemetry: Telemetry | None = None,
        timeout_seconds: float | None = None,
        thread_identity: Callable[[CoordinatorRequest], str] | None = None,
    ) -> None:
        if max_hops < 1:
            raise ValueError("max_hops must be positive")
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if checkpointer is not None and thread_identity is None:
            raise ValueError("persistent checkpointer requires authenticated thread identity")
        self.feature_agent = feature_agent
        self.drift_agent = drift_agent
        self.max_hops = max_hops
        self.checkpointer = checkpointer
        self.telemetry = telemetry
        self.timeout_seconds = timeout_seconds
        self.thread_identity = thread_identity
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:
        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError as exc:
            raise LangGraphUnavailableError(
                "LangGraph is required for the graph orchestration backend"
            ) from exc

        graph = StateGraph(GraphState)
        graph.add_node("feature", self._feature_node)
        graph.add_node("drift", self._drift_node)
        graph.add_node("finalize", self._finalize_node)
        graph.add_edge(START, "feature")
        graph.add_conditional_edges("feature", self._after_feature, {"drift": "drift", "stop": END})
        graph.add_conditional_edges(
            "drift", self._after_drift, {"finalize": "finalize", "stop": END}
        )
        graph.add_edge("finalize", END)
        return graph.compile(checkpointer=self.checkpointer)

    async def _invoke_agent(self, agent: Any, payload: dict[str, Any]) -> Any:
        invocation = agent.run(payload)
        if self.timeout_seconds is None:
            return await invocation
        return await asyncio.wait_for(invocation, timeout=self.timeout_seconds)

    def _agent_failure(self, specialist: str, exc: Exception) -> AgentFailure:
        telemetry = self.telemetry or current_telemetry()
        telemetry.observe_failure(f"agent.{specialist}.langgraph", type(exc).__name__)
        error = f"{specialist}_timeout" if isinstance(exc, TimeoutError) else str(exc)
        return AgentFailure(error=error)

    async def _feature_node(self, state: GraphState) -> dict[str, Any]:
        request = state["request"]
        try:
            response = await self._invoke_agent(
                self.feature_agent,
                {"question": request.question, **request.feature_request},
            )
        except Exception as exc:
            return {"failure": self._agent_failure("feature", exc)}
        return {"feature": response}

    async def _drift_node(self, state: GraphState) -> dict[str, Any]:
        request = state["request"]
        try:
            response = await self._invoke_agent(
                self.drift_agent,
                {"question": request.question, **request.drift_request},
            )
        except Exception as exc:
            return {"failure": self._agent_failure("drift", exc)}
        return {"drift": response}

    @staticmethod
    def _after_feature(state: GraphState) -> str:
        return "stop" if "failure" in state else "drift"

    @staticmethod
    def _after_drift(state: GraphState) -> str:
        return "stop" if "failure" in state else "finalize"

    async def _finalize_node(self, state: GraphState) -> dict[str, Any]:
        if "failure" in state:
            return {"result": state["failure"]}
        feature = state["feature"]
        drift = state["drift"]
        citations = [*feature.citations, *drift.citations]
        if not citations_are_valid(citations):
            return {"result": AgentFailure(error="invalid_citations")}
        return {
            "result": CoordinatorResponse(
                answer=f"[feature] {feature.answer}\n\n[drift] {drift.answer}",
                specialists=[feature, drift],
                citations=citations,
                hops_used=max(2, state["request"].hop + 1),
            )
        }

    def _thread_id(self, request: CoordinatorRequest) -> str:
        if self.thread_identity is not None:
            thread_id = self.thread_identity(request)
            if not isinstance(thread_id, str) or not thread_id.strip():
                raise ValueError("authenticated thread identity must return a non-empty string")
            return thread_id
        user_id = str(request.feature_request.get("user_id", "anonymous"))
        scope = str(request.feature_request.get("scope", "default"))
        return f"{scope}:{user_id}"

    async def coordinate(
        self, raw: CoordinatorRequest | dict[str, Any]
    ) -> CoordinatorResponse | AgentFailure:
        telemetry = self.telemetry or current_telemetry()
        request = (
            raw if isinstance(raw, CoordinatorRequest) else CoordinatorRequest.model_validate(raw)
        )
        if request.hop + 1 > self.max_hops:
            return AgentFailure(error="hop_limit_exceeded")
        telemetry.observe_agent_call("coordinator-langgraph")
        started = datetime.now(UTC).isoformat()
        config = {"configurable": {"thread_id": self._thread_id(request)}}
        try:
            with telemetry.span("agent.coordinator.langgraph", {"backend": "langgraph"}):
                state = await self._graph.ainvoke(
                    {"request": request, "started_at": started}, config=config
                )
        except Exception as exc:
            telemetry.observe_failure("agent.coordinator.langgraph", type(exc).__name__)
            error = "coordinator_timeout" if isinstance(exc, TimeoutError) else str(exc)
            return AgentFailure(error=error)
        result = state.get("result") or state.get("failure")
        if isinstance(result, CoordinatorResponse):
            return result
        if isinstance(result, AgentFailure):
            telemetry.observe_failure("agent.coordinator.langgraph", result.error)
            return result
        telemetry.observe_failure("agent.coordinator.langgraph", "missing_result")
        return AgentFailure(error="langgraph_missing_result")
