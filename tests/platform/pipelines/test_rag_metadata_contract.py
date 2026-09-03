"""Pins the nine-field metadata contract (phase-04-implementation-notes.md
section 4.3) against the real registered rag-sources.yaml fixtures: every
chunk RagIngestionPipeline.parse_and_chunk emits carries all required
fields, and assert_metadata_complete accepts it."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.llm.data_governance import assert_metadata_complete
from src.llm.rag.embedding import DeterministicHashEmbedder
from src.llm.rag_pipeline import RagIngestionPipeline, load_sources_config

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCES_CONFIG = REPO_ROOT / "configs" / "rag-sources.yaml"


@pytest.fixture()
def pipeline(fake_store) -> RagIngestionPipeline:
    return RagIngestionPipeline(fake_store, DeterministicHashEmbedder(), SOURCES_CONFIG)


@pytest.mark.parametrize(
    "source", ["vnstock_news_vnm", "vnstock_news_hpg", "annual_report_fpt_2025"]
)
def test_every_emitted_chunk_carries_complete_metadata(
    pipeline: RagIngestionPipeline, source: str
) -> None:
    documents = pipeline.fetch_documents(source, window=None)
    chunks = pipeline.parse_and_chunk(documents)
    assert chunks  # the fixture actually produced at least one chunk
    for chunk in chunks:
        assert_metadata_complete(chunk)
        assert chunk.chunk_text.strip() != ""
        assert chunk.parser_version == "v1"


def test_chunk_indices_are_sequential_per_document(pipeline: RagIngestionPipeline) -> None:
    documents = pipeline.fetch_documents("annual_report_fpt_2025", window=None)
    chunks = pipeline.parse_and_chunk(documents)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_registered_sources_declare_all_required_fields() -> None:
    sources = load_sources_config(SOURCES_CONFIG)
    assert len(sources) == 3
    for name, entry in sources.items():
        for key in ("source_uri", "source_name", "content_type", "license", "access_class"):
            assert entry.get(key), f"{name} missing {key!r}"
        fixture_path = REPO_ROOT / entry["source_uri"]
        assert fixture_path.is_file(), f"{name}: fixture not found at {fixture_path}"
