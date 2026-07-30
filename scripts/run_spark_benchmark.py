#!/usr/bin/env python3
"""Run one reproducible Spark baseline or optimized benchmark variant."""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.jobs.spark_baseline_job import build_baseline_plan  # noqa: E402
from src.jobs.spark_benchmark_common import (  # noqa: E402
    canonical_output_digest,
    file_digest,
    load_benchmark_config,
    summarize_durations,
)
from src.jobs.spark_optimized_job import build_optimized_plan  # noqa: E402
from src.jobs.spark_storage_experiment import run_storage_experiment  # noqa: E402
from src.jobs.stage1_spark_lakehouse_job import _spark_session  # noqa: E402


def _rows(dataframe: Any) -> list[dict[str, Any]]:
    return [row.asDict(recursive=True) for row in dataframe.collect()]


def _final_plan(executed_plan: str) -> str:
    """Exclude AQE's repeated initial plan from structural signal counts."""
    return executed_plan.split("+- == Initial Plan ==", maxsplit=1)[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/spark-benchmark.yaml"))
    parser.add_argument("--variant", choices=("baseline", "optimized"), required=True)
    parser.add_argument("--runs", type=int)
    parser.add_argument("--warmups", type=int)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-storage", action="store_true")
    parser.add_argument("--hold-ui-seconds", type=int, default=0)
    parser.add_argument("--ui-snapshot", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_benchmark_config(args.config)
    runs = config.repetitions if args.runs is None else args.runs
    warmups = config.warmup_runs if args.warmups is None else args.warmups
    if runs <= 0 or warmups < 0:
        raise ValueError("runs must be positive and warmups non-negative")
    settings = getattr(config, args.variant)
    spark = _spark_session(f"financial-distress-spark-{args.variant}")
    spark.conf.set("spark.sql.shuffle.partitions", str(settings.shuffle_partitions))
    spark.conf.set("spark.sql.adaptive.enabled", str(settings.adaptive_enabled).lower())
    spark.conf.set(
        "spark.sql.autoBroadcastJoinThreshold",
        "10485760" if settings.auto_broadcast_enabled else "-1",
    )
    try:
        companies = spark.read.parquet(f"{config.input_root}/companies/").cache()
        statements = spark.read.parquet(f"{config.input_root}/financial_statements/").cache()
        input_counts = {
            "companies": companies.count(),
            "financial_statements": statements.count(),
        }
        build = build_baseline_plan if args.variant == "baseline" else build_optimized_plan

        def plan() -> Any:
            if args.variant == "baseline":
                return build(companies, statements)
            return build(companies, statements, config.salt_buckets)

        for _ in range(warmups):
            _rows(plan())
        durations = []
        output_rows: list[dict[str, Any]] = []
        executed_plan = ""
        for _ in range(runs):
            started = time.perf_counter()
            dataframe = plan()
            output_rows = _rows(dataframe)
            durations.append(time.perf_counter() - started)
            executed_plan = dataframe._jdf.queryExecution().executedPlan().toString()
        signal_plan = _final_plan(executed_plan)
        report: dict[str, Any] = {
            "schema_version": 1,
            "status": "pass",
            "run_id": config.run_id,
            "variant": args.variant,
            "input_digest": file_digest(args.source_manifest),
            "input_counts": input_counts,
            "output_digest": canonical_output_digest(output_rows),
            "output_rows": len(output_rows),
            "output": output_rows,
            "duration": summarize_durations(durations),
            "protocol": {
                "warmup_runs": warmups,
                "measured_runs": runs,
                "shuffle_partitions": settings.shuffle_partitions,
                "adaptive_enabled": settings.adaptive_enabled,
                "auto_broadcast_enabled": settings.auto_broadcast_enabled,
                "salt_buckets": config.salt_buckets if args.variant == "optimized" else 0,
            },
            "plan_signals": {
                "exchange_count": signal_plan.count("Exchange"),
                "sort_count": signal_plan.count("Sort"),
                "window_count": signal_plan.count("Window"),
                "broadcast_count": signal_plan.count("Broadcast"),
                "physical_plan": executed_plan,
            },
            "runtime": {
                "python": platform.python_version(),
                "spark": spark.version,
                "platform": platform.platform(),
                "default_parallelism": spark.sparkContext.defaultParallelism,
                "ui_url": spark.sparkContext.uiWebUrl,
            },
        }
        if args.include_storage:
            report["storage"] = run_storage_experiment(spark, statements, config, args.variant)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
        excluded = {"output", "plan_signals"}
        summary = {key: value for key, value in report.items() if key not in excluded}
        summary["plan_signals"] = {
            key: value for key, value in report["plan_signals"].items() if key != "physical_plan"
        }
        print(json.dumps(summary, indent=2))
        if args.ui_snapshot:
            ui_url = spark.sparkContext.uiWebUrl
            if not ui_url:
                raise RuntimeError("Spark UI URL is unavailable")
            args.ui_snapshot.parent.mkdir(parents=True, exist_ok=True)
            args.ui_snapshot.write_bytes(urlopen(f"{ui_url}/jobs/").read())
        if args.hold_ui_seconds > 0:
            time.sleep(args.hold_ui_seconds)
    finally:
        spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
