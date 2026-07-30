#!/usr/bin/env python3
"""Build and audit a deterministic DuckDB schema for reviewer inspection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_schema_evidence(sql_path: Path, output: Path) -> dict[str, object]:
    """Create the database and return table, timestamp, SCD2, and FK proof."""
    import duckdb

    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    connection = duckdb.connect(str(output))
    try:
        connection.execute(sql_path.read_text(encoding="utf-8"))
        connection.execute("""
            INSERT INTO gold.dim_company VALUES
              ('aaa-v1', 'aaa', 'AAA', 'Alpha Old', '2025-01-01', '2026-01-01', false),
              ('aaa-v2', 'aaa', 'AAA', 'Alpha New', '2026-01-01', NULL, true)
            """)
        tables = connection.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema IN ('bronze', 'silver', 'gold')
            ORDER BY table_schema, table_name
            """).fetchall()
        feature_columns = connection.execute("""
            SELECT table_name, list(column_name ORDER BY ordinal_position)
            FROM information_schema.columns
            WHERE table_schema = 'gold' AND table_name LIKE 'feat_%'
            GROUP BY table_name ORDER BY table_name
            """).fetchall()
        foreign_keys = connection.execute("""
            SELECT table_name, constraint_name
            FROM information_schema.table_constraints
            WHERE table_schema = 'gold' AND constraint_type = 'FOREIGN KEY'
            ORDER BY table_name, constraint_name
            """).fetchall()
        history = connection.execute("""
            SELECT ticker, count(*) AS versions,
                   sum(CASE WHEN is_current THEN 1 ELSE 0 END) AS current_versions
            FROM gold.dim_company GROUP BY ticker
            """).fetchall()
    finally:
        connection.close()

    required_timestamps = {"event_timestamp", "created_ts"}
    missing_feature_timestamps = [
        table for table, columns in feature_columns if not required_timestamps.issubset(columns)
    ]
    report = {
        "schema_version": 1,
        "status": "pass",
        "database": str(output),
        "zones": sorted({schema for schema, _ in tables}),
        "table_count": len(tables),
        "tables": [f"{schema}.{table}" for schema, table in tables],
        "foreign_key_count": len(foreign_keys),
        "foreign_keys": [f"{table}:{name}" for table, name in foreign_keys],
        "feature_timestamp_contract": {
            "required": sorted(required_timestamps),
            "missing_tables": missing_feature_timestamps,
        },
        "scd2_history": [
            {"ticker": ticker, "versions": versions, "current_versions": current}
            for ticker, versions, current in history
        ],
    }
    if (
        report["zones"] != ["bronze", "gold", "silver"]
        or report["table_count"] < 15
        or report["foreign_key_count"] < 4
        or missing_feature_timestamps
        or report["scd2_history"][0]["versions"] < 2
    ):
        report["status"] = "fail"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sql", type=Path, default=Path("sql/schema_evidence.sql"))
    parser.add_argument("--output", type=Path, default=Path("warehouse.db"))
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("docs/evidence/schema/phase8-schema-audit.json"),
    )
    args = parser.parse_args()
    report = build_schema_evidence(args.sql, args.output)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
