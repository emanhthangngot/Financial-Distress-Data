---
phase: 8
title: "Phase 8: Evaluated RAG, LangGraph agents and free inference"
status: pending
priority: P1
effort: "Re-estimate after P0 G3-serving/G5-providers results; historical baseline 8-12 days"
dependencies: ["phase-00-gates.md", "phase-06-platform.md"]
owns: ["platform/inference/", "platform/serving/llm-*", "platform/agents/", "platform/agentgateway/", "src/agents/", "src/llm/"]
---

# Phase 8: Evaluated RAG, LangGraph agents and free inference

## Overview

Re-earn the 60 LLM rubric rows with executed evidence, and deliver the session extensions this phase
owns: LangChain model/tool integration, bounded LangGraph agent orchestration, temporal/authorization
filtered RAG, free-provider inference and a human-reviewed evaluation baseline. Local scaffolding
(providers, graph, retrieval filters, benchmark fixes, eval runner wiring) does not wait for cloud;
live serving and end-to-end exit do.

What is retained, not rebuilt: MCP servers and their typed contracts (`src/llm/contracts.py`), the
agent registry chain, the sandbox boundary, the existing API surface and auth, citation/provenance
governance, pgvector. LangChain/LangGraph replace hand-rolled model and orchestration plumbing
(`src/agents/runtime.py:111-203`, `src/agents/coordinator.py:43-104`) through one parity pilot and
then a clean cutover — never two live orchestration paths.

Rubric rows are unchanged by the framework decision. The five agent-registry rows the earlier plan
files never named remain in scope: LLM 6 (registry deployed), LLM 14/20/24 (feature, drift and
coordinator agents published), LLM 44 (registry UI, routed by P9), plus LLM 25 (warm-up/standby).
All 60 LLM rows retain `validation_command` and `behavioral_assertion`; capture them first in P12.

### Session contract applied here

| Master decision | Effect in this phase | Where |
|---|---|---|
| Rubric before image fidelity | KServe 0.18 / llm-d / LWS / GIE are optional; no AC asserts component parity | §Serving backend |
| No additional monetary spend | Provider allowlist with no paid route; free-tier limits measured, never assumed | §Provider policy, AC-P8-19/28 |
| LangChain + LangGraph | Parity pilot then clean cutover; MCP, API, auth, telemetry retained | §Framework boundary, AC-P8-18 |
| Free inference | Groq Free primary, one verified free fallback; no silent fallback in evaluation or after partial streaming | §Provider policy, AC-P8-21/22/26 |
| Evaluated RAG | Temporal + authorization filters before context; supported citations; paired hybrid/reranker experiments | §Retrieval, AC-P8-24/25/27 |
| Memory | Session-only state, scoped identity, TTL; no cross-session semantic memory | §Session state, AC-P8-23 |
| Fine-tuning conditional (P7) | P8 only declares the serve-compat lane a P7 adapter must satisfy | §Serve path for a local adapter |
| Data before model claims | End-to-end exit consumes real P4/P5 outputs, not fixtures | §Data-integration subgate |

### Non-goals for this phase

No second agent framework and no second vector database. No arbitrary shell or code-execution tool
for agents. No GraphRAG or new entity registry. No paid provider tier, paid model route or paid
managed inference. No 24/7 public endpoint. No ETL rewrite — data movement stays with P4/P5. No
deletion of working auth or CI to match a diagram. No fine-tuning, adapter training or RLHF here.

## Requirements

Functional:

- An LLM inference platform is deployed and reproducible from the repo, serving completions through a
  custom model server that is not the tutorial default (LLM 2, LLM 3).
- A global model config resolves for all three agents and carries the provider allowlist (LLM 5);
  the agent registry is deployed with all three agents published (LLM 6, 14, 20, 24, 44).
- Agents run multi-replica with autoscale, inside the sandbox (LLM 12, 13, 18, 19, 23).
- Warm-up/standby measurably reduces cold-start latency, with the resident-cost delta reported
  beside it (LLM 25).
- A/B across two allowlisted model/config variants holds a 9:1 split under load and is compared on
  cost, latency and answer quality (LLM 55, 56).
- Both LLM notebooks execute: agent ↔ MCP for feature pull and drift (LLM 21); agent ↔ MCP for RAG
  data (LLM 22).
- The RAG pipeline runs text → chunk → embed → pgvector with license/PII/quarantine governance
  recorded in `ml.rag_quarantine` (LLM 7-8).
- The model-server benchmark reports only metrics measured under the conditions it names (LLM 4).
- The agent plane runs on LangGraph with LangChain model/tool integration after a parity pilot; the
  previous orchestration is deleted, not flagged off.
- Every model call passes a provider allowlist with bounded retries, a circuit breaker, and explicit
  unavailable and partial-stream failure states.
- Retrieval is authorization- and knowledge-time-filtered before the candidate set exists; answers
  abstain when permitted evidence is insufficient; every citation resolves to a stored chunk revision.
- A 100-case human-reviewed evaluation baseline (retrieval, answer, agent task) is published with
  disjoint development and holdout splits and frozen revisions.

Non-functional: zero additional monetary spend; no always-on requirement introduced by this phase;
sandbox egress stays scoped to `agentgateway-system` after injection; `phase2-llm` dissolved;
dependency versions resolved and recorded at execution time, never guessed here.

## Architecture

```
serving namespace (backend chosen at G3-serving)
  custom OpenAI-compatible model server (src/llm/model_server.py contract)
  ClusterIP gateway; weighted split llm-ab -> variant-a (9) / variant-b (1)
  mTLS STRICT + AuthorizationPolicy (P6)
  [optional, justified only] KServe LLMInferenceService / llm-d / LWS / GIE

agents namespace (LangGraph)
  coordinator graph: feature node -> MCP feature tool
                     drift node   -> MCP drift tool
                     answer node  -> provider gateway -> allowlisted model
  checkpointer: session-scoped thread, TTL-swept, no cross-thread store
  agent registry (all three published; UI routed by P9), global ModelConfig

provider gateway (src/llm/providers.py)
  primary Groq Free | one verified free fallback | local self-hosted server
  allowlist, paced retries, circuit breaker, degraded marking, zero paid routes

agents-sandbox -> agentgateway-system -> (only) serving + api-serving
```

### Framework boundary — LangChain/LangGraph versus ours

Grounded in official documentation read 2026-09-10 (URLs in §Sources). No version is asserted beyond
floors the documentation itself states.

