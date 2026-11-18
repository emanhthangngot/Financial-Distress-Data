# RAG pipeline CI fix report

## Scope

- Active phase: Phase 2, RAG pipeline CI.
- Root cause: Ruff `0.8.*` reports `UP038` for the tuple-style `isinstance(values, (str, bytes))` check in `src/llm/embedding_registry.py`.
- Fix: use the Python 3.11 union form, `isinstance(values, str | bytes)`.
- Runtime behavior: unchanged; the check still rejects string and byte-string results while accepting other sequences.

## Acceptance criteria

- platform .AG CI lint -> checks the configured `src/llm` and RAG/governance test paths with Ruff `0.8.*` -> all checks pass.
- platform .AG CI formatting -> checks the same paths with Black `24.*` -> all 15 files remain unchanged.
- RAG pipeline tests -> runs `tests/platform/pipelines -k 'rag or governance' -m 'not slow'` in the platform .nvironment -> 59 tests pass and 123 are deselected.
- RAG pipeline image build -> builds `infra/phase2/rag-pipeline/Dockerfile` -> Docker build completes successfully.
- Phase 5 web gate -> runs the configured test and coverage gate -> 28 tests pass with 96.72% line and 95.65% branch coverage.
- Phase 5 mutation gate -> runs the RAG chunking mutation scope -> 72 mutants are evaluated, score 86.11%, above the 80% threshold.

## Verification evidence

```text
uvx --from 'ruff==0.8.6' ruff check <RAG lint paths>
All checks passed!

uvx --from 'black==24.10.0' black --check <RAG lint paths>
All done! 15 files would be left unchanged.

.venv-phase2/bin/python -m pytest tests/platform/pipelines -k 'rag or governance' -m 'not slow' -q
59 passed, 123 deselected

docker build -f infra/phase2/rag-pipeline/Dockerfile .
DONE
```

The independent code review found no regression or blocker. The independent tester reproduced the exact Ruff, Black, and pytest selectors successfully. Generated coverage files created by the Phase 5 gate were restored and are not part of this fix.

## Remaining question

The local fix is verified but is not committed or pushed yet. A remote CI rerun requires committing this one-line change and pushing it to `dev`.
