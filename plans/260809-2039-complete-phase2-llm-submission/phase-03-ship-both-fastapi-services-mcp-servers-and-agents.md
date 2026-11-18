---
phase: 3
title: "Ship both FastAPI services, MCP servers and agents"
status: completed
priority: P1
effort: "2d"
dependencies: [2]
---

# Phase 3: Ship both FastAPI services, MCP servers and agents

## Overview

The largest slice: 24 points across two Web APIs, their MCP wrappers, three
agents, the sandbox, autoscaling and the agent registry. Both API sections have
the identical six-row shape, so build one parameterized pattern and instantiate
it twice.

Rubric rows owned (24 points) — IDs and paths copied verbatim from the CSV:

| Points | rubric_id | artifact_path (authority) |
|---:|---|---|
| 1 | `LLM-web-api-k-o-d-li-u-user-c-s-d-ng-fastapi-data-validati` | source `apps/feature-mcp/app/main.py` |
| 1 | `LLM-web-api-k-o-d-li-u-user-s-d-ng-async` | source `apps/feature-mcp/app/main.py` |
| 2 | `LLM-web-api-k-o-d-li-u-user-in-the-form-of-mcp-tool-to-k8s` | gitops `charts/feature-mcp/Chart.yaml` — placeholder today |
| 2 | `LLM-web-api-k-o-d-li-u-user-1-agent-s-d-ng-mcp-tool-tr-n-v` | source `src/agents/feature_agent.py` |
| 1 | `LLM-web-api-k-o-d-li-u-user-agent-ch-y-trong-sandbox-m-b-o` | gitops `platform/agents/agent-sandbox.yaml` — placeholder today |
| 2 | `LLM-web-api-k-o-d-li-u-user-publish-agent-tr-n-l-n-registr` | gitops `platform/agents/agentregistry.yaml` — placeholder today |
| 1 | `LLM-web-api-cho-real-time-dri-c-s-d-ng-fastapi-data-validati` | source `apps/drift-mcp/app/main.py` |
| 1 | `LLM-web-api-cho-real-time-dri-s-d-ng-async` | source `apps/drift-mcp/app/main.py` |
| 2 | `LLM-web-api-cho-real-time-dri-in-the-form-of-mcp-tool-to-k8s` | gitops `charts/drift-mcp/Chart.yaml` — placeholder today |
| 2 | `LLM-web-api-cho-real-time-dri-1-agent-s-d-ng-mcp-tool-tr-n-v` | source `src/agents/drift_agent.py` |
| 1 | `LLM-web-api-cho-real-time-dri-agent-ch-y-trong-sandbox-m-b-o` | gitops `platform/agents/agent-sandbox.yaml` |
| 2 | `LLM-web-api-cho-real-time-dri-publish-agent-tr-n-l-n-registr` | gitops `platform/agents/agentregistry.yaml` |
| 2 | `LLM-registry-for-agent-theo-t-registry-for-agent-theo-tutori` | gitops `platform/agents/agentregistry.yaml` |
| 2 | `LLM-1-coordinator-agent-i-u-ph-i-2-agent-tr-n` | source `src/agents/coordinator.py` |
| 2 | `LLM-1-coordinator-agent-publish-agent-n-y-l-n-registry` | gitops `platform/agents/agentregistry.yaml` |

**The code lives at `apps/feature-mcp/app/main.py`, `apps/drift-mcp/app/main.py`
and `src/agents/{feature_agent,drift_agent,coordinator}.py`** — not under
`src/llm/api/`, `src/llm/mcp/` or `src/llm/agents/`. Those are the paths the
generated tests assert.

## Requirements

- Functional: two independent async FastAPI deployables with Pydantic models,
  `/healthz` and `/readyz`; each wrapped by a thin MCP server; each consumed by
  one specialist agent running multi-replica with autoscaling inside the
  restricted `agents-sandbox` namespace; a coordinator that fans out to both
  within a hop bound; an agent registry holding all three.
- Functional prerequisite: **a Feast online store reachable from inside the
  cluster.** Today `feature_repo/structured/feature_store.yaml` points at
  `phase2-redis:6379` and `feature_repo/rag/feature_store.yaml` at
  `phase2-postgres`, both docker-compose DNS names, with the registry on a
  MinIO `s3://` URL. None of that exists in GKE.
- Non-functional: **business logic never lives in the MCP layer** — the MCP
  server validates, authorizes, bounds and traces, then calls the API
  (retrofit decision 3). One parameterized Helm chart serves every FastAPI
  deployable (decision 5); the Argo ApplicationSet uses a directory generator
  (decision 6) against the `apps/dev/` directory phase 1 created.

## Architecture

**Feast online store, in-cluster — do this first.** Deploy Redis and Postgres
(pgvector) into the cluster, point a cluster profile of both feature repos at
them, make the Feast registry reachable from in-cluster pods, and run a
materialization job. Without it the Web API resolves `phase2-redis` to nothing
and 9 points evaporate. Budget this as its own half-day; it is not configuration.

