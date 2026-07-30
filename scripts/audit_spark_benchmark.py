#!/usr/bin/env python3
"""Audit Spark baseline/optimized correctness and summarize measured changes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.jobs.spark_benchmark_common import assert_equivalent_reports  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--optimized", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def _ratio(before: float, after: float) -> float | None:
    return round(before / after, 4) if after else None


def main() -> int:
    args = parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    optimized = json.loads(args.optimized.read_text(encoding="utf-8"))
    assert_equivalent_reports(baseline, optimized)
    report = {
        "status": "pass",
        "run_id": baseline["run_id"],
        "input_digest": baseline["input_digest"],
        "output_digest": baseline["output_digest"],
        "output_rows": baseline["output_rows"],
        "runtime": {
            "baseline_median_seconds": baseline["duration"]["median_seconds"],
            "optimized_median_seconds": optimized["duration"]["median_seconds"],
            "baseline_over_optimized_ratio": _ratio(
                baseline["duration"]["median_seconds"],
                optimized["duration"]["median_seconds"],
            ),
        },
        "plan_signals": {
            "baseline": {
                key: value
                for key, value in baseline["plan_signals"].items()
                if key != "physical_plan"
            },
            "optimized": {
                key: value
                for key, value in optimized["plan_signals"].items()
                if key != "physical_plan"
            },
        },
    }
    if "storage" in baseline and "storage" in optimized:
        report["storage"] = {
            "baseline_file_count": baseline["storage"]["file_count"],
            "optimized_file_count": optimized["storage"]["file_count"],
            "file_count_reduction": baseline["storage"]["file_count"]
            - optimized["storage"]["file_count"],
            "baseline_read_seconds": baseline["storage"]["filtered_read_seconds"],
            "optimized_read_seconds": optimized["storage"]["filtered_read_seconds"],
            "read_speed_ratio": _ratio(
                baseline["storage"]["filtered_read_seconds"],
                optimized["storage"]["filtered_read_seconds"],
            ),
        }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
