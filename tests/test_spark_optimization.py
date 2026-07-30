from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_spark_benchmark import _final_plan
from src.jobs.spark_benchmark_common import (
    assert_equivalent_reports,
    canonical_output_digest,
    load_benchmark_config,
    summarize_durations,
)

CONFIG_PATH = Path("configs/spark-benchmark.yaml")


def test_benchmark_config_freezes_input_and_measurement_protocol():
    config = load_benchmark_config(CONFIG_PATH)

    assert config.run_id == "generator-evidence-v1"
    assert config.repetitions == 5
    assert config.warmup_runs == 1
    assert config.salt_buckets == 8
    assert config.baseline.adaptive_enabled is False
    assert config.baseline.auto_broadcast_enabled is False
    assert config.optimized.adaptive_enabled is True
    assert config.optimized.auto_broadcast_enabled is True


def test_benchmark_config_rejects_invalid_protocol(tmp_path: Path):
    raw = json.loads(json.dumps(load_benchmark_config(CONFIG_PATH).to_dict()))
    raw["repetitions"] = 0
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="repetitions"):
        load_benchmark_config(path)


def test_canonical_digest_ignores_output_row_order_but_not_values():
    rows = [
        {"sector": "Retail", "statement_count": 2, "total_assets": 10.0},
        {"sector": "Energy", "statement_count": 1, "total_assets": 3.0},
    ]

    assert canonical_output_digest(rows) == canonical_output_digest(list(reversed(rows)))
    changed = [dict(row) for row in rows]
    changed[0]["statement_count"] = 3
    assert canonical_output_digest(rows) != canonical_output_digest(changed)


def test_report_audit_requires_same_input_and_output_digests():
    baseline = {
        "run_id": "run-1",
        "input_digest": "input",
        "input_counts": {"rows": 10},
        "output_digest": "output",
        "output_rows": 5,
    }
    optimized = dict(baseline)
    assert_equivalent_reports(baseline, optimized)

    optimized["output_digest"] = "different"
    with pytest.raises(ValueError, match="output_digest"):
        assert_equivalent_reports(baseline, optimized)


def test_report_audit_rejects_different_runs_and_storage_populations():
    baseline = {
        "run_id": "run-1",
        "input_digest": "input",
        "input_counts": {"rows": 10},
        "output_digest": "output",
        "output_rows": 5,
        "storage": {"row_count": 10, "filtered_year": 2024, "filtered_row_count": 6},
    }
    optimized = json.loads(json.dumps(baseline))
    optimized["run_id"] = "run-2"
    with pytest.raises(ValueError, match="run_id"):
        assert_equivalent_reports(baseline, optimized)

    optimized = json.loads(json.dumps(baseline))
    optimized["storage"]["row_count"] = 9
    with pytest.raises(ValueError, match="storage row_count"):
        assert_equivalent_reports(baseline, optimized)


def test_duration_summary_uses_median_and_records_each_run():
    summary = summarize_durations([3.0, 1.0, 2.0, 9.0, 4.0])

    assert summary["median_seconds"] == 3.0
    assert summary["runs_seconds"] == [3.0, 1.0, 2.0, 9.0, 4.0]


def test_aqe_signal_counts_exclude_repeated_initial_plan():
    plan = "Final Exchange\n+- == Initial Plan ==\nInitial Exchange\n"

    assert _final_plan(plan) == "Final Exchange\n"


def test_baseline_and_optimized_sources_expose_intentional_plan_differences():
    baseline = Path("src/jobs/spark_baseline_job.py").read_text(encoding="utf-8")
    optimized = Path("src/jobs/spark_optimized_job.py").read_text(encoding="utf-8")

    assert "countDistinct" in baseline
    assert "Window.partitionBy" in baseline
    assert "broadcast(" not in baseline
    assert "allowMissingColumns=True" in optimized
    assert "max_by" in optimized
    assert "broadcast(" in optimized
    assert '"_salt"' in optimized
    assert "xxhash64" in optimized


def test_postgres_benchmark_contains_before_after_explain_and_real_index():
    sql = Path("sql/postgres-index-benchmark.sql").read_text(encoding="utf-8")

    assert sql.count("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)") == 2
    assert "DROP INDEX IF EXISTS" in sql
    assert "CREATE INDEX" in sql
    assert "source_request_log" in sql