**Web API kéo dữ liệu** reads the Feast online store by ID (`user_id`,
`chunk_id`) plus the RAG chunk store from phase-04. **Web API drift** serves
real-time drift detection over `src/drift/`. Both stay generic services with no
agent- or MCP-specific code, so the deferred ML track reuses them verbatim.

**RAG content is untrusted input.** Retrieved chunks reach the agent's context
through the MCP tool; today nothing treats them as hostile. Wrap retrieved
chunks in a delimited untrusted-content block, re-validate any tool-call
argument derived from retrieved text against the caller's original scope (never
widening it), and enforce a per-request tool-call budget. Add one negative test
with a poisoned fixture chunk asserting the tool is **not** called. This is
cheap and it is the only thing that makes "sandboxed" a claim rather than a
label.

**Sandbox** — the `agents-sandbox` namespace: restricted PSS enforce, tokenless
ServiceAccount with no RoleBinding, `runAsNonRoot` + `readOnlyRootFilesystem` +
`drop: [ALL]` + `seccompProfile: RuntimeDefault`, default-deny NetworkPolicy
with egress only to the MCP gateway and the model service, CPU/memory limits.

Evidence is the manifest plus negatives that map to the real threat model — the
old three-demo script was weaker than it looked:

- token absent: `test -f /var/run/secrets/kubernetes.io/serviceaccount/token`
  fails (with a tokenless SA, `kubectl get secrets` fails at credential
  resolution, not at RBAC — recording it as "403" would misstate the result)
- egress to `169.254.169.254` (the metadata endpoint) refused
- DNS restricted to `kube-dns` only, closing the DNS-tunnel exfil path the
  default-deny policy currently leaves open to all namespaces
- an attempt to reach the model service **bypassing agentgateway** refused
- `touch /x` → read-only filesystem

