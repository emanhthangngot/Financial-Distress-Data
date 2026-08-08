"""RagIngestionService implementation (contract: src.llm.contracts,
signatures locked — do not change).

fetch_documents reads a committed fixture file registered in
``configs/rag-sources.yaml`` rather than a live HTTP endpoint — confirmed
2026-08-08 (Open Question Q4, phase-04-implementation-notes.md section 4):
deterministic, network-free evidence runs, no scraping/HTML/PDF-parsing
code. All three registered sources are ``text/plain`` extracts; a non-text
content type raises ``NotImplementedError`` rather than being silently
mis-parsed.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from src.llm.contracts import RagIngestionService
from src.llm.data_governance import enforce_chunk_governance
from src.llm.rag.chunking import (
    PARSER_VERSION,
    chunk_text,
    compute_content_hash,
    compute_document_hash,
    normalize_text,
)
from src.llm.rag.embedding import EmbeddingBackend
from src.llm.rag.pgvector_store import PgVectorStore

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCES_CONFIG = REPO_ROOT / "configs" / "rag-sources.yaml"


@dataclass(frozen=True)
class RawDocument:
    source_uri: str
    source_name: str
    company: str | None
    report_date: str | None
    raw_bytes: bytes
    content_type: str
    license: str
    access_class: str
    fetched_ts: str


@dataclass(frozen=True)
class Chunk:
    """The nine documented metadata fields (phase-04-implementation-notes.md
    section 4.3) minus the four added only at write time (embedding_model,
    embedding_version, embedding, ingestion_version): document_hash,
    content_hash, chunk_index, chunk_text, source_uri, company, report_date,
    parser_version, access_class."""

    document_hash: str
    content_hash: str
    chunk_index: int
    chunk_text: str
    source_uri: str
    company: str | None
    report_date: str | None
    parser_version: str
    access_class: str


def load_sources_config(path: Path = DEFAULT_SOURCES_CONFIG) -> dict[str, dict[str, Any]]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("rag sources config must be a mapping")
    return raw.get("sources", {})


def load_governance_policy(path: Path = DEFAULT_SOURCES_CONFIG) -> dict[str, set[str]]:
    """The ``governance_policy`` block: an allowlist declared separately from
    each source's own ``license``/``access_class`` so the gate can actually
    fail (see the comment in configs/rag-sources.yaml)."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    policy = raw.get("governance_policy", {}) if isinstance(raw, dict) else {}
    return {
        "allowed_licenses": set(policy.get("allowed_licenses", [])),
        "allowed_access_classes": set(policy.get("allowed_access_classes", [])),
    }


def _ingestion_version(content_hashes: Iterable[str], embedding_version: str) -> str:
    """Stable across reruns of identical input *on the same day* — how
    idempotency is *observed* in the evidence run
    (phase-04-implementation-notes.md section 4.1). Two caveats this string
    does not protect against: it changes across a UTC-midnight boundary even
    for identical input (the date prefix is for human readability, not
    identity), and ``embedding_version`` is included in the digest
    specifically so two runs of the same content under different embedding
    versions never collide on ``rag_ingestion_run``'s primary key."""
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    payload = embedding_version + "|" + "".join(sorted(content_hashes))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"{date_str}-{digest}"


