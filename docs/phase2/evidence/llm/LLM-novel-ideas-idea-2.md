# Evidence — citation and PII guard

- rubric_id: LLM-novel-ideas-idea-2
- execution_timestamp: 2026-08-11T08:52:37Z
- source_sha: 1b38709b4ef1b28e7a1bb7f12a49b68cbfe1c049
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: Python 3.11; `CitationGuard`; pytest
- command: `.venv-phase2/bin/python -m pytest -q tests/phase2/verification/test_llm_novel_ideas.py -k citation_guard`
- expected_result: supported citations permit a response, PII is rewritten or blocked, unsupported citations are blocked, resolver failures fail closed, and each decision retains trace and evidence-manifest identifiers
- actual_result: focused guard tests passed; email output was rewritten with category-only findings, unsupported/default citations were blocked, resolver exceptions were blocked, and fail-closed PII mode blocked sensitive output while preserving `trace_id` and `evidence_manifest`
- redaction_status: reviewed — the evidence records categories and synthetic trace identifiers, never matched sensitive values

## Reproducible output

The policy boundary is implemented in `src/llm/citation_guard.py` and the
decision contract is exercised by `tests/phase2/verification/test_llm_novel_ideas.py`.
