"""LLM track contracts and dependency-injected reference implementations.

The five abstract services are the stable ports described in
``docs/phase2/low-level-design.md``. Concrete classes keep storage, benchmark,
and GitOps effects behind injected adapters while the contracts own validation,
state transitions, and bounded failure policies. Importing this module never
opens a network connection or mutates a repository.
"""

import hashlib
import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
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


@dataclass(frozen=True)
class EmbeddingVersion:
    """Registry record used by :class:`InMemoryEmbeddingRegistry`."""

    version: str
    model_name: str
    dims: int
    digest: str


class InMemoryEmbeddingRegistry(EmbeddingRegistryService):
    """Thread-safe registry adapter for local tests and evidence runs.

    Production persistence is supplied by the phase-2 metadata service later;
    this implementation makes the contract executable without smuggling a
    database client into import-time code.
    """

    _DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

    def __init__(self) -> None:
        self._versions: dict[str, EmbeddingVersion] = {}
        self._active: str | None = None
        self._lock = Lock()

    def register_version(self, model_name: str, dims: int, digest: str) -> str:
        if not model_name.strip():
            raise ValueError("model_name must not be empty")
        if dims < 1:
            raise ValueError("dims must be positive")
        if not self._DIGEST_RE.fullmatch(digest):
            raise ValueError("digest must be a sha256:<64 hex> image digest")
        version = hashlib.sha256(f"{model_name}|{dims}|{digest}".encode()).hexdigest()[:16]
        with self._lock:
            self._versions[version] = EmbeddingVersion(version, model_name, dims, digest)
            if self._active is None:
                self._active = version
        return version

    def hot_swap(self, new_version: str) -> dict[str, Any]:
        with self._lock:
            candidate = self._versions.get(new_version)
            if candidate is None:
                raise KeyError(f"unknown embedding version: {new_version}")
            previous = self._active
            previous_record = self._versions.get(previous) if previous is not None else None
            if previous_record is not None and previous_record.dims != candidate.dims:
                raise ValueError("embedding dimensions are incompatible")
            self._active = new_version
        return {
            "status": "swapped",
            "previous_version": previous,
            "active_version": new_version,
            "validated_at": datetime.now(UTC).isoformat(),
        }

    def resolve_active(self) -> str:
        with self._lock:
            if self._active is None:
                raise LookupError("no active embedding version")
            return self._active

    def compatibility_check(self, a: str, b: str) -> bool:
        with self._lock:
            left, right = self._versions.get(a), self._versions.get(b)
            return left is not None and right is not None and left.dims == right.dims


class InMemoryAgentReleaseService(AgentReleaseService):
    """GitOps release state machine with injected benchmark/revision ports.

    ``benchmark`` is called only by ``warm_up`` and must return measured
    values. This avoids fabricating cold/warm timings when a live cluster is
    unavailable while keeping the release contract executable in unit tests.
    """

    def __init__(
        self,
        *,
        benchmark: Callable[[str, int], dict[str, Any]],
        revision_provider: Callable[[], str],
    ) -> None:
        self._benchmark = benchmark
        self._revision_provider = revision_provider
        self._releases: dict[str, dict[str, Any]] = {}
        self._experiments: dict[str, dict[str, Any]] = {}

    def register(self, agent: str, version: str, config: dict[str, Any]) -> str:
        if not agent.strip() or not version.strip():
            raise ValueError("agent and version must not be empty")
        release_id = hashlib.sha256(f"{agent}|{version}".encode()).hexdigest()[:16]
        self._releases[agent] = {
            "release_id": release_id,
            "version": version,
            "config": dict(config),
            "status": "registered",
        }
        return release_id

    def canary(self, agent: str, new_version: str, fraction: float) -> str:
        if not 0 < fraction < 1:
            raise ValueError("canary fraction must be greater than 0 and less than 1")
        if agent not in self._releases:
            raise KeyError(f"agent is not registered: {agent}")
        experiment_id = hashlib.sha256(f"{agent}|{new_version}|{fraction}".encode()).hexdigest()[
            :16
        ]
        self._experiments[experiment_id] = {
            "agent": agent,
            "new_version": new_version,
            "fraction": fraction,
            "status": "active",
        }
        return experiment_id

    def warm_up(self, agent: str, replicas: int) -> dict[str, Any]:
        if agent not in self._releases:
            raise KeyError(f"agent is not registered: {agent}")
        if replicas < 1:
            raise ValueError("replicas must be positive")
        measurements = self._benchmark(agent, replicas)
        required = {
            "cold_start_seconds",
            "warm_start_seconds",
            "cold_ttft_seconds",
            "warm_ttft_seconds",
        }
        missing = required - measurements.keys()
        if missing:
            raise ValueError(f"benchmark is missing measurements: {sorted(missing)}")
        return {"agent": agent, "replicas": replicas, **measurements}

    def promote_or_rollback(self, agent: str, decision: str) -> str:
        if agent not in self._releases:
            raise KeyError(f"agent is not registered: {agent}")
        if decision not in {"promote", "rollback"}:
            raise ValueError("decision must be promote or rollback")
        self._releases[agent]["status"] = "active" if decision == "promote" else "rolled_back"
        return self._revision_provider()
