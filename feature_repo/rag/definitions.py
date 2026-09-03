"""fd_rag Feast project: entity + FeatureView over ml.rag_chunk
(sql/init_ml_metadata.sql, written directly by src.llm.rag_pipeline).

Registered for ADR-005 compliance (a documented offline/online split for the
RAG store) — actual RAG retrieval in this repo goes through direct PGVector
SQL (src/llm/rag/pgvector_store.py), not Feast's online-store API. No
retrieval code depends on this file; it exists so `feast apply` can register
the project and so the offline/online contract is provable, per ADR-005's
amendment note that the offline store must be defined correctly even though
only the online path is exercised this week.

Loaded only by the `feast` CLI (.venv-phase2) — physical construction here
rather than a re-export from src/, since no src/llm module needs a Feast
dependency of its own (RagIngestionPipeline never imports feast).
"""

from datetime import timedelta

from feast import Entity, FeatureView, Field, FileSource
from feast.types import Array, Float32, String
from feast.value_type import ValueType

chunk_id = Entity(name="chunk_id", join_keys=["chunk_id"], value_type=ValueType.STRING)

# Offline source: the chunking/embedding pipeline writes directly to
# Postgres, not parquet — this FileSource is a placeholder satisfying
# "every FeatureView declares an offline source" (phase-04.md:108) rather
# than a populated dataset. A real offline export is out of scope for this
# slice (RAG training-set export belongs to the phase-05 ML retrofit).
_offline_placeholder = FileSource(
    name="rag_chunk_offline_placeholder",
    path="s3://financial-distress-lake/phase2/rag/offline/rag_chunk_placeholder.parquet",
    timestamp_field="created_ts",
)

document_chunk_vectors = FeatureView(
    name="document_chunk_vectors",
    entities=[chunk_id],
    ttl=timedelta(days=365),  # tied to document version, not calendar time —
    # a chunk is valid until its parent document hash changes, at which
    # point re-ingestion supersedes it explicitly; TTL is a backstop only.
    schema=[
        Field(name="embedding", dtype=Array(Float32)),
        Field(name="embedding_model", dtype=String),
        Field(name="embedding_version", dtype=String),
    ],
    source=_offline_placeholder,
    description=(
        "Tied to document version: a chunk is valid until its parent "
        "document hash changes, at which point ingestion supersedes it "
        "explicitly rather than letting it expire. TTL is a backstop, not "
        "the invalidation mechanism."
    ),
)
