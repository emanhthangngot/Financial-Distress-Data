#!/usr/bin/env python3
"""Validate the correlated Stage 5 Flink evidence package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit(evidence_dir: Path) -> dict:
    baseline_contract = _load(evidence_dir / "baseline-contract.json")
    optimized_contract = _load(evidence_dir / "optimized-contract.json")
    baseline_runtime = _load(evidence_dir / "baseline-runtime.json")
    optimized_runtime = _load(evidence_dir / "optimized-runtime.json")
    optimized_checkpoints = _load(evidence_dir / "optimized-checkpoints.json")
    restart_checkpoints = _load(evidence_dir / "restart-checkpoints.json")
    restart_after = _load(evidence_dir / "restart-after-cancel.json")

    baseline_source = baseline_runtime["vertices"][0]
    optimized_source, optimized_dedup, optimized_window = optimized_runtime["vertices"]
    restored = restart_checkpoints["latest"]["restored"]
    completed = restart_checkpoints["latest"]["completed"]
    checks = {
        "contracts_share_run_and_input": (
            baseline_contract["run_id"] == optimized_contract["run_id"]
            and baseline_contract["input_digest"] == optimized_contract["input_digest"]
            and baseline_contract["input_events"] == optimized_contract["input_events"]
        ),
        "bounded_contract_has_50000_events": baseline_contract["input_events"] == 50_000,
        "optimized_contract_removes_duplicates": (
            optimized_contract["counts"]["duplicates"] > 0
            and optimized_contract["counts"]["valid"] < baseline_contract["counts"]["valid"]
        ),
        "runtime_jobs_finished": (
            baseline_runtime["state"] == "FINISHED" and optimized_runtime["state"] == "FINISHED"
        ),
        "runtime_consumed_same_kafka_records": (
            baseline_source["metrics"]["write-records"]
            == optimized_source["metrics"]["write-records"]
            == 50_212
        ),
        "runtime_dedup_removed_records": (
            optimized_source["metrics"]["write-records"]
            > optimized_dedup["metrics"]["write-records"]
            == optimized_window["metrics"]["read-records"]
        ),
        "optimized_has_completed_checkpoint": (
            optimized_checkpoints["counts"]["completed"] > 0
            and optimized_checkpoints["latest"]["completed"]["status"] == "COMPLETED"
        ),
        "savepoint_was_restored": (
            restart_checkpoints["counts"]["restored"] == 1
            and restored["is_savepoint"] is True
            and restored["external_path"].startswith(
                "file:/opt/flink/checkpoints/savepoints/savepoint-"
            )
        ),
        "restored_job_reached_idle_checkpoint": (
            completed["status"] == "COMPLETED"
            and completed["processed_data"] == 0
            and restart_after["state"] == "CANCELED"
        ),
    }
    return {
        "schema_version": 1,
        "status": "pass" if all(checks.values()) else "fail",
        "run_id": baseline_contract["run_id"],
        "checks": checks,
        "metrics": {
            "baseline_duration_ms": baseline_runtime["duration"],
            "optimized_duration_ms": optimized_runtime["duration"],
            "baseline_parallelism": baseline_source["parallelism"],
            "optimized_parallelism": optimized_source["parallelism"],
            "baseline_source_backpressure_ms": baseline_source["metrics"][
                "accumulated-backpressured-time"
            ],
            "optimized_source_backpressure_ms_per_subtask": round(
                optimized_source["metrics"]["accumulated-backpressured-time"]
                / optimized_source["parallelism"],
                2,
            ),
            "runtime_duplicates_removed": (
                optimized_source["metrics"]["write-records"]
                - optimized_dedup["metrics"]["write-records"]
            ),
            "completed_checkpoints": optimized_checkpoints["counts"]["completed"],
            "restart_completed_checkpoints": restart_checkpoints["counts"]["completed"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=Path("docs/evidence/flink"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.evidence_dir)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
