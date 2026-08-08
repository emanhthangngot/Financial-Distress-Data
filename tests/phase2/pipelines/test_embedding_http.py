"""Unit tests for src.llm.rag.embedding — no network, no live cluster.

Pins: DeterministicHashEmbedder shape/determinism; TeiHttpEmbedder's prefix
application, batching, dimension/norm contract assertions, and retry-vs-fail
classification. requests is stubbed; TeiHttpEmbedder must never import it at
module level (the two-venv rule, D4 in phase-04-implementation-notes.md) — a
module-level import would break collection here since `.venv` has neither
`requests` nor `tenacity` installed.
"""

from __future__ import annotations

import hashlib
import sys
import types

import pytest


def test_deterministic_hash_embedder_shape_and_determinism():
    from src.llm.rag.embedding import DeterministicHashEmbedder

    embedder = DeterministicHashEmbedder()
    vectors = embedder.embed(["hello world", "financial distress"])

    assert len(vectors) == 2
    assert all(len(v) == 384 for v in vectors)
    # Same input -> byte-identical output (idempotency).
    vectors_again = embedder.embed(["hello world", "financial distress"])
    assert vectors == vectors_again
    # Different input -> different vector.
    assert vectors[0] != vectors[1]


def test_deterministic_hash_embedder_changes_with_content_hash():
    from src.llm.rag.embedding import DeterministicHashEmbedder

    embedder = DeterministicHashEmbedder()
    digest_a = hashlib.sha256(b"a").hexdigest()
    digest_b = hashlib.sha256(b"b").hexdigest()
    assert digest_a != digest_b
    vectors = embedder.embed(["a", "b"])
    assert vectors[0] != vectors[1]


class _FakeResponse:
    def __init__(self, status_code: int, json_body: dict | None = None):
        self.status_code = status_code
        self._json_body = json_body or {}

    def json(self):
        return self._json_body

    def raise_for_status(self):
        if self.status_code >= 400:
            error = _FakeHTTPError(f"status {self.status_code}")
            error.response = self
            raise error


class _FakeHTTPError(Exception):
    response = None


def _install_fake_requests(monkeypatch, post_impl):
    """Install a fake `requests` module so TeiHttpEmbedder's lazy import
    resolves to a controllable stub, without requiring the real package."""
    fake_requests = types.ModuleType("requests")
    fake_requests.post = post_impl
    fake_requests.ConnectionError = ConnectionError
    fake_requests.Timeout = TimeoutError
    fake_requests.HTTPError = _FakeHTTPError
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    return fake_requests


def _normalized_vector(dims: int = 384) -> list[float]:
    import math

    raw = [1.0] + [0.0] * (dims - 1)
    norm = math.sqrt(sum(x * x for x in raw))
    return [x / norm for x in raw]


def test_tei_embedder_applies_passage_prefix_and_sends_host_header(monkeypatch):
    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append({"url": url, "json": json, "headers": headers})
        vector = _normalized_vector()
        return _FakeResponse(200, {"data": [{"embedding": vector}]})

    _install_fake_requests(monkeypatch, fake_post)

    from src.llm.rag.embedding import TeiHttpEmbedder

    embedder = TeiHttpEmbedder(
        endpoint="http://127.0.0.1:8080/v1/embeddings",
        host_header="fd-embeddings.default.svc.cluster.local",
    )
    embedder.embed(["Doanh nghiệp có tỷ lệ nợ cao."])

    assert len(calls) == 1
    assert calls[0]["json"]["input"] == ["passage: Doanh nghiệp có tỷ lệ nợ cao."]
    assert calls[0]["headers"]["Host"] == "fd-embeddings.default.svc.cluster.local"


def test_tei_embedder_batches_at_configured_size(monkeypatch):
    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append(json["input"])
        vectors = [_normalized_vector() for _ in json["input"]]
        return _FakeResponse(200, {"data": [{"embedding": v} for v in vectors]})

    _install_fake_requests(monkeypatch, fake_post)

    from src.llm.rag.embedding import TeiHttpEmbedder

    embedder = TeiHttpEmbedder(endpoint="http://x/v1/embeddings", batch_size=2)
    embedder.embed(["a", "b", "c", "d", "e"])

    assert [len(c) for c in calls] == [2, 2, 1]


def test_tei_embedder_raises_on_wrong_dimensionality(monkeypatch):
    def fake_post(url, json, headers, timeout):
        return _FakeResponse(200, {"data": [{"embedding": [0.1, 0.2]}]})

    _install_fake_requests(monkeypatch, fake_post)

    from src.llm.rag.embedding import EmbeddingBackendError, TeiHttpEmbedder

    embedder = TeiHttpEmbedder(endpoint="http://x/v1/embeddings")
    with pytest.raises(EmbeddingBackendError, match="dim"):
        embedder.embed(["text"])


def test_tei_embedder_raises_on_unnormalized_vector(monkeypatch):
    def fake_post(url, json, headers, timeout):
        vector = [1.0] * 384  # norm way above 1.0, not normalized
        return _FakeResponse(200, {"data": [{"embedding": vector}]})

    _install_fake_requests(monkeypatch, fake_post)

    from src.llm.rag.embedding import EmbeddingBackendError, TeiHttpEmbedder

    embedder = TeiHttpEmbedder(endpoint="http://x/v1/embeddings")
    with pytest.raises(EmbeddingBackendError, match="normalized"):
        embedder.embed(["text"])


def test_tei_embedder_retries_on_503_then_succeeds(monkeypatch):
    attempts = {"n": 0}

    def fake_post(url, json, headers, timeout):
        attempts["n"] += 1
        if attempts["n"] < 3:
            return _FakeResponse(503)
        return _FakeResponse(200, {"data": [{"embedding": _normalized_vector()}]})

    _install_fake_requests(monkeypatch, fake_post)

    from src.llm.rag.embedding import TeiHttpEmbedder

    embedder = TeiHttpEmbedder(endpoint="http://x/v1/embeddings")
    vectors = embedder.embed(["text"])

    assert attempts["n"] == 3
    assert len(vectors) == 1


def test_tei_embedder_does_not_retry_on_400(monkeypatch):
    """A 400 (e.g. missing Host header -> Kourier 404, or a malformed
    request) is a bug, not a transient failure — must fail immediately."""
    attempts = {"n": 0}

    def fake_post(url, json, headers, timeout):
        attempts["n"] += 1
        return _FakeResponse(400)

    _install_fake_requests(monkeypatch, fake_post)

    from src.llm.rag.embedding import TeiHttpEmbedder

    embedder = TeiHttpEmbedder(endpoint="http://x/v1/embeddings")
    with pytest.raises(_FakeHTTPError):
        embedder.embed(["text"])
    assert attempts["n"] == 1, "400 must not be retried"


def test_embedding_backends_config_parses_and_digest_matches():
    import hashlib as _hashlib
    import json

    import yaml

    config_path = "configs/embedding-backends.yaml"
    with open(config_path, encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    backend = config["backends"]["e5-small-tei"]
    recorded_digest = backend.pop("digest")
    canonical = json.dumps(backend, sort_keys=True)
    recomputed = _hashlib.sha256(canonical.encode()).hexdigest()

    assert recomputed == recorded_digest, "embedding-backends.yaml digest is stale"
