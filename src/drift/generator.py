"""Deterministic drift injection and before/after reporting.

``apply_drift`` is a pure post-transform over generator output rows: it
consumes ``src.generator.offline.generate_offline_data`` /
``src.generator.streaming.generate_stream_events`` rows as inputs and never
mutates ``src/generator/`` (AGENTS.md: Phase 1 read-only). It uses its own
``random.Random(scenario.seed)`` instance, never the global RNG, so two runs
with the same input and seed are byte-identical.

Scope limitation (slice 4A): ``apply_drift`` shifts only the fields a
scenario names in ``feature_shifts`` and does not co-shift derived/dependent
fields (e.g. shifting ``total_liabilities`` does not adjust ``total_assets``
or ``equity`` to keep the balance-sheet identity, and shifting ``close_price``
does not adjust ``high_price``/``low_price``). Drifted rows are consumed only
by ``build_drift_report`` in this slice — nothing downstream (Gold, Feast)
reads them yet. Co-shifting dependents is deferred to whichever later slice
first writes drifted rows to a store, where the concrete downstream
consistency requirement will be known.
"""

from __future__ import annotations

import json
import math
import random
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.drift.generator_config import DERIVED_METRIC_NAMES, DriftScenario, ShiftSpec

OUTPUT_ROOT = Path("outputs/phase2/drift")

# One resolver per name in generator_config.DERIVED_METRIC_NAMES — kept in
# sync by the assertion below (a name present in one without the other is a
# config bug that should fail at import time, not deep inside a run).
_DERIVED_METRICS: dict[str, Any] = {
    "debt_to_asset": lambda row: (
        row["debt_to_asset"]
        if row.get("debt_to_asset") is not None
        else (row["total_liabilities"] / row["total_assets"] if row.get("total_assets") else None)
    ),
    "close_price": lambda row: row.get("close_price"),
}
assert (
    set(_DERIVED_METRICS) == DERIVED_METRIC_NAMES
), "generator._DERIVED_METRICS and generator_config.DERIVED_METRIC_NAMES drifted apart"


@dataclass(frozen=True)
class DriftedData:
    rows: list[dict[str, Any]]
    affected_tickers: frozenset[str]


def _apply_shift(value: float, shift: ShiftSpec, ramp_fraction: float) -> float:
    magnitude = shift.magnitude * ramp_fraction
    if shift.mode == "multiplicative":
        # A positive magnitude on the selected affected subgroup widens the
        # cross-sectional spread against the untouched unaffected subgroup —
        # this is how market_stress raises close_price's population stdev.
        return value * (1 + magnitude)
    if shift.mode == "additive":
        return value + magnitude
    raise ValueError(
        f"unhandled shift mode {shift.mode!r}"
    )  # unreachable: ShiftSpec.validate() gates this


def _ramp_fraction(row: dict[str, Any], scenario: DriftScenario) -> float:
    """1.0 once a row's fiscal quarter reaches ``start_quarter``; rows with no
    quarter axis (e.g. price snapshots) are treated as already at full ramp
    once their ticker is selected — there is nothing to ramp against."""
    quarter = row.get("fiscal_quarter")
    if quarter is None:
        period = row.get("report_period")
        if not period:
            return 1.0
        try:
            quarter = int(str(period)[-1])
        except ValueError:
            return 1.0
    return 1.0 if quarter >= scenario.start_quarter else 0.0


def apply_drift(rows: list[dict[str, Any]], scenario: DriftScenario) -> DriftedData:
    """Apply ``scenario.feature_shifts`` to a seeded ``affected_fraction`` of
    tickers. Rows for unaffected tickers, and features absent from a row,
    pass through unchanged."""
    rng = random.Random(scenario.seed)
    tickers = sorted({str(row["ticker"]) for row in rows})
    affected_count = round(len(tickers) * scenario.affected_fraction)
    affected_tickers = (
        frozenset(rng.sample(tickers, affected_count)) if affected_count else frozenset()
    )

    drifted: list[dict[str, Any]] = []
    for row in rows:
        new_row = dict(row)
        if str(row["ticker"]) in affected_tickers:
            ramp = _ramp_fraction(row, scenario)
            if ramp > 0:
                for feature, shift in scenario.feature_shifts.items():
                    if feature in new_row and new_row[feature] is not None:
                        new_row[feature] = _apply_shift(float(new_row[feature]), shift, ramp)
        drifted.append(new_row)
    return DriftedData(rows=drifted, affected_tickers=affected_tickers)


def _distribution_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"mean": 0.0, "std": 0.0, "p50": 0.0, "p95": 0.0, "count": 0}
    ordered = sorted(values)
    return {
        "mean": statistics.fmean(values),
        "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "p50": statistics.median(ordered),
        "p95": ordered[min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))],
        "count": len(values),
    }