| Concern | Owner | Grounding |
|---|---|---|
| Chat-model client and provider switching | LangChain (`init_chat_model`, provider classes) | *Models* |
| Model retry/backoff | LangChain — automatic exponential backoff with jitter, default `max_retries=6`; 429/5xx retried, 401/404 not | *Models* |
| Request pacing | LangChain `InMemoryRateLimiter(requests_per_second, check_every_n_seconds, max_bucket_size)`; documented to limit request count, not size | *Models* |
| Fallback between allowlisted providers | LangChain `ModelFallbackMiddleware` | *Prebuilt middleware* |
| Bounded tool retry and tool-error surfacing | LangChain `ToolRetryMiddleware` (defaults `max_retries=2`, `backoff_factor=2.0`, `initial_delay=1.0`, `max_delay=60.0`, jitter ±25 %), `ToolErrorMiddleware` | *Prebuilt middleware* |
| Step ceiling | LangChain `ModelCallLimitMiddleware(thread_limit, run_limit, exit_behavior)` replaces the hand-rolled `max_hops` (`src/agents/coordinator.py:47`) | *Prebuilt middleware* |
| PII on input and streamed output | LangChain `PIIMiddleware` (redact/mask/block/hash; `apply_to_output` also redacts streamed wire output) | *Prebuilt middleware* |
| Graph topology, per-step state, resumability | LangGraph `StateGraph`; middleware hooks run inside the compiled graph and an agent can be a node in a larger graph | LangGraph *Overview*, *Middleware overview* |
| Session state | LangGraph checkpointer — thread-scoped snapshots keyed by `thread_id` | *Persistence*, *Checkpointers* |
| Cross-session memory | **Not enabled.** LangGraph Store is the cross-thread mechanism and is deliberately unused | *Persistence* (checkpointer vs store) |
| Streaming projections | LangGraph/LangChain `updates` / `messages` / `custom` modes; event streaming is the newer typed API | *Streaming* |
| MCP tools | **Ours.** `langchain.mcp.MCPAdapter` exists but is documented beta, needs `langchain[mcp]>=1.4.0`, warns once per process and may change. Our clients are typed and policy-bound (`src/agents/runtime.py:44-108`, `src/llm/contracts.py:141-199`), so they are wrapped as LangChain tools and keep their validation and tracing. `MCPAdapter` is adopted only if the pilot shows identical validation and trace emission | *MCP* |
| Circuit breaking | **Ours.** The middleware catalogue documents retries, fallback and call limits — not a circuit breaker. `src/llm/providers.py` owns it; no framework claim is made | *Prebuilt middleware* (absence) |
| Citation/abstention policy, governance, quarantine | **Ours** — `src/llm/citation_guard.py`, `data_governance.py`, `contracts.py` keep their role | in-repo |
| Vector store | **pgvector, retained.** `langchain-postgres`' `PGVector` supports metadata filters (`$eq`, `$in`, `$lte`, `$and`), scored search and `as_retriever`, is psycopg3-only and has no schema-migration mechanism. `src/llm/rag/pgvector_store.py` keeps ownership of the `ml.rag_*` schema; the LangChain store is used only if it reads that schema without owning it | *PGVector* |

### Parity pilot, then clean cutover

1. Rebuild exactly one path — coordinator → feature MCP tool → drift MCP tool → answer — as a
   LangGraph graph behind the unchanged FastAPI surface and unchanged request/response models
   (`src/agents/models.py`, `src/agents/coordinator.py:20-34`), using the P9-supplied parity fixture
   of current external schemas, auth and session flow.
2. Score pilot against current path on the P11 development cases: equal or better citation validity
   and task success, identical request contract, no new request-time external dependency,
   unchanged auth and telemetry behaviour (AC-P8-18).
3. Cut over the remaining agents, delete `OpenAICompatibleRenderer` (`src/agents/runtime.py:111-203`)
   and the bespoke hop/parallel logic it fed, and remove every caller. No flag, no shim, no
   re-export. If parity fails, fix the adapter boundary and re-run the same eval — do not keep a
   second permanent runtime.

`decode_model_response` (`:206-239`) is deleted with the renderer, except for the SSE-usage rule it
encodes (`:228-229`), which moves into the benchmark fix (B-1).

### Provider policy — allowlist, bounded retries, circuit breaker, stream failure

`src/llm/providers.py` (new) is the single model egress. `src/agents/runtime.py:132` hardcodes
`Authorization: Bearer not-required-local-model`; that literal is removed and credentials come from
ESO/Vault (P6).

- **Allowlist, deny by default.** A `(provider_id, model_id)` outside the global `ModelConfig`
  allowlist is rejected before egress. The allowlist holds Groq Free (primary), the single free
  fallback verified at G5-providers (Gemini is a candidate until then), and the local self-hosted
  server. Paid routes and paid-tier switches are absent from configuration, not merely unused.
- **Bounded retries and pacing.** LangChain's model retry plus `ToolRetryMiddleware` for tools, with
  an explicit small ceiling; `InMemoryRateLimiter` configured from the free-tier limit **measured**
  at G5-providers, never a guessed rate.
- **Circuit breaker (ours).** Per `(provider_id, model_id)`: open after N consecutive terminal
  failures in a window; while open, return `provider_unavailable` with no network call; one half-open
  probe closes or re-opens it. This exists to stop retry storms against a free tier.
- **Fallback without false equivalence.** On primary exhaustion the fallback answers, and the
  response records the provider that actually answered plus `degraded: true` and a reason. Capability
  differences are published (§Capability differences). **During a scored evaluation run there is no
  fallback at all** — providers are pinned and a provider change voids the run.
- **Stream failure is explicit.** Before the first token: normal error envelope, no partial output.
  After the first token: terminal error event carrying the same `request_id`, transcript marked
  incomplete, and **no fallback re-generation appended to a partially streamed answer**. Circuit open
  or provider down: a single `unavailable` response with its reason. Today `render` buffers all
  chunks and decodes only at the end (`src/agents/runtime.py:161-174`), so a mid-stream failure
  silently yields nothing; that behaviour is replaced.

#### Capability differences (filled by measurement, never assumed)

| Capability | Groq (primary) | Free fallback | Local self-host |
|---|---|---|---|
| Tool calling | documented yes | verify at G5-providers | verify against served model |
| Token-level streaming | documented yes | verify | server-dependent |
| Token usage reporting | documented yes | verify | server-dependent |
| Image input | documented for named vision models | verify | no |
| Audio / video input | documented no | verify | no |
| Custom adapter / LoRA | no (hosted API) | no (hosted API) | possible, see §Serve path |
| Rate limit | measured at gate | measured at gate | bounded by the serving window |

The Groq column cites the ChatGroq model-feature table. An unfilled cell blocks AC-P8-21.

### Session state, TTL and tenant isolation

Checkpointers only; no LangGraph Store, so there is no automatic cross-session semantic memory.

- P9 derives the principal server-side; `session_id` is not authorization. P8 scopes state by the
  resolved principal/tenant, deriving `thread_id` from `(tenant, session)` within the documented
  255-character bound.
- LangGraph documentation states checkpoints accumulate and recommends pruning or a retention policy,
  and that in-memory savers lose everything on restart. Multi-replica agents therefore use a
  persistent checkpointer plus a **TTL sweep**; an expired session starts from empty state.
