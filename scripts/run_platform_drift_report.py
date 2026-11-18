#!/usr/bin/env python3
"""Generate deterministic offline data, apply a configured drift scenario,
and write the before/after report — the evidence command for the two
"data-generator drift/config" LLM rubric rows."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.drift.generator import run_scenario_against_generator  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario", required=True, help="scenario name in configs/drift-config.yaml"
    )
    parser.add_argument("--drift-config", type=Path, default=ROOT / "configs" / "drift-config.yaml")
    parser.add_argument(
        "--generator-config", type=Path, default=ROOT / "configs" / "generator-config.yaml"
    )
    parser.add_argument("--profile", default="ci", help="generator config profile to load")
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / "evidence" / "drift")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    directory, report = run_scenario_against_generator(
        args.scenario,
        args.drift_config,
        args.generator_config,
        profile=args.profile,
        output_root=args.output_root,
    )
    print(f"wrote {directory / 'report.json'} and {directory / 'report.md'}")
    if not report["passed"]:
        print(
            f"drift assertion failed: observed_direction={report['observed_direction']!r} "
            f"relative_change={report['relative_change']:.4f} threshold={report['threshold']}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