def _population_stability_index(
    before: list[float], after: list[float], buckets: int = 10
) -> float:
    """Standard fixed-width-bucket PSI over the before/after value sets. 0.0
    when either population is empty (nothing to compare)."""
    if not before or not after:
        return 0.0
    lo, hi = min(before + after), max(before + after)
    if lo == hi:
        return 0.0
    width = (hi - lo) / buckets

    def _bucket_fractions(values: list[float]) -> list[float]:
        counts = [0] * buckets
        for value in values:
            index = min(buckets - 1, max(0, int((value - lo) / width)))
            counts[index] += 1
        floor = 1e-6  # avoid log(0) for an empty bucket
        return [max(count / len(values), floor) for count in counts]

    before_fractions = _bucket_fractions(before)
    after_fractions = _bucket_fractions(after)
    return sum(
        (after_f - before_f) * math.log(after_f / before_f)
        for before_f, after_f in zip(before_fractions, after_fractions, strict=True)
    )


def build_drift_report(
    before: list[dict[str, Any]], after: list[dict[str, Any]], scenario: DriftScenario
) -> dict[str, Any]:
    """Per-population before/after stats, PSI, and a pass/fail verdict
    against ``scenario.expected_direction`` / ``scenario.threshold``."""
    resolver = _DERIVED_METRICS[scenario.target_metric]
    before_values = [v for row in before if (v := resolver(row)) is not None]
    after_values = [v for row in after if (v := resolver(row)) is not None]
    before_stats = _distribution_stats(before_values)
    after_stats = _distribution_stats(after_values)

    observed_before = before_stats[scenario.observed_stat]
    observed_after = after_stats[scenario.observed_stat]
    relative_change = (
        (observed_after - observed_before) / observed_before if observed_before else 0.0
    )
    observed_direction = "increase" if relative_change > 0 else "decrease"
    passed = (
        observed_direction == scenario.expected_direction
        and abs(relative_change) >= scenario.threshold
    )

    return {
        "scenario": scenario.name,
        "seed": scenario.seed,
        "target_metric": scenario.target_metric,
        "observed_stat": scenario.observed_stat,
        "before": before_stats,
        "after": after_stats,
        "relative_change": relative_change,
        "observed_direction": observed_direction,
        "configured_direction": scenario.expected_direction,
        "threshold": scenario.threshold,
        "psi": _population_stability_index(before_values, after_values),
        "passed": passed,
    }


def render_drift_report_markdown(report: dict[str, Any]) -> str:
    """Renders ``build_drift_report``'s output as a Markdown table."""
    before, after = report["before"], report["after"]
    lines = [
        f"# Drift report — {report['scenario']}",
        "",
        f"- seed: `{report['seed']}`",
        f"- target metric: `{report['target_metric']}` "
        f"(observed stat: `{report['observed_stat']}`)",
        f"- configured direction: `{report['configured_direction']}`, "
        f"threshold: `{report['threshold']}`",
        f"- observed direction: `{report['observed_direction']}`, "
        f"relative change: `{report['relative_change']:.4f}`",
        f"- PSI: `{report['psi']:.4f}`",
        f"- **passed: {report['passed']}**",
        "",
        "| stat | before | after |",
        "|---|---:|---:|",
    ]
    for stat in ("count", "mean", "std", "p50", "p95"):
        lines.append(f"| {stat} | {before[stat]:.4f} | {after[stat]:.4f} |")
    lines.append("")
    return "\n".join(lines)


def write_drift_report(
    report: dict[str, Any], markdown: str, run_id: str, output_root: Path = OUTPUT_ROOT
) -> Path:
    """Writes ``report.json`` and ``report.md`` to
    ``outputs/phase2/drift/{scenario}/{run_id}/``; returns the directory."""
    directory = output_root / report["scenario"] / run_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (directory / "report.md").write_text(markdown, encoding="utf-8")
    return directory


def new_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


# Which offline dataset each target_metric is read from — explicit so a
# third metric added to generator_config.DERIVED_METRIC_NAMES fails loudly
# here instead of silently defaulting to the wrong dataset.
_TARGET_METRIC_DATASET = {
    "debt_to_asset": "financial_statements",
    "close_price": "market_prices",
}


def run_scenario_against_generator(
    scenario_name: str,
    drift_config_path: Path,
    generator_config_path: Path,
    profile: str = "ci",
    output_root: Path = OUTPUT_ROOT,
) -> tuple[Path, dict[str, Any]]:
    """Generate deterministic offline data, apply the named drift scenario,
    write the before/after report. The single orchestrator both
    scripts/run_phase2_drift_report.py (CLI evidence command) and
    dags/phase2/phase2_label_drift_build.py (Airflow wrapper) call — kept
    here rather than in scripts/ because dags/ containers mount src/ and
    configs/ but not scripts/ (docker-compose.yml's airflow-* volumes)."""
    from src.drift.generator_config import get_scenario, load_drift_config
    from src.generator.config import load_generator_config
    from src.generator.offline import generate_offline_data

    drift_config = load_drift_config(drift_config_path)
    scenario = get_scenario(drift_config, scenario_name)

    generator_config = load_generator_config(generator_config_path, profile=profile)
    offline_data = generate_offline_data(generator_config)
    dataset_name = _TARGET_METRIC_DATASET[scenario.target_metric]
    rows = getattr(offline_data, dataset_name)

    drifted = apply_drift(rows, scenario)
    report = build_drift_report(rows, drifted.rows, scenario)
    markdown = render_drift_report_markdown(report)
    directory = write_drift_report(report, markdown, run_id=new_run_id(), output_root=output_root)
    return directory, report
