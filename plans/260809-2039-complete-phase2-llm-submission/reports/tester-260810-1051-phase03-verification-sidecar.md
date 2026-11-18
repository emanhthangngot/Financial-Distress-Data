# Test Report — 2026-08-10 — platform .hase 03 Verification Sidecar

---
phase: 3
scope: FastAPI services, MCP wrappers, specialist agents, coordinator
status: done-with-concerns
environment: .venv-phase2 / Python 3.11.15 / pytest 9.1.1
---

## Summary

- Focused source suite: 11 passed, 0 failed, 0 skipped in 1.61s.
- Focused source line coverage: 76% (692 statements, 166 missed), below the testing skill's 80% guideline.
- Generated Phase 03 requirement suite: 0 passed, 0 failed, 15 skipped in 0.13s.
- All generated cases skipped because their `docs/platform/evidence/llm/*.md` execution evidence does not yet exist; therefore these tests did not reach artifact existence or behavioral-contract checks.
- No live services, Docker, Kubernetes, GitOps, or cluster mutation used.
- No source/config/test files changed. Only this requested report created. Existing user untracked docs preserved.

## Commands and Results

### Discovery and pre-flight

```bash
git status --short
find apps/drift-mcp apps/feature-mcp src/agents tests/phase2 -type f -print | sort
find tests/platform/requirements -maxdepth 1 -type f -name 'test_llm_ac_*.py' -print | sort
```

Result: Phase 03 source and focused tests present. Worktree already dirty: `src/llm/contracts.py` modified; Phase 03 app/agent/test trees and unrelated onboarding docs untracked. No mutation performed.

`rg` was unavailable (`zsh: command not found: rg`); discovery continued with `find` and `grep`.

### Focused source tests with coverage

```bash
PYTHONDONTWRITEBYTECODE=1 COVERAGE_FILE=/tmp/phase03-sidecar.coverage \
  .venv-phase2/bin/python -m pytest -p no:cacheprovider \
  tests/platform/apps tests/platform/agents \
  --cov=src/agents \
  --cov=apps/feature-mcp/app \
  --cov=apps/drift-mcp/app \
  --cov-report=term-missing
```

Result: exit 0; 11 collected; 11 passed; 0 failed; 0 skipped; 1.61s test time, 2.33s command wall time.

| Module | Statements | Missed | Line coverage |
|---|---:|---:|---:|
| `apps/drift-mcp/app/main.py` | 132 | 15 | 89% |
| `apps/drift-mcp/app/mcp_server.py` | 95 | 31 | 67% |
| `apps/feature-mcp/app/main.py` | 213 | 54 | 75% |
| `apps/feature-mcp/app/mcp_server.py` | 106 | 31 | 71% |
| `src/agents/coordinator.py` | 50 | 2 | 96% |
| `src/agents/drift_agent.py` | 29 | 29 | 0% |
| `src/agents/feature_agent.py` | 52 | 4 | 92% |
| `src/agents/models.py` | 15 | 0 | 100% |
| **Total** | **692** | **166** | **76%** |

### Narrow generated Phase 03 requirement tests

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-phase2/bin/python -m pytest \
  -p no:cacheprovider -ra \
  tests/platform/requirements/test_llm_ac_03_registry.py \
  tests/platform/requirements/test_llm_ac_05_feature_rag_api.py \
  tests/platform/requirements/test_llm_ac_06_drift_mcp.py \
  tests/platform/requirements/test_llm_ac_08_coordinator.py
```

Result: exit 0; 15 collected; 15 skipped; 0 passed; 0 failed; 0.13s test time, 0.39s command wall time.

Skip distribution:

- AC-03 registry: 1 missing evidence file.
- AC-05 feature/RAG API: 6 missing evidence files.
- AC-06 drift/MCP: 6 missing evidence files.
- AC-08 coordinator: 2 missing evidence files.

Every skip reason was `evidence not yet executed: docs/platform/evidence/llm/<rubric-id>.md`.

## Behavior Coverage Assessment

Covered with executable source tests:

- Feature API health/readiness, request validation, successful feature lookup, fail-closed production config, Feast entity mapping/off-thread call, metrics, MCP mount.
- Drift API health/readiness, validation, deterministic repeated response, domain work off-thread, metrics, MCP mount.
- Feature MCP forbidden, tool-budget exhaustion, timeout, and no-call-on-rejection paths.
- Drift MCP forbidden and no-call-on-rejection path.
- Feature agent poisoned-content delimiting, original-scope preservation, one-call budget, citation creation.
- Coordinator two-specialist fan-out, hop bound, citation aggregation, invalid-citation rejection.

Material gaps:

1. `src/agents/drift_agent.py` is entirely unexecuted (0%). Its request validation, tool call, failure handling, renderer call, and citation URI are unverified.
2. Neither MCP wrapper has broad behavioral coverage. Feature MCP lacks successful invocation, validation-error and HTTP-error tests; drift MCP lacks successful invocation, validation-error, budget, timeout and HTTP-error tests.
3. HTTP transport lifecycle, environment grant parsing, and runtime assembly are mostly uncovered in both MCP wrappers.
4. Feature API's RAG lookup/adapter and several dependency/error branches remain uncovered; module coverage is 75%.
5. Concrete `BoundedMcpToolService` and `BoundedAgentOrchestrationService` implementations in `src/llm/contracts.py` have no behavioral test references. Existing rubric-matrix checks cover abstract signatures only.
6. Generated requirement tests currently provide zero artifact-contract evidence: all 15 skip before checking source/GitOps artifacts.
7. No local test can verify Phase 03 cluster-only criteria: Feast in-cluster reachability/materialization, Helm atomic rollback/rolling update, sandbox negatives, autoscale, or agent registry publication. Those require later controlled evidence execution and were intentionally not attempted here.

## Failures

No executed test failed. Coverage target not met, and all generated requirement checks skipped.

## Recommendations

1. High: add focused `DriftAgent` happy/error/validation tests; current specialist implementation has 0% coverage.
2. High: add successful and structured-error tests for both MCP services, especially drift budget/timeout/API-error behavior.
3. High: execute and record Phase 03 evidence, then rerun the four generated requirement modules so they reach artifact behavioral assertions.
4. Medium: test concrete `src/llm/contracts.py` implementations or remove them from Phase 03 completion claims until behavior is pinned.
5. Medium: add RAG endpoint/adapter and MCP runtime/environment parsing tests to raise critical-path coverage above 80%.

## Unresolved Questions

- When will the separate GitOps checkout and controlled cluster evidence window be available for registry, sandbox, rollout, autoscale, and in-cluster Feast verification?

Status: DONE_WITH_CONCERNS

Summary: Focused source behavior passes 11/11, but aggregate coverage is 76%, `DriftAgent` is 0%, and all 15 generated Phase 03 requirement checks skip on absent execution evidence.

Concerns/Blockers: Missing executed evidence prevents generated artifact-contract validation; cluster-only acceptance criteria remain unverified by constraint.
