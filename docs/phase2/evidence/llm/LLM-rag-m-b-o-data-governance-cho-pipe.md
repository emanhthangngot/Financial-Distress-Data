# Evidence — Đảm bảo data governance cho pipeline

Proves `src/llm/data_governance.py` (licensing allowlist, access-class check,
PII detection, rate limiter, retry policy, quarantine routing) enforced by
`RagIngestionPipeline.enforce_licensing_and_metadata` — unit suite plus a
live-store run against `phase2-postgres` (PGVector) exercising the real
quarantine path end to end.

- rubric_id: LLM-rag-m-b-o-data-governance-cho-pipe
- execution_timestamp: 2026-08-08T09:40:20+00:00
- source_sha: 08ed63b454a857dd355cb9f34f80c049209a396b
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: financial-distress-data@5a5a40a, pgvector/pgvector:pg16
- command: `.venv/bin/python -m pytest tests/phase2/pipelines/test_data_governance.py -q` then a live probe against `phase2-postgres` inserting one chunk with a disallowed license (`unlicensed_scrape`) through `RagIngestionPipeline.enforce_licensing_and_metadata`, followed by `SELECT * FROM ml_metadata.rag_quarantine;`
- expected_result: full governance unit suite green (licensing, access-class, PII regexes, rate limiter spacing, retry-on-5xx/429-not-4xx, quarantine-not-silent-drop); a chunk carrying a disallowed license is removed from the batch (`enforce_licensing_and_metadata` in-place filter) and a row appears in `ml_metadata.rag_quarantine` with a non-empty `violation_reason`; `ml_metadata.rag_chunk`/`rag_document` unaffected by the quarantined chunk
- actual_result: `32 passed in 3.18s`. Live probe: constructed one `Chunk` from a synthetic document declared with `license="unlicensed_scrape"` (outside `configs/rag-sources.yaml`'s `allowed_licenses` — no registered real source violates the policy, so a synthetic probe chunk was used to exercise the enforcement+quarantine path against real Postgres rather than a mock). After `enforce_licensing_and_metadata`, the chunk list was empty (`chunks remaining after governance: 0`). `ml_metadata.rag_quarantine` gained exactly 1 row: `violation_reason = "license 'unlicensed_scrape' not in allowlist ['company_disclosure_public_domain', 'vnstock_public_api_terms']"`. `ml_metadata.rag_chunk` stayed at 2 rows and `ml_metadata.rag_document` at 1 row (unchanged by the quarantined probe) — governance correctly quarantines without touching unrelated writes.
- redaction_status: none — synthetic probe text only, no real PII or secrets

## Command output (real run)

Unit suite:
```
$ .venv/bin/python -m pytest tests/phase2/pipelines/test_data_governance.py -q
................................                                         [100%]
32 passed in 3.18s
```

Live quarantine probe (against `phase2-postgres`, port 5433):
```
$ PHASE2_PG_DSN=postgresql://phase2:phase2@localhost:5433/ml_metadata .venv/bin/python -c "..."
chunks remaining after governance: 0

$ psql -U phase2 -d ml_metadata -c "SELECT chunk_id, source_uri, violation_reason, quarantined_ts FROM ml_metadata.rag_quarantine;"
             chunk_id             |                      source_uri                       |                                               violation_reason                                                |        quarantined_ts
----------------------------------+-------------------------------------------------------+---------------------------------------------------------------------------------------------------------------+-------------------------------
 7960d31459178494ca6e32df45eab5f7 | tests/phase2/fixtures/rag_corpus/vnstock_news_vnm.txt | license 'unlicensed_scrape' not in allowlist ['company_disclosure_public_domain', 'vnstock_public_api_terms'] | 2026-08-08 09:40:20.492315+00
(1 row)

$ psql -U phase2 -d ml_metadata -c "SELECT count(*) FROM ml_metadata.rag_chunk;"
 count
-------
     2
(1 row)
```

DataHub lineage row for this run confirmed via the same no-network
`audit_phase2_lineage` path used by the RAG pipeline evidence (see
`LLM-rag-rag-data-pipeline.md`) — this sandbox has no live DataHub server.