- A valid `session_id` presented by another principal returns not-found, never another transcript.
- Durability mode (`exit` / `async` / `sync`) is chosen and recorded with the checkpointer so a
  mid-run replica restart has defined behaviour.

### Authorization and knowledge-time cutoff precede retrieval

Both filters build the candidate set; neither is a post-filter:

1. Resolve principal, tenant and permitted `access_class` from P9's server-side identity.
2. Resolve `cutoff_ts` from the request; absent is rejected, never silently widened.
3. Push `access_class ∈ permitted AND known_from_ts <= cutoff_ts` into the pgvector query as a
   metadata filter (`$in`, `$lte`, `$and` per the PGVector integration docs).
4. Only then run similarity search.

Post-filtering is prohibited because top-k over ineligible chunks silently starves the answer while
looking healthy. Falsifiable form: removing either predicate must make AC-P8-24 fail.

### Retrieval, provenance and abstention

- pgvector retained. `src/llm/rag/pgvector_store.py` keeps the `ml.rag_*` schema, the documented
  `register_vector` caller obligation (`:11-21`) and `ON CONFLICT (content_hash, embedding_version)
  DO NOTHING` idempotency (`:90`).
- Hybrid (lexical + vector) retrieval and reranking are **paired experiments**: same corpus, same
  prompts, same pinned providers, one variable changed, pre-registered metric and margin, scored on
  the **development split only**. Kept only on measured improvement; rejection is a valid recorded
  outcome. Both candidates must run at zero spend — Postgres full-text for lexical, a local CPU
  cross-encoder for reranking.
- Provenance: every emitted citation resolves to a stored chunk with document URI and
  ingestion/embedding revision; unresolvable citations fail closed, preserving `CitationGuard`
  behaviour (`src/llm/citation_guard.py:3-6`).
- Abstention: when the permitted, in-cutoff candidate set is empty or below the evidence threshold,
  the agent abstains with an explicit reason and zero citations. Abstention scores as correct in the
  P11 harness; fabricated coverage does not.

### Request and response contract (P8 side)

P9 owns the external API schema and streaming event semantics; P8 consumes and enforces.

- Request fields P8 relies on: `request_id`, `session_id`, `ticker`, `cutoff_ts`, `question`, plus
  the resolved `provider_id`, `model_id`, `prompt_revision`, `corpus_revision` that P8 records.
- `company_id`/`company_key` are not reintroduced as a competing key; feature retrieval identity is
  P5's contract.
- Responses keep the existing schema. P8 adds only citations with provenance, the provider that
  answered, `degraded`/abstained markers, and the explicit unavailable and partial-stream forms.
  Anything the current schema cannot carry is versioned deliberately with P9, not smuggled in.

### Evaluation baseline — P11 owns harness and corpus, P8 runs it

P8 publishes `docs/evidence/llm/baseline-<dataset_revision>.json`, one entry per metric with
`metric_name`, `value`, `ci_low`/`ci_high` (bootstrap 95 %), `n`, `dataset_revision`, `split`,
`provider_id`, `model_id`, `prompt_revision`, `corpus_revision`, `harness_revision`, `captured_ts`.

Rules that make the number mean something, all graded by AC-P8-26: 100 human-reviewed cases;
disjoint development and holdout splits with the holdout sealed and read once per candidate;
providers and models pinned for the whole scored run; no expected answer, gold citation or holdout
text present in any prompt template, few-shot example or retrieval corpus. P7's conditional
fine-tuning gate and P10's agent promotion consume this artifact read-only.

### Model-server benchmark — three measurement defects (LLM 4)

All three are read from the current source and fixed under AC-P8-12. P12's AC-P12-5 states the same
rule for telemetry: SSE chunks are never treated as tokens.

| # | Defect | Evidence | Fix |
|---|---|---|---|
| B-1 | An SSE event is counted as a token: every non-blank line that is not `data: [DONE]` increments `token_count`, so role-only deltas, the finish-reason chunk, the usage chunk and framing lines all count. `inter_token_latency` and `throughput_tokens_per_second` are wire-line rates mislabelled as token rates | `src/llm/benchmark.py:58-64,95,96` | Send `stream_options: {"include_usage": true}` and read `usage.completion_tokens` — already done in-repo (`src/agents/runtime.py:138` sets it, `:228-229` reads it); otherwise count content deltas only (`:234`); if neither is available, fail the run rather than report a line count |
| B-2 | Concurrency is a label, not a condition: `concurrency` is accepted, stored into the result and never used — the prompt loop is strictly sequential, so any "concurrency = N" claim is false | `src/llm/benchmark.py:87,93-94,105` | Drive N genuinely concurrent streams and report achieved concurrency and queue wait beside the requested value, or delete the parameter and report 1. P11's load harness is the throughput/concurrency authority |
| B-3 | Client memory reported as server memory: `read_peak_rss_mb` defaults to `/proc/self/status`, is called with that default and surfaced as `peak_rss_mb` — the benchmark process's own RSS | `src/llm/benchmark.py:69,89,103,121` | Read the serving container's working set (cgroup inside the server pod, or the P12 container-memory metric), or drop the column. Unattributable metrics do not appear in the artifact |

The write-up names the backend actually benchmarked and cites no metric from a backend that was not
run. Quantization / thread / batch comparisons are acceptable optimization evidence (G3-serving).

### Serving backend selection

Graded rows are LLM 2 (platform deployed reproducibly), LLM 3 (custom model server), LLM 4
(benchmark + optimize), LLM 55/56 (A/B), LLM 25 (warm-up), plus the agent rows. None of them names a
specific controller.

- **Default:** the self-hosted OpenAI-compatible custom model server already contracted in
  `src/llm/model_server.py:3-9`, on the existing KServe path if viable, behind a ClusterIP gateway
  with a weighted A/B split. G3-serving prefers a small local model plus the existing path.
- **llm-d / LWS / GIE / a KServe major upgrade are not required** and are not automatic deployments.
  They may be used only with a capability-specific justification recorded in
  `platform/inference/VERSIONS.md`, at no additional spend.
- `VERSIONS.md` records the backend and version actually deployed and why, so no artifact implies a
  component that is not running. Image-only omissions are documented, not treated as failures.
- Warm/standby, multi-replica autoscale, registry and sandbox are properties of the agent plane and
  remain graded regardless of backend choice.

### Serve path for a local adapter (interface for P7's conditional gate)

Groq and the free fallback are hosted APIs and cannot load a custom adapter — adapter-on-hosted is a
serve-compat FAIL and STOP is an honest outcome. The local self-hosted custom model server is the
only lane that can serve one, and only if the adapter's base model equals the served base model, the
adapter converts to the server's weight format, and it fits a no-spend serving window. P8 exposes the
lane and its constraints; P7 owns training, packaging and the decision.

### Data-integration subgate (P4/P5)

