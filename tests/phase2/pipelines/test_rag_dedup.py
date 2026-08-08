"""Pins the deduplication contract end-to-end through RagIngestionPipeline
(configs/rag-sources.yaml -> fetch -> chunk -> dedupe -> govern -> write):
reprocessing an unchanged document under the same embedding_version yields
zero new chunks; a changed embedding_version yields a full new set."""

from __future__ import annotations

from pathlib import Path

from src.llm.rag.embedding import DeterministicHashEmbedder
from src.llm.rag_pipeline import RagIngestionPipeline

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCES_CONFIG = REPO_ROOT / "configs" / "rag-sources.yaml"


def _run_full_ingest(pipeline: RagIngestionPipeline, source: str, embedding_version: str) -> str:
    documents = pipeline.fetch_documents(source, window=None)
    chunks = pipeline.parse_and_chunk(documents)
    chunks = pipeline.deduplicate_chunks(chunks)
    pipeline.enforce_licensing_and_metadata(chunks)
    return pipeline.write_vectors(chunks, embedding_version)


def test_reprocessing_unchanged_document_yields_zero_new_chunks(fake_store) -> None:
    embedder = DeterministicHashEmbedder()
    pipeline = RagIngestionPipeline(fake_store, embedder, SOURCES_CONFIG)

    first_version = _run_full_ingest(pipeline, "vnstock_news_vnm", embedder.version)
    assert first_version  # non-empty: something was written
    chunk_count_after_first = len(fake_store.chunks)
    assert chunk_count_after_first > 0

    second_version = _run_full_ingest(pipeline, "vnstock_news_vnm", embedder.version)
    assert second_version == ""  # nothing new written
    assert len(fake_store.chunks) == chunk_count_after_first  # criterion 1


def test_new_embedding_version_produces_a_full_new_set(fake_store) -> None:
    embedder_v1 = DeterministicHashEmbedder()
    pipeline_v1 = RagIngestionPipeline(fake_store, embedder_v1, SOURCES_CONFIG)
    _run_full_ingest(pipeline_v1, "vnstock_news_hpg", embedder_v1.version)
    count_after_v1 = len(fake_store.chunks)
    assert count_after_v1 > 0

    class DeterministicHashEmbedderV2(DeterministicHashEmbedder):
        version = "deterministic-hash-v2"

    embedder_v2 = DeterministicHashEmbedderV2()
    pipeline_v2 = RagIngestionPipeline(fake_store, embedder_v2, SOURCES_CONFIG)
    version_written = _run_full_ingest(pipeline_v2, "vnstock_news_hpg", embedder_v2.version)

    assert version_written  # a full new set was written under v2
    assert len(fake_store.chunks) == count_after_v1 * 2
    for _content_hash, embedding_version in fake_store.chunks:
        assert embedding_version in {embedder_v1.version, embedder_v2.version}


def test_deduplicate_chunks_drops_only_already_embedded_chunks(fake_store) -> None:
    embedder = DeterministicHashEmbedder()
    pipeline = RagIngestionPipeline(fake_store, embedder, SOURCES_CONFIG)
    _run_full_ingest(pipeline, "annual_report_fpt_2025", embedder.version)

    documents = pipeline.fetch_documents("annual_report_fpt_2025", window=None)
    chunks = pipeline.parse_and_chunk(documents)
    deduped = pipeline.deduplicate_chunks(chunks)
    assert deduped == []  # every one of them already has an embedded row


def test_deduplicate_chunks_keeps_genuinely_new_chunks(fake_store) -> None:
    embedder = DeterministicHashEmbedder()
    pipeline = RagIngestionPipeline(fake_store, embedder, SOURCES_CONFIG)
    documents = pipeline.fetch_documents("vnstock_news_vnm", window=None)
    chunks = pipeline.parse_and_chunk(documents)
    deduped = pipeline.deduplicate_chunks(chunks)
    assert deduped == chunks  # nothing in the store yet: all kept
