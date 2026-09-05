"""Schema evidence contract (phase-02-data-model.md Step 8, partial).

Full AC-P2-9/AC-P2-10 (real Gold Parquet, zero-orphan / NULL-rate-ceiling
assertions against actual pipeline output) need a running Spark+MinIO stack
and the physical-storage-layer rename this phase's follow-up still owns —
see src/io/paths.py's module docstring note. These tests cover what the
current DuckDB-fixture-based scripts/build_schema_evidence.py can prove
without live infra: the target DDL (sql/schema_evidence.sql) is internally
consistent, and the evidence audit is a live assertion, not vacuous.
"""

from __future__ import annotations

from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")

from scripts.build_schema_evidence import build_schema_evidence  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_SQL = REPO_ROOT / "sql" / "schema_evidence.sql"


def test_schema_evidence_passes_against_target_ddl(tmp_path: Path) -> None:
    report = build_schema_evidence(SCHEMA_SQL, tmp_path / "warehouse.db")

    assert report["status"] == "pass"
    assert report["zones"] == ["bronze", "gold", "silver"]
    assert report["table_count"] == 18
    assert report["foreign_key_count"] >= 4
    assert report["feature_timestamp_contract"]["missing_tables"] == []
    assert report["scd2_history"] == [{"ticker": "AAA", "versions": 2, "current_versions": 1}]


def test_schema_evidence_reports_all_twelve_gold_datasets(tmp_path: Path) -> None:
    """AC-P2-18: 12 Gold tables, including the three that were missing pre-rebuild."""
    report = build_schema_evidence(SCHEMA_SQL, tmp_path / "warehouse.db")

    gold_tables = {name.split(".", 1)[1] for name in report["tables"] if name.startswith("gold.")}
    assert len(gold_tables) == 12
    for required in ("fact_market_alert", "fact_news_sentiment", "fact_distress_label"):
        assert required in gold_tables


def test_schema_evidence_fails_closed_when_a_feature_table_drops_a_reserved_column(
    tmp_path: Path,
) -> None:
    """AC-P2-21 / F14 negative test: the audit must be a live assertion, not vacuous.

    A minimal but otherwise well-formed schema that omits ``created_timestamp``
    from a ``feat_`` table must fail the audit — proving the check actually
    inspects real column names instead of trusting table presence alone.
    """
    broken_sql = tmp_path / "broken_schema.sql"
    broken_sql.write_text(
        """
        CREATE SCHEMA bronze;
        CREATE SCHEMA silver;
        CREATE SCHEMA gold;
        CREATE TABLE bronze.raw_companies (ticker VARCHAR, created_ts TIMESTAMP);
        CREATE TABLE silver.stg_companies (ticker VARCHAR, created_ts TIMESTAMP);
        CREATE TABLE gold.dim_company (
            company_version_key VARCHAR PRIMARY KEY,
            ticker VARCHAR NOT NULL,
            company_name VARCHAR NOT NULL,
            exchange VARCHAR NOT NULL,
            industry VARCHAR,
            sector VARCHAR,
            listing_date DATE,
            delisted_flag BOOLEAN NOT NULL DEFAULT FALSE,
            valid_from_ts TIMESTAMP NOT NULL,
            valid_to_ts TIMESTAMP,
            is_current BOOLEAN NOT NULL
        );
        -- Missing created_timestamp — the reserved Feast tie-break column.
        CREATE TABLE gold.feat_incomplete (
            ticker VARCHAR NOT NULL,
            event_timestamp TIMESTAMP NOT NULL,
            known_from_ts TIMESTAMP NOT NULL
        );
        """,
        encoding="utf-8",
    )

    report = build_schema_evidence(broken_sql, tmp_path / "broken_warehouse.db")

    assert report["status"] == "fail"
    assert "feat_incomplete" in report["feature_timestamp_contract"]["missing_tables"]
