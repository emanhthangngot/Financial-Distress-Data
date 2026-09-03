"""psycopg-backed repository for the ``ml_metadata`` RAG tables
(sql/init_ml_metadata.sql): rag_document, rag_chunk, rag_quarantine,
rag_ingestion_run.

The connection is injected, not constructed here, so this module never
imports ``psycopg`` itself — the two-venv lazy-import rule (D4,
phase-04-implementation-notes.md section 0) is satisfied by construction:
whatever creates the connection (a DAG task, a test fixture) is where the
lazy ``import psycopg`` belongs.

**Caller obligation**: the injected connection must have
``pgvector.psycopg.register_vector(conn)`` called on it before it reaches
``PgVectorStore`` (also lazy, same two-venv rule). Without it, psycopg3
adapts a plain ``list[float]`` to a Postgres ``float8[]``, and there is no
implicit ``float8[] -> vector`` cast — ``insert_chunks`` would fail against a
real ``vector(384)`` column. This module cannot register it itself without
importing psycopg at call time for a side effect unrelated to any query it
runs, so the obligation is documented here instead. ``src.llm.rag_pipeline.
run_ingestion_task`` is the one production caller and does call it before
constructing ``PgVectorStore``, verified against a real
``pgvector/pgvector:pg16`` container (fresh insert + idempotent rerun).
``tests/platform/pipelines/test_pgvector_store.py`` still skips whenever the
pgvector extension itself is unavailable in the test environment.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.llm.rag_pipeline import Chunk, RawDocument


def _chunk_id(content_hash: str, embedding_version: str) -> str:
    return hashlib.sha256(f"{content_hash}|{embedding_version}".encode()).hexdigest()[:32]


class PgVectorStore:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    def document_exists(self, document_hash: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM ml_metadata.rag_document WHERE document_hash = %s",
                (document_hash,),
            )
            return cur.fetchone() is not None

    def upsert_document(self, document: RawDocument, document_hash: str, now: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ml_metadata.rag_document
                    (document_hash, source_uri, source_name, company, report_date,
                     license, access_class, fetched_ts, first_ingested_ts)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (document_hash) DO NOTHING
                """,
                (
                    document_hash,
                    document.source_uri,
                    document.source_name,
                    document.company,
                    document.report_date,
                    document.license,
                    document.access_class,
                    document.fetched_ts,
                    now,
                ),
            )
        self.conn.commit()

    def content_hash_exists(self, content_hash: str, embedding_version: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM ml_metadata.rag_chunk WHERE content_hash = %s "
                "AND embedding_version = %s",
                (content_hash, embedding_version),
            )
            return cur.fetchone() is not None

    def insert_chunks(
        self,
        chunks_with_vectors: list[tuple[Chunk, list[float]]],
        embedding_model: str,
        embedding_version: str,
        ingestion_version: str,
    ) -> int:
        """``ON CONFLICT (content_hash, embedding_version) DO NOTHING`` — a
        rerun of unchanged content inserts zero new rows (criterion 1,
        phase-04-implementation-notes.md section 15). Returns the count of
        rows actually inserted (excludes conflicts)."""
        inserted = 0
        with self.conn.cursor() as cur:
            for chunk, vector in chunks_with_vectors:
                cur.execute(
                    """
                    INSERT INTO ml_metadata.rag_chunk
                        (chunk_id, document_hash, content_hash, chunk_index, chunk_text,
                         source_uri, company, report_date, parser_version, embedding_model,
                         embedding_version, embedding, access_class, ingestion_version)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (content_hash, embedding_version) DO NOTHING
                    """,
                    (
                        _chunk_id(chunk.content_hash, embedding_version),
                        chunk.document_hash,
                        chunk.content_hash,
                        chunk.chunk_index,
                        chunk.chunk_text,
                        chunk.source_uri,
                        chunk.company,
                        chunk.report_date,
                        chunk.parser_version,
                        embedding_model,
                        embedding_version,
                        vector,
                        chunk.access_class,
                        ingestion_version,
                    ),
                )
                inserted += cur.rowcount
        self.conn.commit()
        return inserted

    def insert_quarantine(self, chunk: Chunk, reason: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ml_metadata.rag_quarantine
                    (chunk_id, document_hash, content_hash, source_uri, company, report_date,
                     access_class, violation_reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (chunk_id) DO NOTHING
                """,
                (
                    _chunk_id(chunk.content_hash, "quarantine"),
                    chunk.document_hash,
                    chunk.content_hash,
                    chunk.source_uri,
                    chunk.company,
                    chunk.report_date,
                    chunk.access_class,
                    reason,
                ),
            )
        self.conn.commit()

    def record_ingestion_run(
        self,
        ingestion_version: str,
        run_id: str,
        started_ts: str,
        finished_ts: str,
        documents_fetched: int,
        chunks_new: int,
        chunks_reused: int,
        chunks_quarantined: int,
        source_sha: str,
    ) -> None:
        """Not yet called by ``RagIngestionPipeline`` — ``run_id``/
        ``source_sha`` are DAG-run identity, not pipeline state, so this is
        deferred to whichever slice wires the DAG orchestrator (4C) or the
        evidence run (4D) rather than invented here. The method and the
        ``ml_metadata.rag_ingestion_run`` table exist now so that caller has
        nothing left to design."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ml_metadata.rag_ingestion_run
                    (ingestion_version, run_id, started_ts, finished_ts, documents_fetched,
                     chunks_new, chunks_reused, chunks_quarantined, source_sha)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ingestion_version) DO NOTHING
                """,
                (
                    ingestion_version,
                    run_id,
                    started_ts,
                    finished_ts,
                    documents_fetched,
                    chunks_new,
                    chunks_reused,
                    chunks_quarantined,
                    source_sha,
                ),
            )
        self.conn.commit()
