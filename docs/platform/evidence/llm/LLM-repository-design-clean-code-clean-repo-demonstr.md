# Evidence — Repository design (clean code, clean repo)

Proves `src/llm/contracts.py` implements the documented service contracts
and design patterns from `docs/platform/low-level-design.md` as real, executable
abstract base classes with concrete implementations, plus the two-repo
separation (source repo for code/CI, private GitOps repo for deployed state).

- rubric_id: LLM-repository-design-clean-code-clean-repo-demonstr
- execution_timestamp: 2026-08-10T13:10:00+07:00
- source_sha: 9ec6f065276d316bad1e308c88028c5662edc4db
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: python 3.11
- command: `pytest tests/platform/verification/test_contract_implementations.py -v`
- expected_result: `src/llm/contracts.py` defines abstract service contracts (`RagIngestionService`, `EmbeddingRegistryService`, `McpToolService`, `AgentOrchestrationService`, `AgentReleaseService`) with concrete, behaviorally-tested implementations (`BoundedMcpToolService`, `BoundedAgentOrchestrationService`, `InMemoryEmbeddingRegistry`), not stubs
- actual_result: 11 classes in `src/llm/contracts.py` (5 abstract contracts, concrete implementations and value objects), with real logic (tool-budget enforcement, hop-bound enforcement, embedding-version tracking); all 9 contract implementation tests pass
- redaction_status: reviewed — source code only, no secrets

## Command output (real run)

```
$ pytest tests/platform/verification/test_contract_implementations.py -q
.........                                                                 [100%]
9 passed in 0.12s

$ grep -c '^class ' src/llm/contracts.py
11
```
