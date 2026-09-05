# Low-Level Design: 5 Key Classes per Track

Rubric: ML 56 / LLM 59, "Documentation ; (tất cả documents để trong folder
`docs/`)... low-level ML design" — 2 points each, owned by P3 (this phase,
`docs/rubric-matrix-unified.csv` rows `ML-documentation-low-level-ml-design`,
`LLM-documentation-low-level-ml-design`).

Every class below is a real class in the repo today (not a design sketch to
be built later) — signatures are copied from source, not invented. Sequence
flows describe the runtime call order each class participates in.

## ML Track

### 1. `TrainingPipeline` (`src/ml/pipelines/training_pipeline.py`)

```python
class TrainingPipeline:
    """Run PIT validation, deterministic training, evaluation and registration."""

    def __init__(self, registry: MLflowRegistry | None = None): ...
    def train(self, train_df: Any, config: dict[str, Any] | None = None) -> LogisticModel: ...
    def evaluate(self, model: LogisticModel, validation_df: Any) -> dict[str, float]: ...
    def log_run(self, model: LogisticModel, metrics: dict[str, float], data_version: str) -> str: ...
    def run(self, train_df: Any, validation_df: Any | None = None, ...) -> TrainingResult: ...
```

Orchestrates one training run end to end: `train` fits a deterministic
`LogisticModel` from PIT-filtered rows, `evaluate` scores it against a
held-out split, `log_run` hands the model artifact and metrics to the
injected `MLflowRegistry`, and `run` sequences all three plus a
`DataVersion` snapshot (`DataVersioner`) into one `TrainingResult`.

### 2. `MLflowRegistry` (`src/ml/mlflow_registry.py`)

```python
class MLflowRegistry:
    """Register immutable model versions and resolve aliases safely."""

    def __init__(self, tracking_uri: str | None = None, *, ...): ...
    def register(self, model_name: str, artifact_uri: str, ...) -> ...: ...
    def set_alias(self, model_name: str, alias: str, version: str | int) -> None: ...
    def resolve_alias(self, model_name: str, alias: str = "champion") -> dict[str, Any]: ...
```

`register` is called once per `TrainingPipeline.log_run`. `set_alias` moves
a promotion alias (e.g. `champion`) to a specific version — ADR-018's
promotion contract: MLflow is a promotion *dependency*, never a KServe
runtime dependency. `resolve_alias` is the read side the promotion
controller calls to resolve `champion` to an immutable artifact URI before
committing it to GitOps desired state.

### 3. `DataVersioner` (`src/ml/data_versioning.py`)

```python
@dataclass(frozen=True)
class DataVersion:
    version: str
    row_count: int
    snapshot_id: str
    def as_dict(self) -> dict[str, Any]: ...

class DataVersioner:
    """Small state-free facade suitable for injection into training jobs."""

    def create(self, data: Any, **kwargs: Any) -> DataVersion: ...
    def compare(self, left: Any, right: Any) -> bool: ...
```

`create` snapshots the training data used by one `TrainingPipeline.run`
call into a `DataVersion` (incremental, not a full copy — ML rubric row 25).
`compare` answers "did the data change between two runs" by snapshot-ID
equality, without loading either dataset twice.

### 4. `DistributedTrainer` (`src/ml/pipelines/distributed_training.py`)

```python
class DistributedTrainer:
    """Split data deterministically across workers and train a baseline."""

    def __init__(self, worker_count: int = 2): ...
    def train_local(self, train_df: Any, config: dict[str, Any] | None = None) -> DistributedTrainingResult: ...
    def submit_kubeflow(self, endpoint: str, *, ...) -> ...: ...
```

`train_local` is the deterministic, cluster-free path every unit test
exercises: it shards `train_df` into `worker_count` deterministic
partitions and trains a `LogisticModel` per shard. `submit_kubeflow` is the
Ray-cluster submission boundary (ADR-014, amended 2026-09-05: distributed
training runs on Ray, not a Kubeflow Trainer HTTP call) — a real network
request only when explicitly invoked with a live endpoint; local tests
never require a live Ray cluster.

