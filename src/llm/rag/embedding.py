"""Pluggable embedding backends for RagIngestionService.write_vectors.

Two backends, by design (YAGNI — a third "local model" backend was
considered and dropped, see phase-06-embedding-slice-notes.md QE-4):

- ``DeterministicHashEmbedder`` — numpy-only, seeded from content hash. Used
  by unit tests and CI so the fast loop stays network-free and dependency-free.
- ``TeiHttpEmbedder`` — calls the TEI (HuggingFace Text Embeddings Inference)
  InferenceService deployed on GKE (financial-distress-gitops
  platform/inference/embedding-server.yaml). This is the real backend for
  evidence runs.

Both produce 384-dim vectors so the PGVector column type
(``embedding vector(384)``) never changes across backends — but vectors from
different backends are NOT comparable. Callers must give each backend its
own ``embedding_version`` string; the ``(content_hash, embedding_version)``
uniqueness constraint on ``ml.rag_chunk`` depends on this.

Heavy dependencies (``requests``, ``numpy``) are imported lazily inside the
functions that need them, per the two-venv import rule (`.venv` runs the
platform .ast loop and has neither installed) — see
phase-04-implementation-notes.md D4.
"""

from __future__ import annotations

from typing import Protocol


class EmbeddingBackend(Protocol):
    """Contract every embedding backend satisfies (locks D5's design)."""

    name: str
    version: str
    dims: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts; returns one vector per input, same order."""
        ...


class DeterministicHashEmbedder:
    """Numpy-only, seeded from each text's content hash. No network, no model.

    Not semantically meaningful — used only where the test/CI fast loop must
    stay dependency-free. Never used for an evidence run.
    """

    name = "deterministic-hash-v1"
    version = "deterministic-hash-v1"
    dims = 384

    def embed(self, texts: list[str]) -> list[list[float]]:
        import hashlib

        import numpy as np

        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            seed = int.from_bytes(digest[:8], "big") % (2**32)
            rng = np.random.default_rng(seed)
            vector = rng.standard_normal(self.dims)
            vector = vector / np.linalg.norm(vector)
            vectors.append(vector.tolist())
        return vectors


class EmbeddingBackendError(RuntimeError):
    """Raised when a backend cannot honour its output contract."""


def _retry_policy():
    """Shared tenacity retry: transport/5xx/429 only, never on 4xx.

    Hoisted into ``src.llm.data_governance.retry_policy`` now that 4B exists
    (phase-06-embedding-slice-notes.md Phase E3's deliberate DRY note) — this
    is a thin re-export so existing call sites in this module don't churn.
    """
    from src.llm.data_governance import retry_policy

    return retry_policy()


class TeiHttpEmbedder:
    """Calls a TEI (Text Embeddings Inference) OpenAI-compatible endpoint.

    Deployed as the ``fd-embeddings`` KServe InferenceService
    (financial-distress-gitops platform/inference/embedding-server.yaml),
    serving ``intfloat/multilingual-e5-small`` (384-dim, multilingual,
    handles Vietnamese). Reached today via ``kubectl port-forward`` — no
    public route (see phase-06-embedding-slice-notes.md D-E6).

    e5 models require instruction prefixes: ingested/stored text uses
    ``"passage: "``, queries use ``"query: "``. Getting this wrong degrades
    retrieval silently (no error, just worse neighbours) — the prefix is
    applied here, not left to the caller, and is baked into ``version``.
    """

    name = "intfloat/multilingual-e5-small"
    dims = 384

    def __init__(
        self,
        endpoint: str,
        host_header: str | None = None,
        prefix: str = "passage: ",
        embedding_version: str = "e5s-tei-v1",
        timeout: tuple[float, float] = (5.0, 180.0),
        batch_size: int = 32,
    ) -> None:
        self.endpoint = endpoint
        self.host_header = host_header
        self.prefix = prefix
        self.version = embedding_version
        self.timeout = timeout
        self.batch_size = batch_size

    def embed(self, texts: list[str]) -> list[list[float]]:
        import requests

        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            vectors.extend(self._embed_batch(batch, requests))
        return vectors

    def _embed_batch(self, batch: list[str], requests_module) -> list[list[float]]:
        @_retry_policy()
        def _post():
            headers = {"Content-Type": "application/json"}
            if self.host_header:
                headers["Host"] = self.host_header
            payload = {
                "model": self.name,
                "input": [self.prefix + text for text in batch],
            }
            response = requests_module.post(
                f"{self.endpoint}",
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()

        body = _post()
        data = body.get("data", [])
        vectors = [row["embedding"] for row in data]
        self._assert_contract(batch, vectors)
        return vectors

    def _assert_contract(self, batch: list[str], vectors: list[list[float]]) -> None:
        import math

        if len(vectors) != len(batch):
            raise EmbeddingBackendError(f"expected {len(batch)} vectors, got {len(vectors)}")
        for vector in vectors:
            if len(vector) != self.dims:
                raise EmbeddingBackendError(f"expected {self.dims}-dim vector, got {len(vector)}")
        norm = math.sqrt(sum(v * v for v in vectors[0]))
        if abs(norm - 1.0) > 1e-3:
            raise EmbeddingBackendError(
                f"expected L2-normalized output (norm≈1.0), got norm={norm:.4f}"
            )
