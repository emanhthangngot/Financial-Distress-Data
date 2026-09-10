"""Generator restatement vintages (phase-04-data-plane.md, mini novel idea 2 / P4).

The offline generator must emit multiple vintages per (ticker, report_period)
with realistic revision magnitude and lag, so the restatement-leakage guard
(ADR-017, src/ml/leakage_guard.py) has real multi-vintage data to guard
against — this is the "restatement" half of the two-idea novel pair the
owning_phase table assigns: PIT restatement (P2, already implemented and
tested in tests/test_restatement_leakage.py) and generator restatement (P4,
this file).
"""

from __future__ import annotations

from dataclasses import replace

from src.generator.config import GeneratorConfig, OfflineConfig, OutputConfig, StreamingConfig
from src.generator.offline import generate_offline_data


def _config(**offline_overrides) -> GeneratorConfig:
    offline = OfflineConfig(
        companies=5,
        high_cardinality_ids=5,
        quarters=4,
        dominant_sector="Technology",
        dominant_sector_rate=0.5,
        dominant_exchange="HOSE",
        dominant_exchange_rate=0.5,
        duplicate_rate=0.0,
        schema_change_quarter=3,
        **offline_overrides,
    )
    streaming = StreamingConfig(
        events=10,
        window_seconds=10,
        baseline_events_per_window=1,
        burst_window=2,
        burst_multiplier=2,
        late_rate=0.0,
        duplicate_rate=0.0,
        out_of_order_rate=0.0,
        max_lateness_seconds=60,
        max_out_of_order_seconds=30,
    )
    output = OutputConfig(
        root="unused",
        format="jsonl",
        minio_bucket="x",
        minio_prefix="y",
        kafka_bootstrap_servers="kafka:9092",
    )
    return GeneratorConfig(
        schema_version=1, seed=7, run_id="test", offline=offline, streaming=streaming, output=output
    )


def test_zero_restatement_rate_emits_exactly_one_vintage_per_period() -> None:
    config = _config(restatement_rate=0.0)
    data = generate_offline_data(config)

    keys = [(row["ticker"], row["report_period"]) for row in data.financial_statements]
    assert len(keys) == len(
        set(keys)
    ), "no restatements requested, every (ticker, period) must be unique"
    assert all(row["is_latest_vintage"] for row in data.financial_statements)


def test_positive_restatement_rate_emits_multiple_vintages() -> None:
    config = _config(restatement_rate=0.99, restatement_lag_days=180, restatement_magnitude=0.2)
    data = generate_offline_data(config)

    total_periods = config.offline.companies * config.offline.quarters
    restated_periods = len(data.financial_statements) - total_periods
    assert restated_periods > 0, "restatement_rate=0.99 must produce at least one restated vintage"


def test_restated_vintage_has_later_known_from_ts_and_is_latest() -> None:
    config = _config(restatement_rate=0.99, restatement_lag_days=90)
    data = generate_offline_data(config)

    by_key: dict[tuple[str, str], list[dict]] = {}
    for row in data.financial_statements:
        by_key.setdefault((row["ticker"], row["report_period"]), []).append(row)

    restated_pairs = [rows for rows in by_key.values() if len(rows) == 2]
    assert restated_pairs, "expected at least one restated (ticker, report_period) pair"
    for rows in restated_pairs:
        original = next(r for r in rows if not r["is_latest_vintage"])
        restated = next(r for r in rows if r["is_latest_vintage"])
        assert restated["known_from_ts"] > original["known_from_ts"]
        assert restated["total_assets"] != original["total_assets"]
        # Balance sheet identity holds exactly for both vintages.
        assert original["total_assets"] == original["total_liabilities"] + original["equity"]
        assert restated["total_assets"] == restated["total_liabilities"] + restated["equity"]


def test_restatement_is_deterministic_for_a_fixed_seed() -> None:
    config = _config(restatement_rate=0.5, restatement_lag_days=120)
    first = generate_offline_data(config)
    second = generate_offline_data(replace(config, seed=config.seed))

    assert first.financial_statements == second.financial_statements


def test_offline_config_rejects_out_of_range_restatement_rate() -> None:
    config = _config(restatement_rate=1.5)
    try:
        config.offline.validate()
        raised = False
    except ValueError:
        raised = True
    assert raised, "restatement_rate must be validated like every other rate field"