### 5. `ABRouter` (`src/ml/ab_router.py`)

```python
@dataclass(frozen=True)
class RouteDecision:
    key: str
    variant: str
    bucket: float

class ABRouter:
    """Route a stable key to a weighted model variant without mutable RNG state."""

    def __init__(self, variants: Mapping[str, float], *, salt: str = "financial-distress"): ...
    def decide(self, key: str | int) -> RouteDecision: ...
    def route(self, key: str | int) -> str: ...
    weights: dict[str, float]  # property
```

`decide` hashes `key` (e.g. a request ID) with `salt` into a stable
`[0, 1)` bucket and walks the cumulative weight table to a variant — the
same key always routes to the same variant, so A/B assignment survives
retries and does not need session state. `route` is the convenience
wrapper that discards the `RouteDecision` audit trail when the caller only
needs the variant name.

### ML sequence flow — one training-to-promotion cycle

```
DataVersioner.create(train_df)
        │
        ▼
TrainingPipeline.train(train_df, config)  ──▶  LogisticModel
        │
        ▼
TrainingPipeline.evaluate(model, validation_df)  ──▶  metrics
        │
        ▼
TrainingPipeline.log_run(model, metrics, data_version)
        │
        ▼
MLflowRegistry.register(model_name, artifact_uri)
        │
   (holdout gate passes)
        ▼
MLflowRegistry.set_alias(model_name, "champion", version)
        │
        ▼
promotion controller: MLflowRegistry.resolve_alias(model_name, "champion")
        │
        ▼
commit resolved artifact URI to GitOps desired state (phase-10 bump-gitops)
        │
        ▼
ABRouter.decide(request_key)  ← runtime inference traffic split, once deployed
```

`DistributedTrainer.train_local`/`submit_kubeflow` substitutes for
`TrainingPipeline.train` when the run needs sharded/cluster execution; the
rest of the flow is identical either way.

## LLM Track

### 1. `Coordinator` (`src/agents/coordinator.py`)

```python
class Specialist(Protocol):
    async def run(self, request: dict[str, Any]) -> SpecialistResponse: ...

@dataclass
class Coordinator:
    feature_agent: Specialist
    drift_agent: Specialist
    max_hops: int = 2

    @staticmethod
    def failure_policy(error: Any) -> AgentFailure: ...
```

Fans a `CoordinatorRequest` out to the injected `feature_agent` and
`drift_agent` specialists (each satisfying the `Specialist` protocol — a
single `async def run`), bounded by `max_hops` to prevent unbounded agent
chaining. `failure_policy` converts any specialist exception into a
structured `AgentFailure` so a coordinator response is never a raw
traceback.

### 2. `HttpSpecialistClient` (`src/agents/runtime.py`)

```python
class HttpSpecialistClient:
    def __init__(self, base_url: str, telemetry: Telemetry | None = None) -> None: ...
```

The `Specialist`-protocol implementation `Coordinator.feature_agent`/
`drift_agent` are usually bound to in production: an HTTP client that
satisfies `Specialist.run` by calling a real agent's HTTP endpoint, with an
optional `Telemetry` sink for span/metric emission. `McpFeatureToolClient`
and `McpDriftToolClient` in the same module are the narrower MCP-tool-only
variants used when an agent calls a tool directly rather than another full
agent.

### 3. `RagIngestionPipeline` (`src/llm/rag_pipeline.py`)

```python
class RagIngestionPipeline(RagIngestionService):
    """One instance is a single synchronous run of all five contract
    methods, in order, against the same in-process object."""

    def __init__(self, store: PgVectorStore, embedding_backend: EmbeddingBackend, ...): ...
    def fetch_documents(self, source: str, window: Any = None) -> list[RawDocument]: ...
    def parse_and_chunk(self, documents: list[RawDocument]) -> list[Chunk]: ...
    def deduplicate_chunks(self, chunks: list[Chunk]) -> list[Chunk]: ...
    def enforce_licensing_and_metadata(self, chunks: list[Chunk]) -> None: ...
    def write_vectors(self, chunks: list[Chunk], embedding_version: str) -> str: ...
```

