# Evidence — RAG Data Pipeline

Proves `src/llm/rag_pipeline.py`'s `RagIngestionPipeline` (wrapped by
`dags/phase2/phase2_rag_ingest.py`'s `run_ingestion_task`): fetch -> chunk ->
dedupe -> govern -> embed -> write, run twice against a live PGVector store
(`phase2-postgres`, `docker compose --profile phase2 up phase2-postgres`),
proving reprocessing an unchanged document writes zero new rows.

- rubric_id: LLM-rag-rag-data-pipeline
- execution_timestamp: 2026-08-08T09:38:46+00:00
- source_sha: 52dc00c17e69cdc46403f377ae83f00a5406fac5
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: financial-distress-data@5a5a40a, pgvector/pgvector:pg16, embedding_model=deterministic-hash-v1
- command: `PHASE2_PG_DSN=postgresql://phase2:phase2@localhost:5433/ml_metadata .venv/bin/python -c "from src.llm.rag_pipeline import run_ingestion_task; print(run_ingestion_task())"` (run twice)
- expected_result: run 1 writes new chunks with all 9 metadata fields populated; run 2 on the same source writes 0 new rows (`chunks_new == 0`, `ingestion_version == ""`); `ml_metadata.rag_chunk` row count unchanged between runs; lineage audit `status == "pass"`
- actual_result: run 1 → `{"documents_fetched": 1, "chunks_new": 2, "chunks_quarantined": 0, "ingestion_version": "2026-08-08-c53e23b28d00"}`, lineage_audit status=pass (4 datasets, 1 pipeline, 4 edges). Run 2 (same source, same process) → `{"documents_fetched": 1, "chunks_new": 0, "chunks_quarantined": 0, "ingestion_version": ""}`. `SELECT count(*) FROM ml_metadata.rag_chunk` = 2 after both runs — no duplicate rows written on rerun.
- redaction_status: none — synthetic/fixture RAG corpus (`tests/phase2/fixtures/rag_corpus/vnstock_news_vnm.txt`), no real PII or secrets

## Command output (real run)

Run 1:
```json
{
  "source": "vnstock_news_vnm",
  "documents_fetched": 1,
  "chunks_new": 2,
  "chunks_quarantined": 0,
  "ingestion_version": "2026-08-08-c53e23b28d00",
  "lineage_audit": {
    "schema_version": 1,
    "status": "pass",
    "datahub_version": "1.6.0",
    "dataset_count": 4,
    "pipeline_count": 1,
    "lineage_edges": 4,
    "contracts": {
      "phase2_rag_ingest": {
        "dataset": "ml_metadata.rag_chunk",
        "schema_assertion": true,
        "volume_assertion": true
      }
    }
  }
}
```

Run 2 (idempotency check, same process/source):
```json
{
  "source": "vnstock_news_vnm",
  "documents_fetched": 1,
  "chunks_new": 0,
  "chunks_quarantined": 0,
  "ingestion_version": "",
  "lineage_audit": {"schema_version": 1, "status": "pass", "datahub_version": "1.6.0", "dataset_count": 4, "pipeline_count": 1, "lineage_edges": 4}
}
```

`SELECT count(*) FROM ml_metadata.rag_chunk;` → `2` (both before and after run 2).

`SELECT chunk_id, document_hash, content_hash, chunk_index, source_uri, company,
parser_version, embedding_model, embedding_version, access_class, created_ts,
ingestion_version FROM ml_metadata.rag_chunk;` shows all 9 governance metadata
fields populated for both rows (source URI, company, document/content hashes,
parser version, embedding model + version, created_ts, access_class).

DataHub lineage: emitted through `src.governance.phase2_lineage.audit_phase2_lineage`
(no-network local audit — this sandbox has no live DataHub server; the emit
path itself, `src.governance.datahub_emitter.emit_governance`, is exercised by
`tests/phase2/pipelines/test_lineage_emitter.py` against a fake client).