class RagIngestionPipeline(RagIngestionService):
    """One instance is a single synchronous run of all five contract
    methods, in order, against the same in-process object —
    ``enforce_licensing_and_metadata`` and ``write_vectors`` both read
    ``self._document_by_hash``, populated only by ``parse_and_chunk``. A DAG
    that splits these five methods across separate Airflow tasks (as
    phase-04-implementation-notes.md section 7's per-subtask table implies)
    would lose that state across task boundaries. Whichever slice wires
    ``dags/phase2/phase2_rag_ingest.py`` (4C) must call all five methods from
    a single task, or carry ``license`` on ``Chunk`` itself so
    ``enforce_licensing_and_metadata`` doesn't need the lookup."""

    def __init__(
        self,
        store: PgVectorStore,
        embedding_backend: EmbeddingBackend,
        sources_config_path: Path = DEFAULT_SOURCES_CONFIG,
        allowed_licenses: set[str] | None = None,
        allowed_access_classes: set[str] | None = None,
    ) -> None:
        self.store = store
        self.embedding_backend = embedding_backend
        self.sources_config_path = Path(sources_config_path)
        self._sources = load_sources_config(self.sources_config_path)
        policy = load_governance_policy(self.sources_config_path)
        self.allowed_licenses = allowed_licenses or policy["allowed_licenses"]
        self.allowed_access_classes = allowed_access_classes or policy["allowed_access_classes"]
        self._document_by_hash: dict[str, RawDocument] = {}

    def fetch_documents(self, source: str, window: Any = None) -> list[RawDocument]:
        """``window`` is accepted for contract compatibility but unused: a
        committed fixture has no time axis to window over."""
        entry = self._sources.get(source)
        if entry is None:
            raise KeyError(f"unknown rag source {source!r}; known: {sorted(self._sources)}")
        fixture_path = REPO_ROOT / entry["source_uri"]
        document = RawDocument(
            source_uri=entry["source_uri"],
            source_name=entry["source_name"],
            company=entry.get("company"),
            report_date=entry.get("report_date"),
            raw_bytes=fixture_path.read_bytes(),
            content_type=entry["content_type"],
            license=entry["license"],
            access_class=entry["access_class"],
            fetched_ts=datetime.now(UTC).isoformat(),
        )
        return [document]

    def parse_and_chunk(self, documents: list[RawDocument]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for document in documents:
            if document.content_type != "text/plain":
                raise NotImplementedError(
                    f"content_type {document.content_type!r} not supported; only "
                    "text/plain fixtures are registered for this slice"
                )
            document_hash = compute_document_hash(document.raw_bytes)
            self._document_by_hash[document_hash] = document
            text = normalize_text(document.raw_bytes.decode("utf-8"))
            for index, piece in enumerate(chunk_text(text)):
                normalized_piece = normalize_text(piece)
                chunks.append(
                    Chunk(
                        document_hash=document_hash,
                        content_hash=compute_content_hash(normalized_piece, PARSER_VERSION),
                        chunk_index=index,
                        chunk_text=normalized_piece,
                        source_uri=document.source_uri,
                        company=document.company,
                        report_date=document.report_date,
                        parser_version=PARSER_VERSION,
                        access_class=document.access_class,
                    )
                )
        return chunks

    def deduplicate_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Chunk-level: drop chunks whose (content_hash, embedding_version)
        already exists — this alone makes a same-version rerun on unchanged
        input write zero new rows (criterion 1), and correctly still writes
        a full new set when the embedding_version changes.

        Deliberately scoped down from the two-level (document-level
        short-circuit + chunk-level) design in
        phase-04-implementation-notes.md section 4.1: that short-circuit
        existed to skip a redundant *fetch* for a large remote corpus.
        ``fetch_documents`` here reads an instant local fixture file, so the
        short-circuit would save nothing while actively blocking a
        legitimate re-embed-under-a-new-version run (it keys only on
        document_hash, not (document_hash, embedding_version)).
        ``store.document_exists`` is unused by this pipeline as a result —
        ``write_vectors``'s ``upsert_document`` call is itself
        ``ON CONFLICT DO NOTHING``, so re-registering an unchanged document
        is a no-op rather than something that needs checking first.

        ``embedding_version`` isn't a parameter on this contract method, so
        the pipeline's own backend version is the natural default here — the
        caller of ``write_vectors`` may still pass a different version
        string for the actual write."""
        embedding_version = self.embedding_backend.version
        return [
            chunk
            for chunk in chunks
            if not self.store.content_hash_exists(chunk.content_hash, embedding_version)
        ]

    def enforce_licensing_and_metadata(self, chunks: list[Chunk]) -> None:
        """In-place filter (contract return type is ``None``): a metadata
        gap raises directly (programmer error). A license/access-class/PII
        violation quarantines that one chunk and removes it from ``chunks``
        without aborting the rest of the batch — see
        src.llm.data_governance's module docstring for the DQ-severity
        mapping this implements."""
        valid: list[Chunk] = []
        for chunk in chunks:
            document = self._document_by_hash[chunk.document_hash]
            reason = enforce_chunk_governance(
                chunk, document.license, self.allowed_licenses, self.allowed_access_classes
            )
            if reason is None:
                valid.append(chunk)
            else:
                self.store.insert_quarantine(chunk, reason)
        chunks[:] = valid

    def write_vectors(self, chunks: list[Chunk], embedding_version: str) -> str:
        """Embeds and upserts. ``embedding_version`` must equal the
        configured backend's own version — this pipeline embeds with
        ``self.embedding_backend``, so a mismatched caller-supplied version
        would silently mislabel the vectors it just computed. Parent
        documents are registered *before* their chunks: ``rag_chunk.
        document_hash`` is ``NOT NULL REFERENCES rag_document`` (see
        sql/init_ml_metadata.sql), so inserting chunks first would violate
        that foreign key on every write against real Postgres."""
        if not chunks:
            return ""
        if embedding_version != self.embedding_backend.version:
            raise ValueError(
                f"embedding_version {embedding_version!r} does not match the configured "
                f"backend's version {self.embedding_backend.version!r} — "
                "deduplicate_chunks already checked against the backend's version, so "
                "writing under a different one would silently miss rows"
            )
        now = datetime.now(UTC).isoformat()
        for document_hash in {chunk.document_hash for chunk in chunks}:
            self.store.upsert_document(self._document_by_hash[document_hash], document_hash, now)

        vectors = self.embedding_backend.embed([chunk.chunk_text for chunk in chunks])
        ingestion_version = _ingestion_version(
            (chunk.content_hash for chunk in chunks), embedding_version
        )
        inserted = self.store.insert_chunks(
            list(zip(chunks, vectors, strict=True)),
            embedding_model=self.embedding_backend.name,
            embedding_version=embedding_version,
            ingestion_version=ingestion_version,
        )
        return ingestion_version if inserted else ""


def run_ingestion(
    pipeline: RagIngestionPipeline, source: str, window: Any = None
) -> dict[str, Any]:
    """Runs all five contract methods in order against one pipeline instance
    — see ``RagIngestionPipeline``'s class docstring for why they must not
    be split across separate Airflow tasks. This is the single callable
    ``dags/phase2/phase2_rag_ingest.py`` wraps in one ``PythonOperator``.

    Lineage emission (Flow E, phase-04-implementation-notes.md section 2) is
    deliberately not wired here — ``src/governance/phase2_lineage.py`` and
    ``configs/phase2-governance.yaml`` are slice 4D's files, not 4C's."""
    documents = pipeline.fetch_documents(source, window)
    chunks = pipeline.parse_and_chunk(documents)
    chunks = pipeline.deduplicate_chunks(chunks)
    chunks_before_governance = len(chunks)
    pipeline.enforce_licensing_and_metadata(chunks)
    ingestion_version = pipeline.write_vectors(chunks, pipeline.embedding_backend.version)
    return {
        "source": source,
        "documents_fetched": len(documents),
        "chunks_new": len(chunks) if ingestion_version else 0,
        "chunks_quarantined": chunks_before_governance - len(chunks),
        "ingestion_version": ingestion_version,
    }


def run_ingestion_task() -> dict[str, Any]:
    """Airflow entrypoint, no args: reads every setting from environment
    inside this function (never at DAG-module import time —
    dags/phase2/phase2_rag_ingest.py's only job is to point a
    PythonOperator at this callable). ``PHASE2_PG_DSN`` required;
    ``PHASE2_EMBEDDING_ENDPOINT`` unset falls back to the network-free hash
    embedder, matching D5's CI default; ``PHASE2_RAG_SOURCE`` defaults to
    the first registered source."""
    import os
    import uuid

    import psycopg
    from pgvector.psycopg import register_vector

    from src.llm.rag.embedding import DeterministicHashEmbedder, TeiHttpEmbedder
    from src.llm.rag.pgvector_store import PgVectorStore

    source = os.environ.get("PHASE2_RAG_SOURCE", "vnstock_news_vnm")
    embedding_endpoint = os.environ.get("PHASE2_EMBEDDING_ENDPOINT")
    embedder = (
        TeiHttpEmbedder(endpoint=embedding_endpoint)
        if embedding_endpoint
        else DeterministicHashEmbedder()
    )
    with psycopg.connect(os.environ["PHASE2_PG_DSN"]) as conn:
        # PgVectorStore's own docstring documents this obligation: without
        # it, psycopg3 adapts list[float] to float8[] and there is no
        # implicit float8[] -> vector cast for a real vector(384) column.
        register_vector(conn)
        pipeline = RagIngestionPipeline(PgVectorStore(conn), embedder)
        result = run_ingestion(pipeline, source)

    from src.governance.phase2_lineage import (
        audit_phase2_lineage,
        emit_phase2_lineage_if_configured,
    )

    result["lineage_audit"] = audit_phase2_lineage(pipeline_name="phase2_rag_ingest")
    result["lineage_emit"] = emit_phase2_lineage_if_configured(
        run_id=uuid.uuid4().hex, pipeline_name="phase2_rag_ingest"
    )
    return result
