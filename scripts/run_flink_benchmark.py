#!/usr/bin/env python3
"""Benchmark the finite Stage 5 replay contract for baseline or optimized semantics."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.generator.config import load_generator_config  # noqa: E402
from src.generator.streaming import generate_stream_events  # noqa: E402
from src.streaming.flink_contract import (  # noqa: E402
    load_flink_streaming_config,
    process_bounded_events,
)


def _digest(rows: list[dict]) -> str:
    payload = "\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows)
    return hashlib.sha256(payload.encode()).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("baseline", "optimized"), required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/flink-streaming.yaml"))
    parser.add_argument(
        "--generator-config",
        type=Path,
        default=Path("configs/generator-config.yaml"),
    )
    parser.add_argument("--profile", default="evidence")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.runs <= 0 or args.warmups < 0:
        raise ValueError("runs must be positive and warmups non-negative")
    config = load_flink_streaming_config(args.config)
    generator_config = load_generator_config(args.generator_config, profile=args.profile)
    events = generate_stream_events(generator_config)
    optimized = args.variant == "optimized"
    for _ in range(args.warmups):
        process_bounded_events(events, config, optimized=optimized)
    durations = []
    result = {}
    for _ in range(args.runs):
        started = time.perf_counter()
        result = process_bounded_events(events, config, optimized=optimized)
        durations.append(time.perf_counter() - started)
    settings = getattr(config, args.variant)
    report = {
        "schema_version": 1,
        "status": "pass",
        "run_id": config.run_id,
        "variant": args.variant,
        "input_events": len(events),
        "input_digest": _digest(events),
        "counts": result["counts"],
        "window_digest": _digest(result["windows"]),
        "protocol": {
            "runs": args.runs,
            "warmups": args.warmups,
            "parallelism": settings.parallelism,
            "checkpointing": settings.checkpointing,
            "deduplicate": settings.deduplicate,
            "window_seconds": config.window_seconds,
            "max_out_of_orderness_seconds": config.max_out_of_orderness_seconds,
            "allowed_lateness_seconds": config.allowed_lateness_seconds,
            "dedup_ttl_seconds": config.dedup_ttl_seconds,
        },
        "duration": {
            "runs_seconds": [round(value, 6) for value in durations],
            "median_seconds": round(median(durations), 6),
            "events_per_second": round(len(events) / median(durations), 2),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
