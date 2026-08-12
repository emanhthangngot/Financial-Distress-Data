# Evidence — embedding-version hot swap

- rubric_id: LLM-novel-ideas-idea-1
- execution_timestamp: 2026-08-11T08:52:37Z
- source_sha: 3c99fb7fcdbae3e94840ebb1ed1b69b690da7785
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: Python 3.11; `EmbeddingVersionRegistry`; pytest
- command: `.venv-phase2/bin/python -m pytest -q tests/phase2/verification/test_llm_novel_ideas.py -k embedding_registry`
- expected_result: dual-read validation reads previous and candidate namespaces, rejects mixed dimensions, validates query shape, and changes the active alias only after validation
- actual_result: focused registry tests passed; the injected reader was called for both versions, one match was recorded from each read, the candidate became active, and incompatible dimensions/wrong vector length were rejected before query or alias use
- redaction_status: reviewed — test data contains synthetic digests only; no credentials or personal data

## Reproducible output

The proof is implemented in `src/llm/embedding_registry.py` and exercised by
`tests/phase2/verification/test_llm_novel_ideas.py`.