Record real command output verbatim, including the exact error string. Name it
accurately ("namespace-scoped Kubernetes sandbox: restricted PSS, default-deny
egress, tokenless ServiceAccount"); do not claim the kagent Agent Sandbox
product if it was not installed. **These negatives only mean anything because
phase 1 enabled NetworkPolicy enforcement** — before that, the egress denials
would silently pass through Cloud NAT.

**Autoscale.** KEDA HTTP `ScaledObject` per agent plus HPA on the FastAPI
services — subject to the phase-1 capacity budget. If the single node has no
headroom to scale into, capture scale-out with minimal CPU/memory requests and
a stated replica ceiling, and say so in the evidence rather than faking a
series. KEDA is not installed today; check before assuming, and fall back to
HPA, which the row text ("auto-scale") permits.

**Rolling update + auto fallback.** `helm upgrade --install --atomic` with a
deliberately bad revision proving automatic rollback, plus a healthy rolling
update with zero failed requests. Both halves are named in the row text.

**Registry.** Deploy the agent registry — `platform/agents/agentregistry.yaml`
is an empty placeholder today, so this is authoring, not editing — and publish
all three agents with version, status, replicas, model config and sandbox
policy. Four separate rows resolve to that manifest (2 + 2 + 2 + 2), so
registration is not optional polish.

## Related Code Files

- Create: `apps/feature-mcp/app/main.py` (+ its MCP wrapper module),
  `apps/drift-mcp/app/main.py` (+ its MCP wrapper module)
- Create: `src/agents/feature_agent.py`, `src/agents/drift_agent.py`,
  `src/agents/coordinator.py`
- Modify: `src/llm/contracts.py` (implement `McpToolService`,
  `AgentOrchestrationService`; note the retrieval stub is named
  `RagIngestionService`, not `RagRetrievalService`)
- Create: `feature_repo/*/feature_store.cluster.yaml` (or an env-driven profile)
- Create: Dockerfiles per deployable
- Create (GitOps): `charts/fastapi-service/` (the one parameterized chart),
  `apps/dev/feature-mcp/`, `apps/dev/drift-mcp/` (ApplicationSet inputs),
  `platform/data/redis.yaml`, `platform/data/postgres-pgvector.yaml`,
  `platform/agents/keda-scaledobject.yaml`
- Modify (GitOps): `charts/feature-mcp/Chart.yaml`, `charts/drift-mcp/Chart.yaml`,
  `platform/agents/agent-sandbox.yaml`, `platform/agents/agentregistry.yaml`
  — **all four are placeholder comments today**
- Create: 15 evidence files under `docs/platform/evidence/llm/`
- Regenerate (never hand-edit): `tests/platform/requirements/test_llm_ac_03_registry.py`,
  `test_llm_ac_05_feature_rag_api.py`, `test_llm_ac_06_drift_mcp.py`,
  `test_llm_ac_08_coordinator.py`

## Implementation Steps

1. Deploy Redis and pgvector Postgres in-cluster, repoint both Feast repos at
   them through a cluster profile, make the registry reachable, and run
   materialization. Prove a key-by-ID read from inside a pod before writing any
   API code.
2. Seed failing tests: tool contract, authorization, sandbox negatives, registry
   registration, citation, hop bound, idempotency, poisoned-chunk negative.
3. Build `apps/feature-mcp/app/main.py` — async endpoints, Pydantic
   request/response models, structured errors, `/healthz`, `/readyz`, and the
   Prometheus metrics middleware phase 4 consumes (adding it now avoids a second
   pass over both services). Include the token/TTFT counters phase 4 needs.
4. Build `apps/drift-mcp/app/main.py` to the same shape over `src/drift/`.
5. Write the single parameterized Helm chart and instantiate both services from
   values files. Prove `helm upgrade --install --atomic`, a clean rolling
   update, and automatic fallback from a bad revision.
6. Build both MCP wrappers: scoped tool schemas, identity and tool
   authorization, timeout and budget enforcement, structured tool errors, trace
   emission, untrusted-content delimiting. No business logic.
7. Author the `agents-sandbox` namespace policy and capture the five negative
   demonstrations from inside a running agent pod.
8. Deploy `src/agents/feature_agent.py` and `src/agents/drift_agent.py` against
   the phase-2 global `ModelConfig`, multi-replica, with autoscaling. Load past
   the threshold and capture scale-out and scale-in within the capacity budget.
9. Deploy `src/agents/coordinator.py` with bounded fan-out and a hop limit;
   prove it calls both specialists and returns cited results.
10. Author and deploy the registry; publish all three agents; capture its state.
11. Write the 15 evidence files, flip these 15 rows to `executed`, regenerate
    the CSV and requirement tests, re-run the audit. `make gcp-down`; record the
    delta.

## Success Criteria

- [x] Client -> calls the Web API kéo dữ liệu by ID -> receives Pydantic-validated data from a Feast online store that lives in the cluster, over an async path, with `/healthz` and `/readyz` green.
- [x] Operator -> deploys a deliberately bad revision with `helm upgrade --atomic` -> observes automatic rollback, and a separate clean rolling update with no failed requests.
- [ ] Load tester -> drives traffic past the autoscale threshold against each agent -> observes scale-out and scale-in with captured replica, request-rate and latency series, within the stated capacity ceiling.
- [x] Agent pod -> attempts the five negatives (token file, metadata endpoint, arbitrary DNS, direct-to-model bypass, filesystem write) -> is denied on all five, with verbatim command output and an enforced NetworkPolicy behind it.
- [x] Poisoned RAG chunk -> is retrieved into agent context -> does not cause a tool call outside the caller's original scope, proven by a negative test.
- [x] Coordinator -> receives one analyst question -> calls both specialists through their MCP tools within its hop bound and returns a cited answer.
- [x] Registry viewer -> queries the agent registry -> finds all three agents with version, status, replicas, model config and sandbox policy.
- [x] ML retrofitter -> reads the MCP layer -> finds no business logic there, one parameterized Helm chart serving both services, and the ApplicationSet discovering them by directory.

## Execution Notes

- The two async FastAPI services, MCP wrappers, specialist agents, bounded
  coordinator, registry API, sandbox policies, cluster Feast profiles and
  parameterized GitOps chart are implemented and deployed from the merged
  GitOps revision.
- Live verification covered Feast online writes, `/healthz`/`/readyz`, positive
  feature and coordinator calls, registry publication, tokenless/default-deny
  sandbox negatives, and an atomic bad-revision rollback.
- HPA configuration and the observed replica state were captured. A temporary
  second GKE node could not be added because the project CPU quota was short by
  5 vCPU, so scale-out beyond the available node capacity is recorded as a
  capacity limitation rather than claimed as evidence.

## Risk Assessment

- **Scope concentration: 24 points, and it grew to 2 days** because the Feast
  online store must be built in-cluster first. A slip cascades into phases 4-6.
  **Cut ladder entry 4 applies here:** if day 1 of this phase ends without the
  feature chain working, drop the drift API's agent + autoscale + registry rows
  (5 points), keep its API and MCP tool, and move on.
- **Capacity.** One `e2-standard-8` already carrying the platform plus the model
  server may not schedule two APIs, two MCP servers and three multi-replica
  agents. Mitigation: the phase-1 budget governs; run agent captures in a window
  with the observability stack scaled down if needed, and state that.
- **KEDA may not be installed.** Mitigation: check first; HPA is the documented
  fallback and satisfies the row text.
- **Sandbox egress rules can break the agent's own MCP calls.** Mitigation:
  build the allow-list to the MCP gateway and model service before enforcing
  default-deny, and test the positive path alongside the negatives.
- **Four rows resolve to one registry manifest.** A single mistake there costs 8
  points. Mitigation: author it early in the phase, not on the last afternoon.