Provider gateway, graph, retrieval filters, benchmark fixes and eval wiring may be built and unit-
proved before P4/P5 land. **End-to-end exit requires real data**: features served through MCP from
P5's store (AC-P8-9, AC-P8-13) and a RAG corpus ingested by the P4-backed pipeline (AC-P8-11), with
`known_from_ts` populated from the P2 contract so AC-P8-24 is meaningful. Fixture-only runs are
scaffolding evidence and are labelled as such, never as integration evidence.

### Instrumentation interface

P12 owns `src/observability/telemetry.py` and the observability deployments; P8 proposes the events
and labels it needs (per-agent and per-MCP-tool call and failure counters, round-trip timing, TTFT,
token usage sourced from provider usage rather than SSE chunk counts, provider/model/prompt/corpus
revision labels) and consumes the agreed interface. Edits to telemetry implementation are serialized
with P12.

### Dependency versions

`pyproject.toml` currently has no LangChain, LangGraph or provider package (`pyproject.toml:28-29,
46-50` hold `pgvector` and `psycopg` only). P8 owns these additions and resolves versions from a real
resolution at execution time, recording the lock — no version is promised here. Documentation-stated
floors to re-check against that lock: `langchain[mcp]>=1.4.0` for the beta `langchain.mcp` namespace,
and the middleware notes `langchain>=1.3.14` (`ToolErrorMiddleware`), `>=1.3.16` (retry
classification) and `>=1.3.2` (`PIIMiddleware` streamed-output redaction). Every added package must
be free to use.

### Rollback and recovery

Agent releases roll back as a set: prompt revision, provider/model identity, corpus revision and the
LangChain/LangGraph dependency lock (P10 records them; hosted model IDs are not image digests).
Session checkpoints are session-scoped and TTL-swept, so a rollback discards in-flight sessions
rather than migrating them — stated explicitly instead of assumed.

If, and only if, a KServe major upgrade is justified and taken, its CRD schema change is not reversed
by `git revert`: the pre-upgrade `InferenceService` export becomes a hard entry artifact and rollback
is restore-from-export. With the default self-hosted path, this phase has no exception to the
git-revert plus resync boundary.

## Related Code Files

- Modify: `financial-distress-gitops/platform/inference/` — deploy the selected backend; drop unused
  vendored charts
- Modify: `platform/inference/VERSIONS.md` — backend, version, justification, entry-artifact path if
  an upgrade is taken
- Create: `platform/serving/gateway.yaml` (ClusterIP), `platform/serving/httproute-llm-ab.yaml`
  (9:1), `platform/serving/llm-variant-a.yaml`, `llm-variant-b.yaml`
- Create: `platform/agents/registry.yaml`, `platform/agents/model-config.yaml` (allowlist, model ids,
  prompt revision), `platform/agents/warm-pool.yaml`
- Create: `src/llm/providers.py` — allowlist, pacing, circuit breaker, degraded marking, unavailable
  and partial-stream failure forms
- Create: `src/agents/graph.py` (LangGraph coordinator graph), `src/agents/tools.py` (MCP clients as
  LangChain tools, retaining validation and tracing)
- Modify: `src/agents/runtime.py` — keep the FastAPI surface; delete `OpenAICompatibleRenderer`
  (`:111-203`) and `decode_model_response` (`:206-239`) at cutover; remove the hardcoded bearer (`:132`)
- Modify: `src/agents/coordinator.py` — hop/parallel policy replaced by graph edges and
  `ModelCallLimitMiddleware`; request/response models retained
- Modify: `src/agents/registry.py`, `feature_agent.py`, `drift_agent.py`
- Modify: `src/llm/benchmark.py` (B-1/B-2/B-3), `rag_pipeline.py`, `citation_guard.py`,
  `data_governance.py`, `embedding_registry.py`, `src/llm/rag/pgvector_store.py`
- Modify: `pyproject.toml` — LangChain/LangGraph/provider packages with resolved versions
- Create: `notebooks/agent-feature-drift-demo.ipynb`, `notebooks/agent-rag-demo.ipynb`
- Restore: `platform/security/authorization-policies.yaml` (serving scope, with P6)
- Consume: `tests/eval/` harness and corpus (P11); P9 parity fixture; P12 telemetry interface
- Produce: `docs/evidence/llm/baseline-<dataset_revision>.json`

## Implementation Steps

1. Record the serving backend decision from G3-serving and its justification in `VERSIONS.md`; if an
   upgrade is taken, capture the pre-upgrade export first.
2. Build `src/llm/providers.py`: allowlist, ESO-sourced credentials, measured rate limits, bounded
   retries, circuit breaker, degraded marking; prove no paid route is reachable from configuration.
3. Build the LangGraph parity pilot behind the unchanged API surface using P9's parity fixture;
   score it against the current path on P11 development cases.
4. Cut over remaining agents; delete the renderer and bespoke hop logic; remove every caller.
5. Session state: scoped `thread_id`, persistent checkpointer, TTL sweep, cross-principal negative test.
6. Retrieval: authorization and cutoff predicates at candidate-set construction; abstention path;
   citation resolution and provenance fields.
7. Serving: ClusterIP gateway, 9:1 split under a 1000-request load test, mTLS and AuthorizationPolicy.
8. Registry chain and global ModelConfig for all three agents; expose the registry UI Service (P9 routes it).
9. Multi-replica autoscale plus warm/standby; capture cold and warm latency and the cost delta.
10. Mesh injection and sandbox negative re-test.
11. RAG pipeline with governance into pgvector, using P4-backed sources.
12. Fix the benchmark (B-1/B-2/B-3) and run it on the deployed backend.
13. Run the P11 harness against the integrated stack; publish the baseline artifact.
14. Run the hybrid and reranker paired experiments on the development split; adopt or reject and record.
15. Execute both notebooks and the end-to-end analyst path; dissolve `phase2-llm`.

Verification for code changes in this phase: run the specific regression first, then
`.venv/bin/python scripts/run_lakehouse_quality_gates.py` before declaring the change done. Commands
introduced by this plan are planned until their owner implements them; they are never reported as
already run.

## Success Criteria

Legacy identifiers `AC-P8-1` … `AC-P8-17` are preserved; §Legacy AC map records every changed meaning.

- [ ] AC-P8-1: Argo CD -> syncs the selected inference backend -> `platform/inference/VERSIONS.md`
      records the backend, version and justification actually deployed; if a KServe major upgrade was
      taken, the pre-upgrade `InferenceService` export exists as an entry artifact captured first
- [ ] AC-P8-2: Platform operator -> describes the LLM gateway -> its Service type is `ClusterIP` and
      the cluster exposes no additional external LoadBalancer beyond the single NGINX entry
- [ ] AC-P8-3 **(LLM 56)**: Traffic split `llm-ab` -> receives 1000 requests -> routes within 5 % of
      the 9:1 weights across variant-a and variant-b
- [ ] AC-P8-4 **(LLM 5)**: Operator -> updates the global `ModelConfig` -> all three agents resolve the
      new configuration and the same provider allowlist with no per-agent edit
