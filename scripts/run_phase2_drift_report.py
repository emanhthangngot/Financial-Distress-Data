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

from src.drift.generator import (  # noqa: E402
    apply_drift,
    build_drift_report,
    new_run_id,
    render_drift_report_markdown,
    write_drift_report,
)
from src.drift.generator_config import get_scenario, load_drift_config  # noqa: E402
from src.generator.config import load_generator_config  # noqa: E402
from src.generator.offline import generate_offline_data  # noqa: E402

# Which offline dataset each target_metric is read from — explicit so a third
# metric added to generator_config.DERIVED_METRIC_NAMES fails loudly here
# instead of silently defaulting to the wrong dataset.
_TARGET_METRIC_DATASET = {
    "debt_to_asset": "financial_statements",
    "close_price": "market_prices",
}


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
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / "phase2" / "drift")
    return parser.parse_args()


def run(args: argparse.Namespace) -> tuple[Path, dict]:
    drift_config = load_drift_config(args.drift_config)
    scenario = get_scenario(drift_config, args.scenario)

    generator_config = load_generator_config(args.generator_config, profile=args.profile)
    offline_data = generate_offline_data(generator_config)
    dataset_name = _TARGET_METRIC_DATASET[scenario.target_metric]
    rows = getattr(offline_data, dataset_name)

    drifted = apply_drift(rows, scenario)
    report = build_drift_report(rows, drifted.rows, scenario)
    markdown = render_drift_report_markdown(report)
    directory = write_drift_report(
        report, markdown, run_id=new_run_id(), output_root=args.output_root
    )
    return directory, report


def main() -> int:
    directory, report = run(parse_args())
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
