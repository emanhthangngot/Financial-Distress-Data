"""
Stage 1 evidence audit.

Compares the local Stage 1 evidence bundle against the rubric checklist. Used
by the rubric row 4 evidence-acceptance flow to confirm that every required
artefact is present and well-formed before submission.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_TOPICS = {
    "financial.price_events",
    "financial.news_events",
    "financial.alert_events",
}
REQUIRED_DUCKDB_METRICS = {
    "total_financial_statement_rows": 16,
    "total_dim_company_rows": 2,
    "total_news_sentiment_rows": 2,
    "total_market_alert_rows": 1,
    "total_financial_feature_rows": 16,
    "total_market_feature_rows": 12,
    "total_news_feature_rows": 2,
    "future_feature_leakage_rows": 0,
}
REQUIRED_MINIO_PREFIXES = {
    "bronze/companies/",
    "bronze/financial_statements/",
    "bronze/market_prices_daily/",
    "bronze/kafka/financial.price_events/",
    "bronze/kafka/financial.news_events/",
    "bronze/kafka/financial.alert_events/",
    "silver/companies/",
    "silver/financial_statements/",
    "silver/market_prices_daily/",
    "gold/dim_company/",
    "gold/fact_financial_statement/",
    "gold/fact_market_price/",
    "gold/fact_news_sentiment/",
    "gold/fact_market_alert/",
    "gold/obt_company_quarter_risk/",
    "gold/feat_company_unified/",
    "evidence/stage1/",
}
REQUIRED_JSON_ARTIFACTS = (
    "stage1_real_kafka_offsets.json",
    "stage1_real_postgres_summary.json",
    "stage1_real_duckdb_validation.json",
    "stage1_real_minio_objects.json",
)


def _airflow_log_success(evidence_dir: Path) -> bool:
    path = evidence_dir / "stage1_real_airflow_dag_test.txt"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return "DagRun Finished" in text and "state=success" in text


def _load_json(evidence_dir: Path, filename: str) -> Any:
    return json.loads((evidence_dir / filename).read_text(encoding="utf-8"))


def _load_required_json_artifacts(evidence_dir: Path) -> tuple[dict[str, Any], dict[str, bool]]:
    artifacts = {}
    checks = {}
    for filename in REQUIRED_JSON_ARTIFACTS:
        check_name = f"artifact_{filename}_readable"
        try:
            artifacts[filename] = _load_json(evidence_dir, filename)
            checks[check_name] = True
        except (FileNotFoundError, json.JSONDecodeError):
            artifacts[filename] = None
            checks[check_name] = False
    return artifacts, checks


def _dq_failure_probe_passed(evidence_dir: Path) -> bool:
    path = evidence_dir / "stage1_dq_failure_probe.json"
    if not path.exists():
        return False
    payload = json.loads(path.read_text(encoding="utf-8"))
    return (
        payload.get("halted") is True
        and payload.get("expected_outcome") == "critical_failure_persisted_before_halt"
        and "ticker_not_null" in str(payload.get("error_message", ""))
    )


def _metric_rows(duckdb_validation: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = {}
    for result in duckdb_validation:
        columns = result.get("columns", [])
        rows = result.get("rows", [])
        if len(columns) == 1 and len(rows) == 1 and len(rows[0]) == 1:
            metrics[columns[0]] = rows[0][0]
    return metrics


def _financial_statement_duplicate_check_passed(
    duckdb_validation: list[dict[str, Any]],
) -> bool:
    for result in duckdb_validation:
        columns = result.get("columns", [])
        if columns == ["ticker", "report_period", "cnt"]:
            return result.get("rows", []) == []
    return False


def _distress_label_distribution_passed(duckdb_validation: list[dict[str, Any]]) -> bool:
    for result in duckdb_validation:
        columns = result.get("columns", [])
        if columns == ["distress_label", "row_count"]:
            labels = {row[0] for row in result.get("rows", [])}
            return {0, 1}.issubset(labels)
    return False


def _topic_has_positive_offset(lines: list[str]) -> bool:
    for line in lines:
        parts = line.rsplit(":", 1)
        if len(parts) == 2 and parts[1].isdigit() and int(parts[1]) > 0:
            return True
    return False


def audit_evidence(evidence_dir: str | Path) -> dict[str, Any]:
    root = Path(evidence_dir)
    artifacts, artifact_checks = _load_required_json_artifacts(root)
    kafka_offsets = artifacts["stage1_real_kafka_offsets.json"] or {}
    postgres_summary = artifacts["stage1_real_postgres_summary.json"] or {}
    duckdb_validation = artifacts["stage1_real_duckdb_validation.json"] or []
    minio_objects = artifacts["stage1_real_minio_objects.json"] or []
    metrics = _metric_rows(duckdb_validation)
    object_names = [item["object_name"] for item in minio_objects]

    checks = {
        **artifact_checks,
        "airflow_log_success": _airflow_log_success(root),
        "all_kafka_topics_present": REQUIRED_TOPICS.issubset(kafka_offsets),
        "all_kafka_topics_have_offsets": all(kafka_offsets.get(topic) for topic in REQUIRED_TOPICS),
        "all_kafka_topics_have_positive_offsets": all(
            _topic_has_positive_offset(kafka_offsets.get(topic, [])) for topic in REQUIRED_TOPICS
        ),
        "minio_has_gold_alert_fact": any(
            object_name.startswith("gold/fact_market_alert/") for object_name in object_names
        ),
        "minio_has_required_medallion_prefixes": all(
            any(object_name.startswith(prefix) for object_name in object_names)
            for prefix in REQUIRED_MINIO_PREFIXES
        ),
        "postgres_has_backfill_evidence": "backfill_request" in postgres_summary
        and "completed" in postgres_summary["backfill_request"],
        "postgres_has_source_request_evidence": "source_request_log" in postgres_summary
        and "vnstock_fixture" in postgres_summary["source_request_log"],
        "postgres_has_collector_checkpoint_evidence": "collector_checkpoint" in postgres_summary
        and "stage1_fixture_collectors" in postgres_summary["collector_checkpoint"],
        "postgres_has_freshness_evidence": "dataset_freshness" in postgres_summary
        and "silver_market_prices" in postgres_summary["dataset_freshness"],
        "postgres_has_dq_evidence": "data_quality_result" in postgres_summary
        and "gold_fact_market_alert" in postgres_summary["data_quality_result"],
        "dq_failure_probe_halted": _dq_failure_probe_passed(root),
        "duckdb_financial_statement_duplicate_check_empty": (
            _financial_statement_duplicate_check_passed(duckdb_validation)
        ),
        "duckdb_distress_label_distribution_has_safe_and_distress": (
            _distress_label_distribution_passed(duckdb_validation)
        ),
    }
    for metric_name, minimum_or_exact in REQUIRED_DUCKDB_METRICS.items():
        value = metrics.get(metric_name)
        if metric_name == "future_feature_leakage_rows":
            checks[f"duckdb_{metric_name}_ok"] = value == minimum_or_exact
        else:
            checks[f"duckdb_{metric_name}_ok"] = value is not None and value >= minimum_or_exact
    failed_checks = sorted(name for name, passed in checks.items() if not passed)

    return {
        "evidence_dir": str(root),
        "status": "pass" if not failed_checks else "fail",
        "checks": checks,
        "failed_checks": failed_checks,
        "duckdb_metrics": metrics,
        "kafka_topics": sorted(kafka_offsets),
        "minio_object_count": len(minio_objects),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Stage 1 E2E evidence artifacts.")
    parser.add_argument("evidence_dir")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if stage1_runtime_audit_summary.json is missing or stale.",
    )
    args = parser.parse_args()

    summary = audit_evidence(args.evidence_dir)
    output_path = Path(args.evidence_dir) / "stage1_runtime_audit_summary.json"
    summary_text = json.dumps(summary, indent=2, sort_keys=True)
    if args.check:
        if not output_path.exists():
            print(f"Missing audit summary: {output_path}")
            raise SystemExit(1)
        current = output_path.read_text(encoding="utf-8").strip()
        if current != summary_text:
            print(f"Stale audit summary: {output_path}")
            raise SystemExit(1)
    else:
        output_path.write_text(f"{summary_text}\n", encoding="utf-8")
    print(summary_text)
    if summary["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