- [ ] AC-P8-5 **(LLM 6, 14, 20, 24)**: Operator -> queries the agent registry -> feature, drift and
      coordinator agents are listed with published versions
- [ ] AC-P8-6 **(LLM 12, 18, 23)**: Operator -> describes each agent Deployment -> replicas > 1 with an
      autoscaler; load raises replica count and it returns to baseline
- [ ] AC-P8-7 **(LLM 13, 19)**: Sandbox negative test after injection -> direct egress to the serving
      namespace is refused; through `agentgateway-system` it succeeds
- [ ] AC-P8-8 **(LLM 25)**: Operator -> enables warm/standby -> measured cold-start latency drops
      against the cold baseline; both latencies and the resident-cost delta are captured
- [ ] AC-P8-9 **(LLM 21)**: Data scientist -> runs `notebooks/agent-feature-drift-demo.ipynb` -> the
      LangGraph agent pulls real P5 features through MCP and performs drift detection
- [ ] AC-P8-10 **(LLM 22)**: Data scientist -> runs `notebooks/agent-rag-demo.ipynb` -> the agent pulls
      RAG data through MCP
- [ ] AC-P8-11 **(LLM 7-8)**: Pipeline -> runs text -> chunk -> embedding -> pgvector on P4-backed
      sources -> completes, with license, PII and quarantine decisions recorded in `ml.rag_quarantine`
- [ ] AC-P8-12 **(LLM 4)**: Engineer -> benchmarks the deployed model server -> TTFT, tokens/s and the
      chosen optimization comparison are reported with every number measured under the condition it
      names: token counts from `usage.completion_tokens` or counted content deltas (B-1), stated
      concurrency actually driven with achieved concurrency beside it (B-2), memory attributed to the
      serving container or omitted (B-3); no metric from an unrun backend is cited
- [ ] AC-P8-13: Coordinator agent -> answers an analyst prompt -> HTTP 200 with resolvable feature and
      drift citations, and a trace spanning coordinator -> MCP -> api-serving -> model backend with one
      span per graph node
- [ ] AC-P8-14: Platform operator -> lists namespaces -> `phase2-llm` no longer exists
- [ ] AC-P8-15 **(LLM 2)**: Argo CD -> syncs the LLM inference platform -> the stack is Synced/Healthy,
      a prompt to the platform endpoint returns a completion, and the deploy procedure is reproducible
      from the repo alone
- [ ] AC-P8-16 **(LLM 3)**: Engineer -> registers a custom model server (not the tutorial default) ->
      it serves a completion through the same gateway, and the write-up states what was customized
      (image, runtime args, weights source) and why
- [ ] AC-P8-17 **(LLM 55)**: Operator -> runs one agent behind two allowlisted `ModelConfig` variants ->
      both receive traffic and are compared side by side on token cost, latency and answer quality,
      naming the winner and the metric
- [ ] AC-P8-18 **(EXT-AGENT)**: Engineer -> runs the pilot and the current path over the P11 development
      cases -> the pilot matches or beats citation validity and task success with unchanged request
      contract, auth and telemetry; after cutover a grep for `OpenAICompatibleRenderer` and the bespoke
      hop logic returns zero hits and no flag selects between two orchestrations
- [ ] AC-P8-19 **(EXT-COST)**: Engineer -> requests a `(provider_id, model_id)` outside the allowlist ->
      it is rejected before egress; configuration and code contain no paid provider route or paid-tier
      switch, and no literal bearer token remains in `src/agents/`
- [ ] AC-P8-20: Engineer -> forces N consecutive provider failures -> the breaker opens, further calls
      return `provider_unavailable` without a network call, and one half-open probe closes it after
      recovery; retries per request never exceed the configured ceiling
- [ ] AC-P8-21: Engineer -> fails the primary provider outside an evaluation run -> the verified free
      fallback answers, the response names the answering provider and is marked `degraded` with a
      reason, and the capability table has no unfilled cell for that provider
- [ ] AC-P8-22: Engineer -> kills the upstream stream after the first token -> the client receives a
      terminal error event with the same `request_id`, the transcript is marked incomplete, and no
      fallback continuation is appended; a failure before the first token yields the normal error
      envelope with no partial text
- [ ] AC-P8-23: Engineer -> replays a `session_id` after its TTL -> state starts empty; the same
      `session_id` presented by another principal returns not-found; no cross-thread store is configured
- [ ] AC-P8-24: Engineer -> issues a request whose `cutoff_ts` precedes a known document -> the document
      is absent from the candidate set, not filtered from results; an unauthorized `access_class` yields
      zero candidates; removing either predicate makes the test fail
- [ ] AC-P8-25: Engineer -> asks a question with no permitted in-cutoff evidence -> the agent abstains
      with an explicit reason and zero citations; for an answerable question every citation resolves to
      a stored chunk with document URI and ingestion/embedding revision
- [ ] AC-P8-26 **(EXT-EVAL)**: Engineer -> runs the P11 harness against the integrated stack ->
      `docs/evidence/llm/baseline-<dataset_revision>.json` records 100 human-reviewed cases, disjoint
      development and holdout splits, pinned provider/model/prompt/corpus/harness revisions, per-metric
      value with a bootstrap 95 % interval, and a leakage check showing no holdout text in prompts or
      corpus; no provider fallback occurred during the run
- [ ] AC-P8-27: Engineer -> runs the hybrid-retrieval and reranker paired experiments -> each has a
      pre-registered metric and margin, is scored on the development split only, and is adopted or
      rejected on that evidence with the holdout untouched during iteration
- [ ] AC-P8-28 **(EXT-COST)**: Reviewer -> audits provider configuration and the resource-window ledger
      -> zero additional monetary spend for this phase, and every free-tier limit in the artifact is a
      measured value with its measurement date
- [ ] AC-P8-29 **(LLM novel idea 1)**: Reviewer -> opens the novel-idea artifact -> knowledge-time-bounded
      retrieval is documented with its falsifiable proof (predicate removal flips AC-P8-24)
- [ ] AC-P8-30 **(LLM novel idea 2)**: Reviewer -> opens the second novel-idea artifact -> the paired
      experiment gate plus abstention-with-provenance is documented with its measured outcome,
      including any rejected experiment
- [ ] AC-P8-31 **(EXT-FT interface)**: P7 -> applies its fine-tuning eligibility gate -> it reads this
      phase's baseline artifact and the declared serve-compat conditions; no P8 AC depends on a trained
      adapter existing, and a STOP outcome leaves every P8 row unaffected

### Legacy AC map

