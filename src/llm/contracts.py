"""LLM track class contracts (Phase 2 design contract, phase-01).

Signature-only contracts that lock the five named LLM classes before
implementation begins. Implementations live under ``src/llm/`` in later
phases and must satisfy these signatures plus the rubric-matrix evidence
contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from typing import Any


class RagIngestionService(ABC):
    """Fetches trusted documents, parses/chunks/deduplicates, enforces
    metadata/licensing, and writes Feast/PGVector versions."""

    @abstractmethod
    def fetch_documents(self, source: str, window: Any) -> list[Any]:
        """Fetch trusted documents (Vnstock news + PDFs) for a time window."""

    @abstractmethod
    def parse_and_chunk(self, documents: list[Any]) -> list[Any]:
        """Parse into chunks; each chunk records source URI, company, report
        date, content hash, parser version and access class."""

    @abstractmethod
    def deduplicate_chunks(self, chunks: list[Any]) -> list[Any]:
        """Reuse chunk/content hashes for unchanged documents — no duplicate
        vectors."""

    @abstractmethod
    def enforce_licensing_and_metadata(self, chunks: list[Any]) -> None:
        """Validate licensing metadata and access class before ingestion."""

    @abstractmethod
    def write_vectors(self, chunks: list[Any], embedding_version: str) -> str:
        """Embed and write vectors to Feast/PGVector; return ingestion version."""


class EmbeddingRegistryService(ABC):
    """Records model/vector compatibility and performs zero-downtime
    embedding-version hot swap."""

    @abstractmethod
    def register_version(self, model_name: str, dims: int, digest: str) -> str:
        """Register an embedding model/vector compatibility entry."""

    @abstractmethod
    def hot_swap(self, new_version: str) -> dict[str, Any]:
        """Dual-read validation then alias change — no downtime, no
        mixed-vector query."""

    @abstractmethod
    def resolve_active(self) -> str:
        """Return the currently active embedding version alias."""

    @abstractmethod
    def compatibility_check(self, a: str, b: str) -> bool:
        """Return True when two versions are query-compatible."""


class McpToolService(ABC):
    """Validates scoped tool requests, authorizes agent/tool identity,
    enforces timeouts/budgets and emits traces."""

    @abstractmethod
    def authorize(self, tool: str, agent_identity: str, scope: str) -> bool:
        """Return True when the agent may invoke the scoped tool."""

    @abstractmethod
    def invoke(self, tool: str, payload: dict[str, Any]) -> Any:
        """Invoke the tool with timeout and budget enforcement; return a
        structured tool result."""

    @abstractmethod
    def validate_request(self, payload: dict[str, Any]) -> Any:
        """Pydantic-validate the tool request payload."""

    @abstractmethod
    def emit_trace(self, tool: str, request: dict[str, Any], result: Any) -> None:
        """Emit an OpenTelemetry trace for the tool invocation."""


class AgentOrchestrationService(ABC):
    """Coordinates specialist agents with bounded hops, citation checks and a
    deterministic failure policy."""

    @abstractmethod
    def coordinate(self, task: str, specialists: list[str]) -> Any:
        """Fan out to specialist agents with bounded hops and collect
        results."""

    @abstractmethod
    def check_citations(self, response: Any) -> list[Any]:
        """Verify every claim links to a retrievable citation."""

    @abstractmethod
    def failure_policy(self, error: Any) -> dict[str, Any]:
        """Return a deterministic retry/fallback/stop decision."""


class AgentReleaseService(ABC):
    """Registers, canaries, warms, promotes and rolls back agent/model
    configurations through GitOps."""

    @abstractmethod
    def register(self, agent: str, version: str, config: dict[str, Any]) -> str:
        """Publish the agent to the agent registry with version and config."""

    @abstractmethod
    def canary(self, agent: str, new_version: str, fraction: float) -> str:
        """Route a fraction of traffic to the new version; return experiment ID."""

    @abstractmethod
    def warm_up(self, agent: str, replicas: int) -> dict[str, Any]:
        """Warm the worker pool to a minimum capacity; return startup/TTFT
        benchmark evidence."""

    @abstractmethod
    def promote_or_rollback(self, agent: str, decision: str) -> str:
        """Promote or roll back an agent/model config through GitOps; return
        the Git revision."""


@dataclass(frozen=True)
class ToolInvocationResult:
    """Transport-neutral result returned by concrete MCP orchestration."""

    ok: bool
    value: Any = None
    error: str | None = None


class BoundedMcpToolService(McpToolService):
    """Concrete, dependency-injected implementation of the MCP contract.

    Tool handlers remain outside this class. This layer owns only request
    validation, authorization, per-instance budgeting and trace emission.
    """

    def __init__(
        self,
        *,
        handlers: dict[str, Callable[[dict[str, Any]], Any]],
        validators: dict[str, Callable[[dict[str, Any]], Any]],
        grants: dict[str, set[tuple[str, str]]],
        trace_sink: Callable[[str, dict[str, Any], Any], None] | None = None,
        max_calls: int = 8,
    ) -> None:
        if max_calls < 1:
            raise ValueError("max_calls must be positive")
        self._handlers = handlers
        self._validators = validators
        self._grants = grants
        self._trace_sink = trace_sink or (lambda _tool, _request, _result: None)
        self._remaining = max_calls
        self._lock = Lock()

    def authorize(self, tool: str, agent_identity: str, scope: str) -> bool:
        return (agent_identity, scope) in self._grants.get(tool, set())

    def validate_request(self, payload: dict[str, Any]) -> Any:
        tool = str(payload.get("tool", ""))
        if tool not in self._validators:
            raise ValueError(f"unknown tool: {tool}")
        return self._validators[tool](payload)

    def invoke(self, tool: str, payload: dict[str, Any]) -> ToolInvocationResult:
        request = dict(payload)
        request["tool"] = tool
        try:
            validated = self.validate_request(request)
            identity = str(request.get("agent_identity", ""))
            scope = str(request.get("scope", ""))
            if not self.authorize(tool, identity, scope):
                result = ToolInvocationResult(ok=False, error="forbidden")
            else:
                with self._lock:
                    if self._remaining == 0:
                        result = ToolInvocationResult(ok=False, error="tool_budget_exhausted")
                    else:
                        self._remaining -= 1
                        result = ToolInvocationResult(
                            ok=True, value=self._handlers[tool](validated)
                        )
        except (KeyError, TypeError, ValueError) as exc:
            result = ToolInvocationResult(ok=False, error=str(exc))
        self.emit_trace(tool, request, result)
        return result

    def emit_trace(self, tool: str, request: dict[str, Any], result: Any) -> None:
        self._trace_sink(tool, request, result)


class BoundedAgentOrchestrationService(AgentOrchestrationService):
    """Concrete synchronous coordinator for non-async contract consumers."""

    def __init__(
        self,
        handlers: dict[str, Callable[[str], Any]],
        *,
        max_hops: int = 2,
    ) -> None:
        if max_hops < 1:
            raise ValueError("max_hops must be positive")
        self._handlers = handlers
        self._max_hops = max_hops

    def coordinate(self, task: str, specialists: list[str]) -> dict[str, Any]:
        selected = list(dict.fromkeys(specialists))
        if len(selected) > self._max_hops:
            return self.failure_policy("hop_limit_exceeded")
        try:
            results = {name: self._handlers[name](task) for name in selected}
        except (KeyError, RuntimeError, TimeoutError, ValueError) as exc:
            return self.failure_policy(exc)
        invalid = [name for name, result in results.items() if self.check_citations(result)]
        if invalid:
            return self.failure_policy(f"invalid_citations:{','.join(invalid)}")
        return {"status": "ok", "results": results, "hops": len(selected)}

    def check_citations(self, response: Any) -> list[Any]:
        if not isinstance(response, dict):
            return ["response_not_mapping"]
        citations = response.get("citations")
        if not isinstance(citations, list) or not citations:
            return ["missing_citations"]
        return [item for item in citations if not isinstance(item, str) or not item.strip()]

    def failure_policy(self, error: Any) -> dict[str, Any]:
        return {"status": "failed", "decision": "stop", "error": str(error)}
