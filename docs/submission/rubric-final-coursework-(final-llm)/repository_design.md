---
title: "Repository Design"
date: 2026-08-14
status: active
---

# Repository Design: executable service contracts, not just documented ones

This doc proves the single row in "Repository Design": the service contracts
described in the low-level design document are real, executable abstract
base classes with concrete, behaviorally-tested implementations — not
markdown-only documentation — plus a clean two-repository separation between
source/CI and deployed state. It does not prove a formal design-pattern
audit across the whole codebase — `src/llm/contracts.py` is the concrete
proof point this row claims.

**Active deployment facts:** Python 3.11, `src/llm/contracts.py` (11
classes: 5 abstract contracts + concrete implementations + value objects).

## Part I — Contracts as real code

### 1. Five abstract service contracts, concretely implemented

```text
$ grep -n "^class " src/llm/contracts.py
class RagIngestionService(ABC):
class EmbeddingRegistryService(ABC):
class McpToolService(ABC):
class AgentOrchestrationService(ABC):
class AgentReleaseService(ABC):
class ToolInvocationResult:
class BoundedMcpToolService(McpToolService):
class BoundedAgentOrchestrationService(AgentOrchestrationService):
class EmbeddingVersion:
class InMemoryEmbeddingRegistry(EmbeddingRegistryService):
class InMemoryAgentReleaseService(AgentReleaseService):
```

`BoundedMcpToolService` and `BoundedAgentOrchestrationService` implement
real logic — tool-budget enforcement and hop-bound enforcement respectively
— the same bound (`max_hops=2`) proven live in `coordinator_agent.md`.

```text
$ pytest tests/platform/verification/test_contract_implementations.py -q
.........                                                                 [100%]
9 passed in 0.12s
```

Full evidence:
[`LLM-repository-design-clean-code-clean-repo-demonstr.md`](../../platform/evidence/llm/LLM-repository-design-clean-code-clean-repo-demonstr.md).

## Part II — Two-repository separation

`Financial-Distress-Data` (this repo) owns code, contracts, tests, product
migrations, and canonical coursework evidence. `financial-distress-gitops`
(private, separate) owns Terraform, Helm values, Argo applications, and
desired cluster state — see `docs/system-architecture.md` §"Repository
ownership" for the full boundary table. Application logic never lives in the
GitOps repo; deployed state never lives in this one.

## Limitations

This row's proof is scoped to `src/llm/contracts.py` — a representative,
audited example of contract-as-code discipline, not a claim that every
module in the repository follows an identical abstract-base-class pattern.

## References

- Python `abc` module: https://docs.python.org/3/library/abc.html
