"""Live smoke test for the fd-embeddings TEI InferenceService on GKE.

Not a pytest test — this needs a live cluster (kubectl port-forward) and is
run manually as evidence, per phase-06-embedding-slice-notes.md Phase E4.

Usage (after `kubectl port-forward -n kourier-system svc/kourier-internal
18080:80` in another terminal):

    .venv-phase2/bin/python scripts/smoke_embedding_endpoint.py

Or override the endpoint/host:

    EMBEDDING_ENDPOINT=http://127.0.0.1:18080/v1/embeddings \\
    EMBEDDING_HOST_HEADER=fd-embeddings-predictor.default.svc.cluster.local \\
    .venv-phase2/bin/python scripts/smoke_embedding_endpoint.py
"""

from __future__ import annotations

import hashlib
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm.rag.embedding import TeiHttpEmbedder  # noqa: E402


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot / (norm_a * norm_b)


def main() -> int:
    endpoint = os.environ.get("EMBEDDING_ENDPOINT", "http://127.0.0.1:18080/v1/embeddings")
    host_header = os.environ.get(
        "EMBEDDING_HOST_HEADER", "fd-embeddings-predictor.default.svc.cluster.local"
    )

    embedder = TeiHttpEmbedder(endpoint=endpoint, host_header=host_header)

    vi_1 = "Công ty cổ phần này có tỷ lệ nợ trên tổng tài sản cao."
    vi_2 = "Doanh nghiệp ghi nhận dòng tiền hoạt động âm ba quý liên tiếp."
    en_control = "The weather in Paris is sunny today."

    vectors = embedder.embed([vi_1, vi_2, en_control])
    assert len(vectors) == 3, f"expected 3 vectors, got {len(vectors)}"
    assert all(len(v) == 384 for v in vectors), "expected 384-dim vectors"

    sim_vi = _cosine(vectors[0], vectors[1])
    sim_en = _cosine(vectors[0], vectors[2])
    print(f"sim(vi1, vi2) = {sim_vi:.4f}")
    print(f"sim(vi1, en)  = {sim_en:.4f}")
    assert (
        sim_vi > sim_en
    ), "Vietnamese sentences should be more similar to each other than to the English control"

    # Idempotence: same text -> byte-identical vector across two calls.
    repeat_a = embedder.embed(["passage-independent idempotence check"])[0]
    repeat_b = embedder.embed(["passage-independent idempotence check"])[0]
    hash_a = hashlib.sha256(str(repeat_a).encode()).hexdigest()
    hash_b = hashlib.sha256(str(repeat_b).encode()).hexdigest()
    assert hash_a == hash_b, "same input should yield byte-identical output"

    print("OK: dims=384, normalized, semantically sane, idempotent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