Implements the five-method `RagIngestionService` contract in strict order.
`deduplicate_chunks` drops `(content_hash, embedding_version)` collisions so
a same-version rerun on unchanged input writes zero new rows.
`enforce_licensing_and_metadata` filters `chunks` in place — a metadata gap
raises (programmer error), a license/PII violation quarantines that one
chunk. `write_vectors` embeds with `self.embedding_backend` and upserts into
`store`; the `embedding_version` argument must match the backend's own
version or the call raises rather than silently writing mismatched vectors.

### 4. `CitationGuard` (`src/llm/citation_guard.py`)

```python
@dataclass(frozen=True)
class CitationDecision:
    allowed: bool
    action: str
    def as_dict(self) -> dict[str, Any]: ...

class CitationGuard:
    """Validate citations and redact PII without exposing matched values."""

    def __init__(self, citation_exists: Callable[[str], bool] | None = None) -> None: ...
    def evaluate(self, output: str, citations: Iterable[str], ...) -> CitationDecision: ...

    @staticmethod
    def find_pii(output: str) -> tuple[str, ...]: ...
    @staticmethod
    def redact(output: str) -> str: ...
```

`evaluate` is the response-policy boundary every agent answer passes
through before being returned to a user: it checks each citation against
the injected `citation_exists` resolver (never trusts a syntactically
plausible URL as proof a source exists — a caller with no resolver fails
closed) and returns an auditable `CitationDecision`. `find_pii`/`redact` are
static because they need no instance state: they return stable category
names (never the matched values themselves, so the guard's own logs cannot
leak the PII it caught) and produce the redacted output text.

### 5. `ModelServerConfig` (`src/llm/model_server.py`)

```python
@dataclasses.dataclass(frozen=True)
class ModelServerConfig:
    """Runtime configuration for the llama.cpp OpenAI-compatible server.

    Two frozen variants exist so benchmark.py can produce a genuine
    before/after comparison."""

    def to_llama_cpp_args(self) -> list[str]: ...
```

An immutable configuration value (never mutated after construction — a
`benchmark.py` run needs a stable "before" config to diff against an
"after" config, and a mutable object would let the diff silently drift).
`to_llama_cpp_args` renders the dataclass into the llama.cpp server's real
CLI argv, so the config that produced a benchmark result is exactly the
config that started the server, not a second, hand-maintained translation
of it.

### LLM sequence flow — one user question, end to end

```
User question
        │
        ▼
Coordinator.__call__ / run  (dataclass instance: feature_agent, drift_agent bound)
        │
        ├──▶ HttpSpecialistClient(feature_agent url).run(request)  ─┐
        │                                                            │ await, bounded by max_hops
        └──▶ HttpSpecialistClient(drift_agent url).run(request)    ─┘
        │
        ▼
Coordinator.failure_policy(error)   ← only on a specialist exception
        │
        ▼
raw answer text + citations
        │
        ▼
CitationGuard.evaluate(output, citations)  ──▶  CitationDecision
        │
   (if PII found)
        ▼
CitationGuard.redact(output)
        │
        ▼
CoordinatorResponse{answer, specialists, status}  ──▶  user

Separately, offline / on ingestion trigger:
RagIngestionPipeline.fetch_documents → parse_and_chunk → deduplicate_chunks
    → enforce_licensing_and_metadata → write_vectors(embedding_version)
        │
        ▼
PgVectorStore  ← queried by feature_agent/drift_agent's own retrieval step,
                  which happens inside their HttpSpecialistClient.run() call
                  above, not shown as a separate top-level box here.

ModelServerConfig.to_llama_cpp_args() → server process argv
        │
        ▼
llama.cpp server (OpenAI-compatible) ← the model every specialist ultimately
                                        calls through agentgateway (ADR-016)
```
