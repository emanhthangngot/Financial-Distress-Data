"""Shared in-memory PgVectorStore fake for RAG pipeline tests that don't
need a real Postgres (those live in test_pgvector_store.py instead)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest


@dataclass
class FakeStore:
    """Mirrors PgVectorStore's public surface with plain dicts/lists — no
    psycopg, no network, deterministic across runs."""

    documents: dict[str, Any] = field(default_factory=dict)
    chunks: dict[tuple[str, str], Any] = field(default_factory=dict)
    quarantined: list[tuple[Any, str]] = field(default_factory=list)
    ingestion_runs: list[dict[str, Any]] = field(default_factory=list)

    def document_exists(self, document_hash: str) -> bool:
        return document_hash in self.documents

    def upsert_document(self, document: Any, document_hash: str, now: str) -> None:
        self.documents.setdefault(document_hash, document)

    def content_hash_exists(self, content_hash: str, embedding_version: str) -> bool:
        return (content_hash, embedding_version) in self.chunks

    def insert_chunks(
        self,
        chunks_with_vectors: list[tuple[Any, list[float]]],
        embedding_model: str,
        embedding_version: str,
        ingestion_version: str,
    ) -> int:
        inserted = 0
        for chunk, vector in chunks_with_vectors:
            key = (chunk.content_hash, embedding_version)
            if key in self.chunks:
                continue
            self.chunks[key] = {
                "chunk": chunk,
                "vector": vector,
                "embedding_model": embedding_model,
                "ingestion_version": ingestion_version,
            }
            inserted += 1
        return inserted

    def insert_quarantine(self, chunk: Any, reason: str) -> None:
        self.quarantined.append((chunk, reason))

    def record_ingestion_run(self, **kwargs: Any) -> None:
        self.ingestion_runs.append(kwargs)


@pytest.fixture()
def fake_store() -> FakeStore:
    return FakeStore()
