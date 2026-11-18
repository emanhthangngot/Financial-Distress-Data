-- ml schema. Runs against platform-postgres (pgvector/pgvector:pg16), a
-- separate Postgres instance from ops. The cross-write ban between ops and ml
-- was revoked by the unified rebuild plan (AGENTS.md), but the two remain
-- physically separate Postgres instances until a later phase merges them.

CREATE SCHEMA IF NOT EXISTS ml;
CREATE EXTENSION IF NOT EXISTS vector;

-- Distress label table (src/ml/label_pipeline.py). Renamed from ml.label_table:
-- "table" inside a table name (F9, mini row 43). Not a Feast FeatureView by
-- design — see phase-04-implementation-notes.md section 5.
CREATE TABLE IF NOT EXISTS ml.distress_label (
    ticker TEXT NOT NULL,
    event_timestamp TIMESTAMPTZ NOT NULL,
    label INTEGER,
    label_version TEXT NOT NULL,
    created_ts TIMESTAMPTZ NOT NULL,
    training_eligible BOOLEAN NOT NULL DEFAULT FALSE,
    label_source TEXT NOT NULL,
    PRIMARY KEY (ticker, event_timestamp, label_version)
);

-- Feast registry revision (src/ml/feast/materialization.py, phase-04C).
CREATE TABLE IF NOT EXISTS ml.feast_registry_revision (
    revision_id TEXT PRIMARY KEY,
    project TEXT NOT NULL,
    applied_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    registry_digest TEXT NOT NULL,
    feature_view_count INTEGER NOT NULL
);

-- Stream feature job checkpoints (src/ml/feast/offline_job.py, online_job.py, phase-04C).
CREATE TABLE IF NOT EXISTS ml.stream_feature_checkpoint (
    job_name TEXT PRIMARY KEY,
    last_offset BIGINT,
    last_event_ts TIMESTAMPTZ,
    updated_ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RAG document registry (src/llm/rag_pipeline.py, phase-04B).
CREATE TABLE IF NOT EXISTS ml.rag_document (
    document_hash TEXT PRIMARY KEY,
    source_uri TEXT NOT NULL,
    source_name TEXT NOT NULL,
    company TEXT,
    report_date DATE,
    license TEXT NOT NULL,
    access_class TEXT NOT NULL,
    fetched_ts TIMESTAMPTZ NOT NULL,
    first_ingested_ts TIMESTAMPTZ NOT NULL
);

-- RAG chunk vectors, 384-dim (matches every EmbeddingBackend implementation,
-- src/llm/rag/embedding.py). One row per (content_hash, embedding_version).
CREATE TABLE IF NOT EXISTS ml.rag_chunk (
    chunk_id TEXT PRIMARY KEY,
    document_hash TEXT NOT NULL REFERENCES ml.rag_document (document_hash),
    content_hash TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    company TEXT,
    report_date DATE,
    parser_version TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_version TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    access_class TEXT NOT NULL,
    created_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    ingestion_version TEXT NOT NULL,
    UNIQUE (content_hash, embedding_version)
);
CREATE INDEX IF NOT EXISTS rag_chunk_embedding_hnsw
    ON ml.rag_chunk USING hnsw (embedding vector_cosine_ops);

-- Governance quarantine (src/llm/data_governance.py, phase-04B).
CREATE TABLE IF NOT EXISTS ml.rag_quarantine (
    chunk_id TEXT PRIMARY KEY,
    document_hash TEXT,
    content_hash TEXT,
    source_uri TEXT NOT NULL,
    company TEXT,
    report_date DATE,
    access_class TEXT,
    violation_reason TEXT NOT NULL,
    quarantined_ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Per-run ingestion evidence (src/llm/rag_pipeline.py, phase-04B).
CREATE TABLE IF NOT EXISTS ml.rag_ingestion_run (
    ingestion_version TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    started_ts TIMESTAMPTZ NOT NULL,
    finished_ts TIMESTAMPTZ,
    documents_fetched INTEGER NOT NULL DEFAULT 0,
    chunks_new INTEGER NOT NULL DEFAULT 0,
    chunks_reused INTEGER NOT NULL DEFAULT 0,
    chunks_quarantined INTEGER NOT NULL DEFAULT 0,
    source_sha TEXT NOT NULL
);

-- NOTE: ml.data_quality_result was merged into ops.data_quality_result (F4) —
-- one table project-wide, PK check_id, disambiguated by the `track` column.
-- See sql/init_ops.sql and sql/migrations/002_data_model_v2.sql.
