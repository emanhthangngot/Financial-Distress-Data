"""Text normalization, chunking, and content-hash helpers for the RAG
ingestion pipeline (src.llm.rag_pipeline).

Content-hash strategy (phase-04-implementation-notes.md section 4.2):
``document_hash = sha256(raw_bytes)`` is the fetched artifact's identity.
``content_hash = sha256(normalized_chunk_text + parser_version)`` includes
``parser_version`` so a chunker change produces new hashes instead of
silently reusing chunks that no longer correspond to the stored text.
"""

from __future__ import annotations

import hashlib
import unicodedata

# Bumped by hand when chunking behaviour changes (target size, overlap,
# boundary heuristic) — never for a config-only change.
PARSER_VERSION = "v1"

_SENTENCE_BOUNDARIES = (". ", "! ", "? ", ".\n", "!\n", "?\n", "\n\n")


def normalize_text(text: str) -> str:
    """NFKC-normalize, collapse whitespace runs to a single space, strip."""
    normalized = unicodedata.normalize("NFKC", text)
    return " ".join(normalized.split())


def compute_document_hash(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def compute_content_hash(normalized_chunk_text: str, parser_version: str = PARSER_VERSION) -> str:
    payload = (normalized_chunk_text + parser_version).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _find_sentence_boundary(text: str, lo: int, hi: int) -> int | None:
    """Latest sentence-ending boundary inside ``text[lo:hi]``; the cut point
    returned is just after the boundary marker."""
    best: int | None = None
    for marker in _SENTENCE_BOUNDARIES:
        index = text.rfind(marker, lo, hi)
        if index != -1:
            candidate = index + len(marker)
            if best is None or candidate > best:
                best = candidate
    return best


def chunk_text(text: str, target_chars: int = 800, overlap_chars: int = 120) -> list[str]:
    """Recursive character chunking: target ``target_chars`` per chunk with
    ``overlap_chars`` overlap, preferring a sentence boundary within 20% of
    the target cut point over a hard mid-sentence cut."""
    if not text:
        return []
    if len(text) <= target_chars:
        return [text]

    tolerance = round(target_chars * 0.2)
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + target_chars, len(text))
        if end < len(text):
            boundary = _find_sentence_boundary(text, max(start, end - tolerance), end)
            if boundary is not None and boundary > start:
                end = boundary
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap_chars, start + 1)  # always make progress
    return chunks