| AC | Status | Change |
|---|---|---|
| AC-P8-1 | rewritten | "KServe 0.18 sync" -> "selected backend recorded with justification"; export required only if an upgrade is taken |
| AC-P8-2 | rewritten | llm-d Gateway / `GatewayClass: istio` -> "the LLM gateway"; single-public-entry invariant kept |
| AC-P8-3 | rewritten | `HTTPRoute` group -> traffic split; isvc-a/b -> variant-a/b; tolerance unchanged |
| AC-P8-4 | extended | also asserts the provider allowlist resolves from the same ModelConfig |
| AC-P8-5, 6, 7, 10, 14, 15, 16 | retained | substance unchanged |
| AC-P8-8 | extended | resident-cost delta now asserted, not only advised |
| AC-P8-9, 11 | extended | require real P5 features and P4-backed sources (data-integration subgate) |
| AC-P8-12 | rewritten | requires B-1/B-2/B-3 fixed; unmeasured conditions may not be claimed |
| AC-P8-13 | extended | one span per graph node |
| AC-P8-17 | extended | variants must come from the allowlist |
| AC-P8-18…31 | new | cutover parity, provider policy, memory/tenancy, retrieval authorization, eval baseline, experiment gates, spend, novel ideas, P7 interface |
| — | removed | "KServe 0.18 CRD live or ADR-004 branch B" as a requirement, and the 60-row re-capture framed as image parity: backend choice is recorded in `VERSIONS.md` and no AC asserts component parity |

Master anchors: EXT-AGENT -> AC-P8-18; EXT-EVAL -> AC-P8-26; EXT-COST -> AC-P8-19, AC-P8-28;
EXT-FT -> AC-P8-31; O-4 (no knowledge-time leakage) -> AC-P8-24.

## Risk Assessment

**Cutover becomes a permanent dual path.** Signal: a runtime flag selecting orchestration, or the
renderer surviving the cutover commit. Mitigation: AC-P8-18 grades the absence of the old path and
the pilot is one path only. Response: finish the migration or revert the pilot; never ship both.

**Beta framework APIs move.** Signal: `LangChainBetaWarning` from `langchain.mcp`, or a middleware
signature that does not match the resolved package. Mitigation: MCP adapter optional by design; no
version claimed at plan time. Response: keep the wrapped typed clients out of the beta path.

**Free-tier limits break eval and load runs.** Signal: 429s during AC-P8-3 or AC-P8-26. Mitigation:
pacing from measured limits, circuit breaker, runs inside authorized windows. Response: reduce rate
and re-run; never buy a tier — that violates the cost contract and voids provider pinning.

**Fallback silently treated as equivalent.** Signal: a metric reported without the answering provider.
Mitigation: AC-P8-21 and AC-P8-26 (no fallback inside a scored run). Response: void the mixed run and
re-run pinned.

**Holdout contamination.** Signal: monotonically improving holdout scores across iterations.
Mitigation: sealed holdout read once per candidate; AC-P8-27 checks access. Response: rebuild the
holdout from unused material and re-freeze; a leaked holdout has no evidential value.

**Session state leaks or grows unbounded.** Signal: a transcript visible to another principal, or
checkpoint growth with no expiry. Mitigation: principal-scoped `thread_id`, no store, TTL sweep, all
graded by AC-P8-23. Response: purge and fix the derivation, not the API surface alone.

**Cloud capacity never materializes.** Signal: G0-cloud/G2-window stay blocked. Mitigation: local
scaffolding ACs are independent; live ACs record `blocked/unverified`. Response: keep the blocked
state visible; never relabel a local run as cluster evidence.

**Data integration deferred until the end.** Signal: eval and notebook ACs pass on fixtures only.
Mitigation: the P4/P5 subgate defines which ACs require real data. Response: mark fixture runs as
scaffolding evidence and re-run after integration.

**Warm mode raises the resident floor.** Signal: cost rises after AC-P8-8. Mitigation: standby rather
than warm-resident, scheduled inside serving windows. Response: report cost and latency deltas
together — the row grades both.

**Registry claimed from the existing web page.** Signal: AC-P8-5 asserted without a registry service.
Mitigation: LLM 6 grades the deployed registry, LLM 44 grades the UI separately. Response: deploy the
service; the UI alone does not satisfy LLM 6.

**Pre-fix benchmark numbers reused.** Signal: tokens/s matching a pre-fix run, or a concurrency the
harness never drove. Mitigation: AC-P8-12 requires a measurement source per metric. Response: discard
and re-run; a mislabelled metric is worse than a missing one.

**Purge loses banked LLM evidence.** Signal: a P12 capture row cannot be re-earned. Mitigation: all 60
rows keep `validation_command` and `behavioral_assertion`; capture LLM rows first. Response: restore
implementation from history — the code was never deleted, only the evidence.

## Sources

Official documentation read 2026-09-10; the older `python.langchain.com` and
`langchain-ai.github.io/langgraph` paths redirect to these canonical URLs.

- LangChain overview (`create_agent`, built on LangGraph) — `https://docs.langchain.com/oss/python/langchain/overview`
- LangChain *Models* (`init_chat_model`, `max_retries` default 6 with backoff+jitter, retryable vs
  non-retryable errors, `InMemoryRateLimiter`) — `https://docs.langchain.com/oss/python/langchain/models`
- LangChain *Middleware overview* — `https://docs.langchain.com/oss/python/langchain/middleware/overview`
- LangChain *Prebuilt middleware* (`ModelFallbackMiddleware`, `ModelRetryMiddleware`,
  `ToolRetryMiddleware`, `ToolErrorMiddleware`, `ModelCallLimitMiddleware`, `PIIMiddleware`) —
  `https://docs.langchain.com/oss/python/langchain/middleware/built-in`
- LangChain *MCP* (`MCPAdapter`, beta namespace, `langchain[mcp]>=1.4.0`, transports) —
  `https://docs.langchain.com/oss/python/langchain/mcp`
- LangChain *Streaming* (`updates`/`messages`/`custom`, event streaming) —
  `https://docs.langchain.com/oss/python/langchain/streaming`
- LangGraph *Persistence* (checkpointer vs store, in-memory savers lost on restart, unbounded
  checkpoint growth, `thread_id` bound) — `https://docs.langchain.com/oss/python/langgraph/persistence`
- LangGraph *Checkpointers* (threads, super-step checkpoints, durability modes) —
  `https://docs.langchain.com/oss/python/langgraph/checkpointers`
- ChatGroq integration (`langchain-groq`, `GROQ_API_KEY`, feature table: tool calling, structured
  output, token-level streaming, token usage yes; audio/video input no) —
  `https://docs.langchain.com/oss/python/integrations/chat/groq`
- PGVector integration (`langchain-postgres`, psycopg3 only, metadata filter operators, scored search,
  `as_retriever`, no schema-migration mechanism) —
  `https://docs.langchain.com/oss/python/integrations/vectorstores/pgvector`

