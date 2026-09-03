"""
Stage 1 evidence orchestrator.

End-to-end runner that drives the Stage 1 evidence pipeline from the command
line: starts services if needed, triggers the local-evidence DAG, and writes
the result bundle to ``docs/evidence/``. Used by rubric row 4.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.catalog.duckdb_runner import run_duckdb_validation as write_duckdb_validation
from src.io.minio_writer import rows_to_parquet_bytes as _to_parquet_bytes
from src.io.minio_writer import write_minio_dataset as _write_minio_dataset
from src.jobs.lakehouse_evidence_job import (
    DEFAULT_BUCKET,
    DEFAULT_ENV_PATH,
    DEFAULT_EVIDENCE_DIR,
    EvidencePayload,
    build_evidence_payload,
    materialize_lakehouse_evidence,
    metadata_dsn,
    minio_host_endpoint,
    read_env_file,
    write_evidence_files,
    write_minio_outputs,
    write_postgres_metadata,
)

__all__ = [
    "DEFAULT_BUCKET",
    "DEFAULT_ENV_PATH",
    "DEFAULT_EVIDENCE_DIR",
    "EvidencePayload",
    "_to_parquet_bytes",
    "_write_minio_dataset",
    "build_evidence_payload",
    "metadata_dsn",
    "minio_host_endpoint",
    "read_env_file",
    "write_duckdb_validation",
    "write_evidence_files",
    "write_minio_outputs",
    "write_postgres_metadata",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize Stage 1 runtime evidence.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build payload and local evidence files only.",
    )
    parser.add_argument("--bucket", default=os.getenv("FINANCIAL_DISTRESS_BUCKET", DEFAULT_BUCKET))
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = materialize_lakehouse_evidence(
        bucket=args.bucket,
        evidence_dir=args.evidence_dir,
        dry_run=args.dry_run,
    )
    print(json.dumps(payload.row_counts, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
