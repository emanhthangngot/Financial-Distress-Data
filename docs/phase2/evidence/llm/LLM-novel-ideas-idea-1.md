# Evidence — embedding-version hot swap

- rubric_id: LLM-novel-ideas-idea-1
- execution_timestamp: 2026-08-11T08:52:37Z
- source_sha: 81aa31f087110f19ed7415f3976c6eb3d3563fbb
- gitops_sha: 921bdc1075ef8335e0f509747bd64db2d525f73e
- versions: Python 3.11; `EmbeddingVersionRegistry`; pytest
- command: `.venv-phase2/bin/python -m pytest -q tests/phase2/verification/test_llm_novel_ideas.py -k embedding_registry`
- expected_result: dual-read validation reads previous and candidate namespaces, rejects mixed dimensions, validates query shape, and changes the active alias only after validation
- actual_result: focused registry tests passed; the injected reader was called for both versions, one match was recorded from each read, the candidate became active, and incompatible dimensions/wrong vector length were rejected before query or alias use
- redaction_status: reviewed — test data contains synthetic digests only; no credentials or personal data

## Reproducible output

The proof is implemented in `src/llm/embedding_registry.py` and exercised by
`tests/phase2/verification/test_llm_novel_ideas.py`.