In-repo anchors used above: `src/llm/benchmark.py:58-64,69,87,89,93-96,103,105,121`;
`src/agents/runtime.py:44-108,111-203,132,138,161-174,206-239,228-229,234`;
`src/agents/coordinator.py:20-34,43-104,47`; `src/llm/model_server.py:3-9`;
`src/llm/rag/pgvector_store.py:11-21,90`; `src/llm/citation_guard.py:3-6`;
`src/llm/contracts.py:141-199`; `src/agents/registry.py:13-18`; `pyproject.toml:28-29,46-50`.

## Rubric Citations (phase-03 R-12 closure, appended 2026-09-05)

Every rubric row this phase owns per `docs/rubric-matrix-unified.csv`'s `owning_phase` column, cited so `scripts/verify_rubric_coverage.py` can resolve ownership to an assertion (R-12). Each line names the row's real `rubric_id`, its stated requirement, and its proof artifact/deliverable — the row's own matrix columns, not invented text. Rows whose capability is not yet implemented are forward specs, matching this file's other `AC-P8-*` entries.

- AC-P8-RUBRIC-1: `LLM-1-coordinator-agent-i-u-ph-i-2-agent-tr-n` — llm_engineer -> delivers "Deploy 1 Coordinator Agent — Điều phối 2 Agent ở trên" -> Capture kết quả đã tương tác (evidence: `docs/platform/evidence/llm/LLM-1-coordinator-agent-i-u-ph-i-2-agent-tr-n.md`)
- AC-P8-RUBRIC-2: `LLM-1-coordinator-agent-publish-agent-n-y-l-n-registry` — llm_engineer -> delivers "Publish Agent ở này lên registry đã deploy để đảm bảo governance" -> Demonstrate Agent có trên registry, được deploy với multi-replica, và màn hình UI chat với Agent (evidence: `docs/platform/evidence/llm/LLM-1-coordinator-agent-publish-agent-n-y-l-n-registry.md`)
- AC-P8-RUBRIC-3: `LLM-1-global-model-config-c-c-1-global-model-config-c-c-agen` — platform_operator -> delivers "Deploy 1 global model config để các Agent có thể dùng follow tutorial này, config này sẽ link tới inference platform ở trên thông qua cái ag..." -> Capture chứng minh phần code config đã được apply (evidence: `docs/platform/evidence/llm/LLM-1-global-model-config-c-c-1-global-model-config-c-c-agen.md`)
- AC-P8-RUBRIC-4: `LLM-a-b-testing-perform-a-b-test-for-different` — llm_engineer -> delivers "Perform A/B test for different LLM versions on the LLM inference platform" -> Capture màn hình thể hiện cách mọi người thực hiện A/B test và dashboard để đánh giá kết quả A/B test (evidence: `docs/platform/evidence/llm/LLM-a-b-testing-perform-a-b-test-for-different.md`)
- AC-P8-RUBRIC-5: `LLM-a-b-testing-when-you-deploy-a-new-model` — llm_engineer -> delivers "A/B Testing — When you deploy a new model, don't replace the old one directly, you should do A/B test, monitor it, and deploy." -> Capture màn hình thể hiện cách mọi người thực hiện A/B test và dashboard để đánh giá kết quả A/B test (evidence: `docs/platform/evidence/llm/LLM-a-b-testing-when-you-deploy-a-new-model.md`)
- AC-P8-RUBRIC-6: `LLM-a-llm-inference-platform--a-custom-model` — llm_engineer -> delivers "Setup a custom model" -> Document cách mọi người deploy, setup các custom model server để có thể triển khai riêng model của mọi người, cách thực hiện benchmark và op... (evidence: `docs/platform/evidence/llm/LLM-a-llm-inference-platform--a-custom-model.md`)
- AC-P8-RUBRIC-7: `LLM-a-llm-inference-platform--benchmark-model-server-and-opt` — llm_engineer -> delivers "Benchmark model server and optimize the platform" -> Document cách mọi người deploy, setup các custom model server để có thể triển khai riêng model của mọi người, cách thực hiện benchmark và op... (evidence: `docs/platform/evidence/llm/LLM-a-llm-inference-platform--benchmark-model-server-and-opt.md`)
- AC-P8-RUBRIC-8: `LLM-a-llm-inference-platform--llm-inference-platform-setup-c` — llm_engineer -> delivers "Deploy a LLM inference platform theo hướng dẫn này và set up gateway cho agent theo hướng dẫn này — Deploy LLM inference platform + setup cu..." -> Document cách mọi người deploy, setup các custom model server để có thể triển khai riêng model của mọi người, cách thực hiện benchmark và op... (evidence: `docs/platform/evidence/llm/LLM-a-llm-inference-platform--llm-inference-platform-setup-c.md`)
- AC-P8-RUBRIC-9: `LLM-c-i-t-h-th-ng-ch-warm-up--c-i-t-h-th-ng-ch-warm-up-cho-a` — llm_engineer -> delivers "Cài đặt hệ thống ở chế độ Warm Up cho agent theo hướng dẫn sau để tối ưu chi phí, đồng thời giảm thiểu thời gian startup" -> + Benchmark và document đã tối ưu được gì; + Document cách tăng HA (ví dụ set up replicas cho worker pool) (evidence: `docs/platform/evidence/llm/LLM-c-i-t-h-th-ng-ch-warm-up--c-i-t-h-th-ng-ch-warm-up-cho-a.md`)
- AC-P8-RUBRIC-10: `LLM-demonstrate-basic-underst-jupyter-notebook-demonstrate-a` — llm_engineer -> delivers "Jupyter notebook để demonstrate Agent tương tác với MCP servers để kéo dữ liệu từ feature store cho RAG (cả nhà coi ví dụ tại đây)" -> Capture kết quả đã tương tác (evidence: `docs/platform/evidence/llm/LLM-demonstrate-basic-underst-jupyter-notebook-demonstrate-a.md`)
- AC-P8-RUBRIC-11: `LLM-demonstrate-basic-underst-jupyter-notebooks-to-demonstra` — llm_engineer -> delivers "Demonstrate basic understanding of Agents — Jupyter notebooks to demonstrate basic understanding of Agents" -> Capture kết quả đã tương tác (evidence: `docs/platform/evidence/llm/LLM-demonstrate-basic-underst-jupyter-notebooks-to-demonstra.md`)
- AC-P8-RUBRIC-12: `LLM-novel-ideas-idea-1` — llm_engineer -> delivers "Novel ideas ; (không nhất thiết tự sáng tạo ra cái gì, có thể nghiên cứu dùng thêm các công cụ, hoặc kỹ thuật gì đó không được dạy ở EDAI) —..." -> Document idea + proof it worked! (evidence: `docs/platform/evidence/llm/LLM-novel-ideas-idea-1.md`)
- AC-P8-RUBRIC-13: `LLM-novel-ideas-idea-2` — llm_engineer -> delivers "Idea 2" -> Document idea + proof it worked! (evidence: `docs/platform/evidence/llm/LLM-novel-ideas-idea-2.md`)
- AC-P8-RUBRIC-14: `LLM-rag-m-b-o-data-governance-cho-pipe` — data_engineer -> delivers "Đảm bảo data governance cho pipeline (tương tự mini-coursework)" -> Capture màn hình thể hiện pipeline đã chạy thành công, với lineage trên DataHub (evidence: `docs/platform/evidence/llm/LLM-rag-m-b-o-data-governance-cho-pipe.md`)
- AC-P8-RUBRIC-15: `LLM-rag-rag-data-pipeline` — data_engineer -> delivers "RAG — RAG Data Pipeline" -> Capture màn hình thể hiện pipeline đã chạy thành công, với lineage trên DataHub (evidence: `docs/platform/evidence/llm/LLM-rag-rag-data-pipeline.md`)
- AC-P8-RUBRIC-16: `LLM-registry-for-agent-theo-t-registry-for-agent-theo-tutori` — platform_operator -> delivers "Deploy registry for agent theo tutorial này" -> Capture màn hình thể hiện registry đã được deploy (evidence: `docs/platform/evidence/llm/LLM-registry-for-agent-theo-t-registry-for-agent-theo-tutori.md`)
- AC-P8-RUBRIC-17: `LLM-routing-gateway-ui-cho-agent-registry` — platform_operator -> delivers "UI cho agent registry" -> Capture màn hình thể hiện từng setup đã thành công (evidence: `docs/platform/evidence/llm/LLM-routing-gateway-ui-cho-agent-registry.md`)
- AC-P8-RUBRIC-18: `LLM-web-api-cho-real-time-dri-1-agent-s-d-ng-mcp-tool-tr-n-v` — llm_engineer -> delivers "Deploy 1 Agent sử dụng MCP tool ở trên với multi-replica và auto-scale sử dụng cái này" -> Demonstrate Agent có trên registry, được deploy với multi-replica, giới hạn quyền thông qua Sandbox và màn hình UI chat với Agent (evidence: `docs/platform/evidence/llm/LLM-web-api-cho-real-time-dri-1-agent-s-d-ng-mcp-tool-tr-n-v.md`)
- AC-P8-RUBRIC-19: `LLM-web-api-cho-real-time-dri-agent-ch-y-trong-sandbox-m-b-o` — llm_engineer -> delivers "Configure Agent chạy trong Sandbox để đảm bảo security" -> Demonstrate Agent có trên registry, được deploy với multi-replica, giới hạn quyền thông qua Sandbox và màn hình UI chat với Agent (evidence: `docs/platform/evidence/llm/LLM-web-api-cho-real-time-dri-agent-ch-y-trong-sandbox-m-b-o.md`)
- AC-P8-RUBRIC-20: `LLM-web-api-cho-real-time-dri-c-s-d-ng-fastapi-data-validati` — data_engineer -> delivers "Web API cho Real-time Drift Detection (để làm MCP tool, tương tự như trên) — Có sử dụng FastAPI + data validation (với pydantic)" -> Demonstrate Agent có trên registry, được deploy với multi-replica, giới hạn quyền thông qua Sandbox và màn hình UI chat với Agent (evidence: `docs/platform/evidence/llm/LLM-web-api-cho-real-time-dri-c-s-d-ng-fastapi-data-validati.md`)
- AC-P8-RUBRIC-21: `LLM-web-api-cho-real-time-dri-publish-agent-tr-n-l-n-registr` — llm_engineer -> delivers "Publish Agent ở trên lên registry đã deploy để đảm bảo governance" -> Demonstrate Agent có trên registry, được deploy với multi-replica, giới hạn quyền thông qua Sandbox và màn hình UI chat với Agent (evidence: `docs/platform/evidence/llm/LLM-web-api-cho-real-time-dri-publish-agent-tr-n-l-n-registr.md`)
- AC-P8-RUBRIC-22: `LLM-web-api-cho-real-time-dri-s-d-ng-async` — data_engineer -> delivers "Sử dụng async" -> Demonstrate Agent có trên registry, được deploy với multi-replica, giới hạn quyền thông qua Sandbox và màn hình UI chat với Agent (evidence: `docs/platform/evidence/llm/LLM-web-api-cho-real-time-dri-s-d-ng-async.md`)
- AC-P8-RUBRIC-23: `LLM-web-api-k-o-d-li-u-user-1-agent-s-d-ng-mcp-tool-tr-n-v` — llm_engineer -> delivers "Deploy 1 Agent sử dụng MCP tool ở trên với multi-replica và auto-scale sử dụng cái này" -> Demonstrate Agent có trên registry, được deploy với multi-replica, giới hạn quyền thông qua Sandbox và màn hình UI chat với Agent (evidence: `docs/platform/evidence/llm/LLM-web-api-k-o-d-li-u-user-1-agent-s-d-ng-mcp-tool-tr-n-v.md`)
- AC-P8-RUBRIC-24: `LLM-web-api-k-o-d-li-u-user-agent-ch-y-trong-sandbox-m-b-o` — llm_engineer -> delivers "Configure Agent chạy trong Sandbox để đảm bảo security" -> Demonstrate Agent có trên registry, được deploy với multi-replica, giới hạn quyền thông qua Sandbox và màn hình UI chat với Agent (evidence: `docs/platform/evidence/llm/LLM-web-api-k-o-d-li-u-user-agent-ch-y-trong-sandbox-m-b-o.md`)
- AC-P8-RUBRIC-25: `LLM-web-api-k-o-d-li-u-user-c-s-d-ng-fastapi-data-validati` — data_engineer -> delivers "Web API kéo dữ liệu user (đã lưu thông qua feature pipeline) và chunk (đã được lưu thông qua RAG pipeline); (Web API này sẽ dùng để kéo dữ l..." -> Demonstrate Agent có trên registry, được deploy với multi-replica, giới hạn quyền thông qua Sandbox và màn hình UI chat với Agent (evidence: `docs/platform/evidence/llm/LLM-web-api-k-o-d-li-u-user-c-s-d-ng-fastapi-data-validati.md`)
- AC-P8-RUBRIC-26: `LLM-web-api-k-o-d-li-u-user-publish-agent-tr-n-l-n-registr` — llm_engineer -> delivers "Publish Agent ở trên lên registry đã deploy để đảm bảo governance" -> Demonstrate Agent có trên registry, được deploy với multi-replica, giới hạn quyền thông qua Sandbox và màn hình UI chat với Agent (evidence: `docs/platform/evidence/llm/LLM-web-api-k-o-d-li-u-user-publish-agent-tr-n-l-n-registr.md`)
- AC-P8-RUBRIC-27: `LLM-web-api-k-o-d-li-u-user-s-d-ng-async` — data_engineer -> delivers "Sử dụng async" -> Demonstrate Agent có trên registry, được deploy với multi-replica, giới hạn quyền thông qua Sandbox và màn hình UI chat với Agent (evidence: `docs/platform/evidence/llm/LLM-web-api-k-o-d-li-u-user-s-d-ng-async.md`)
