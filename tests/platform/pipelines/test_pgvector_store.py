"""Real-psycopg pin for src/llm/rag/pgvector_store.py against an ephemeral
local Postgres cluster running sql/init_ml.sql: upsert idempotency,
the (content_hash, embedding_version) unique constraint, and quarantine
writes. Marked postgres + slow (mirrors tests/platform/product/conftest.py's
pattern), and additionally skipped when the pgvector extension itself isn't
installed on this machine — the pgvector/pgvector:pg16 Docker image ships it,
a bare local Postgres usually does not.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import psycopg
import pytest

from src.llm.rag.pgvector_store import PgVectorStore
from src.llm.rag_pipeline import Chunk, RawDocument

pytestmark = [pytest.mark.postgres, pytest.mark.slow]

REPO_ROOT = Path(__file__).resolve().parents[3]
INIT_SQL = REPO_ROOT / "sql" / "init_ml.sql"


@pytest.fixture(scope="module")
def ml_metadata_conn(tmp_path_factory: pytest.TempPathFactory):
    for binary in ("initdb", "pg_ctl"):
        if shutil.which(binary) is None:
            message = f"{binary} not available; cannot run real-Postgres RAG store tests"
            if os.environ.get("PHASE2_REQUIRE_PG") == "1":
                pytest.fail(message)
            pytest.skip(message)

    data_dir = tmp_path_factory.mktemp("rag-pgdata")
    socket_dir = tmp_path_factory.mktemp("rag-pgsocket")
    log_file = data_dir / "server.log"

    subprocess.run(
        ["initdb", "-D", str(data_dir), "-U", "postgres", "-A", "trust"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "pg_ctl",
            "-D",
            str(data_dir),
            "-o",
            f"-k {socket_dir} -h '' -c listen_addresses=''",
            "-l",
            str(log_file),
            "start",
        ],
        check=True,
        capture_output=True,
    )
    try:
        for _ in range(50):
            try:
                with psycopg.connect(dbname="postgres", user="postgres", host=str(socket_dir)):
                    break
            except psycopg.OperationalError:
                time.sleep(0.1)
        else:
            raise RuntimeError(f"Postgres did not become ready; see {log_file}")

        admin_conn = psycopg.connect(
            dbname="postgres", user="postgres", host=str(socket_dir), autocommit=True
        )
        admin_conn.execute("create database ml_metadata_test")
        admin_conn.close()

        conn = psycopg.connect(dbname="ml_metadata_test", user="postgres", host=str(socket_dir))
        try:
            conn.execute(INIT_SQL.read_text(encoding="utf-8"))
            conn.commit()
        except (psycopg.errors.FeatureNotSupported, psycopg.errors.UndefinedFile) as exc:
            conn.rollback()
            conn.close()
            # Always skip here, never escalate via PHASE2_REQUIRE_PG: that var
            # (tests/platform/product/conftest.py) exists to guarantee the
            # initdb/pg_ctl *binaries* are present, not that every Postgres
            # extension is installed. CI's `apt-get install postgresql` step
            # (.github/workflows/ci.yml) does not install pgvector — that only
            # ships in pgvector/pgvector:pg16 (docker-compose.yml's
            # phase2-postgres service). Wiring a pgvector-capable CI job is
            # slice 4D's job (phase2-*.yaml workflows), not this test's.
            pytest.skip(f"pgvector extension not available on this machine: {exc}")

        yield conn
        conn.close()
    finally:
        subprocess.run(
            ["pg_ctl", "-D", str(data_dir), "-m", "immediate", "stop"],
            capture_output=True,
        )


@pytest.fixture()
def store(ml_metadata_conn: psycopg.Connection):
    for table in ("rag_chunk", "rag_quarantine", "rag_ingestion_run", "rag_document"):
        ml_metadata_conn.execute(f"truncate ml.{table} cascade")
    ml_metadata_conn.commit()
    return PgVectorStore(ml_metadata_conn)


def _document() -> RawDocument:
    return RawDocument(
        source_uri="tests/platform/fixtures/rag_corpus/vnstock_news_vnm.txt",
        source_name="vnstock_news",
        company="VNM",
        report_date=None,
        raw_bytes=b"placeholder",
        content_type="text/plain",
        license="vnstock_public_api_terms",
        access_class="public_market_commentary",
        fetched_ts="2026-08-08T00:00:00+00:00",
    )


def _chunk(document_hash: str = "doc-hash-1", content_hash: str = "content-hash-1") -> Chunk:
    return Chunk(
        document_hash=document_hash,
        content_hash=content_hash,
        chunk_index=0,
        chunk_text="Vinamilk cong bo ket qua kinh doanh quy gan nhat.",
        source_uri="tests/platform/fixtures/rag_corpus/vnstock_news_vnm.txt",
        company="VNM",
        report_date=None,
        parser_version="v1",
        access_class="public_market_commentary",
    )


def test_document_round_trip(store: PgVectorStore) -> None:
    document = _document()
    assert store.document_exists("doc-hash-1") is False
    store.upsert_document(document, "doc-hash-1", "2026-08-08T00:00:00+00:00")
    assert store.document_exists("doc-hash-1") is True


def test_insert_chunks_is_idempotent(store: PgVectorStore) -> None:
    # rag_chunk.document_hash is NOT NULL REFERENCES rag_document — the
    # parent document must exist first (sql/init_ml.sql).
    store.upsert_document(_document(), "doc-hash-1", "2026-08-08T00:00:00+00:00")
    vector = [0.1] * 384
    chunk = _chunk()
    first = store.insert_chunks([(chunk, vector)], "test-model", "v1", "2026-08-08-abc123")
    second = store.insert_chunks([(chunk, vector)], "test-model", "v1", "2026-08-08-abc123")
    assert first == 1
    assert second == 0  # unique (content_hash, embedding_version) blocks the rerun


def test_different_embedding_version_inserts_a_new_row(store: PgVectorStore) -> None:
    store.upsert_document(_document(), "doc-hash-1", "2026-08-08T00:00:00+00:00")
    vector = [0.1] * 384
    chunk = _chunk()
    store.insert_chunks([(chunk, vector)], "test-model", "v1", "2026-08-08-abc123")
    inserted_v2 = store.insert_chunks([(chunk, vector)], "test-model", "v2", "2026-08-08-def456")
    assert inserted_v2 == 1
    assert store.content_hash_exists(chunk.content_hash, "v1") is True
    assert store.content_hash_exists(chunk.content_hash, "v2") is True


def test_insert_quarantine_writes_a_row(store: PgVectorStore) -> None:
    chunk = _chunk()
    store.insert_quarantine(chunk, "pii detected: email")
    with store.conn.cursor() as cur:
        cur.execute("SELECT violation_reason FROM ml.rag_quarantine")
        row = cur.fetchone()
    assert row == ("pii detected: email",)


def test_record_ingestion_run_writes_a_row(store: PgVectorStore) -> None:
    store.record_ingestion_run(
        ingestion_version="2026-08-08-abc123",
        run_id="run-1",
        started_ts="2026-08-08T00:00:00+00:00",
        finished_ts="2026-08-08T00:01:00+00:00",
        documents_fetched=1,
        chunks_new=3,
        chunks_reused=0,
        chunks_quarantined=1,
        source_sha="a" * 40,
    )
    with store.conn.cursor() as cur:
        cur.execute("SELECT chunks_new FROM ml.rag_ingestion_run")
        row = cur.fetchone()
    assert row == (3,)
