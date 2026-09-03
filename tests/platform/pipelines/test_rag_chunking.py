"""Pins src/llm/rag/chunking.py: chunk size/overlap bounds, sentence-boundary
preference, content_hash stability under whitespace normalization, and
content_hash changing when parser_version changes."""

from __future__ import annotations

from src.llm.rag.chunking import (
    chunk_text,
    compute_content_hash,
    compute_document_hash,
    normalize_text,
)


def test_short_text_is_a_single_chunk() -> None:
    assert chunk_text("short text.", target_chars=800) == ["short text."]


def test_empty_text_yields_no_chunks() -> None:
    assert chunk_text("", target_chars=800) == []


def test_long_text_is_split_into_multiple_chunks() -> None:
    paragraph = "Cau vi du ngan de kiem tra ranh gioi cau. " * 60  # ~2500 chars
    chunks = chunk_text(paragraph, target_chars=800, overlap_chars=120)
    assert len(chunks) > 1
    for chunk in chunks:
        # boundary preference can overshoot target but never by more than
        # the 20% tolerance plus the length of the boundary marker itself
        assert len(chunk) <= 800 + round(800 * 0.2) + 4


def test_chunks_overlap_by_roughly_the_configured_amount() -> None:
    text = "".join(f"Cau so {i}, noi dung tai chinh vi du. " for i in range(80))
    chunks = chunk_text(text, target_chars=400, overlap_chars=80)
    assert len(chunks) > 1
    # consecutive chunks share a non-trivial suffix/prefix (the overlap)
    first_tail = chunks[0][-40:]
    assert first_tail[:20] in chunks[1] or first_tail[-20:] in chunks[1]


def test_prefers_sentence_boundary_over_hard_cut() -> None:
    sentence_a = "A" * 780 + ". "
    sentence_b = "B" * 200
    text = sentence_a + sentence_b
    chunks = chunk_text(text, target_chars=800, overlap_chars=120)
    # the first chunk should end at the sentence boundary (781 chars),
    # not a hard cut at exactly 800 mid-way into sentence_b
    assert chunks[0].endswith(".")


def test_normalize_text_collapses_whitespace_and_strips() -> None:
    assert normalize_text("  hello   world  \n\n  ") == "hello world"


def test_content_hash_stable_under_whitespace_normalization() -> None:
    a = compute_content_hash(normalize_text("hello   world"), "v1")
    b = compute_content_hash(normalize_text("hello world"), "v1")
    assert a == b


def test_content_hash_changes_with_parser_version() -> None:
    text = normalize_text("hello world")
    assert compute_content_hash(text, "v1") != compute_content_hash(text, "v2")


def test_content_hash_changes_with_content() -> None:
    text = normalize_text("hello")
    other = normalize_text("world")
    assert compute_content_hash(text, "v1") != compute_content_hash(other, "v1")


def test_document_hash_is_identity_of_raw_bytes() -> None:
    assert compute_document_hash(b"same bytes") == compute_document_hash(b"same bytes")
    assert compute_document_hash(b"same bytes") != compute_document_hash(b"different bytes")
