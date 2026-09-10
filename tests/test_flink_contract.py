"""Code-level contract tests for src/streaming/flink_contract.py (phase-05-cdc-streaming.md,
mini-20..24). Exercises the deterministic oracle the Flink job's Table API pipeline mirrors:
window bucketing, watermark/allowed-lateness classification, and optimized-mode
deduplication — the parts of AC-P5-9..13 verifiable without a live Flink cluster."""

from __future__ import annotations

import pytest

from src.streaming.flink_contract import (
    FlinkStreamingConfig,
    FlinkVariantConfig,
    load_flink_streaming_config,
    price_event_error,
    process_bounded_events,
)


def _event(event_id: str, ticker: str, ts: str, price: float = 10.0, volume: int = 100) -> dict:
    return {
        "event_id": event_id,
        "event_type": "trade",
        "ticker": ticker,
        "event_timestamp": ts,
        "price": price,
        "volume": volume,
    }


def test_load_flink_streaming_config_reads_the_real_deployment_yaml() -> None:
    config = load_flink_streaming_config("configs/flink-streaming.yaml")
    assert config.window_seconds == 10
    assert config.max_out_of_orderness_seconds == 120
    assert config.allowed_lateness_seconds == 180
    assert config.baseline.deduplicate is False
    assert config.optimized.deduplicate is True


def test_config_rejects_non_positive_parallelism() -> None:
    with pytest.raises(ValueError, match="parallelism must be positive"):
        FlinkVariantConfig(parallelism=0, checkpointing=False, deduplicate=False).validate(
            "baseline"
        )


def test_config_rejects_negative_window_seconds() -> None:
    with pytest.raises(ValueError, match="window_seconds"):
        FlinkStreamingConfig.fixture(window_seconds=0)


def test_price_event_error_flags_missing_and_malformed_fields() -> None:
    assert price_event_error(_event("e1", "VNM", "2026-01-01T00:00:00Z")) is None
    assert "missing required event fields" in price_event_error(
        {"event_id": "e1", "event_type": "trade", "ticker": "VNM"}
    )
    assert "invalid type" in price_event_error(
        _event("e1", "VNM", "2026-01-01T00:00:00Z", price="not-a-number")
    )


def test_window_processing_buckets_by_ticker_and_tumbling_window() -> None:
    config = FlinkStreamingConfig.fixture(window_seconds=10)
    events = [
        _event("e1", "VNM", "2026-01-01T00:00:01Z", price=10.0, volume=100),
        _event("e2", "VNM", "2026-01-01T00:00:05Z", price=20.0, volume=200),
        _event("e3", "VNM", "2026-01-01T00:00:15Z", price=30.0, volume=300),
    ]
    result = process_bounded_events(events, config, optimized=False)
    assert result["counts"]["window_results"] == 2
    first_window = next(w for w in result["windows"] if w["event_count"] == 2)
    assert first_window["average_price"] == 15.0
    assert first_window["total_volume"] == 300


def test_optimized_mode_deduplicates_repeated_event_ids() -> None:
    config = FlinkStreamingConfig.fixture()
    events = [
        _event("e1", "VNM", "2026-01-01T00:00:01Z"),
        _event("e1", "VNM", "2026-01-01T00:00:01Z"),
    ]
    baseline = process_bounded_events(events, config, optimized=False)
    optimized = process_bounded_events(events, config, optimized=True)
    assert baseline["counts"]["duplicates"] == 0
    assert baseline["counts"]["valid"] == 2
    assert optimized["counts"]["duplicates"] == 1
    assert optimized["counts"]["valid"] == 1


def test_late_arrival_within_allowed_lateness_is_accepted_beyond_it_is_dropped() -> None:
    config = FlinkStreamingConfig.fixture(
        max_out_of_orderness_seconds=10, allowed_lateness_seconds=30
    )
    events = [
        _event("e1", "VNM", "2026-01-01T00:01:00Z"),
        # 25s behind the watermark (60 - 10 = 50s cutoff): within the 30s allowance.
        _event("e2", "VNM", "2026-01-01T00:00:25Z"),
        # 55s behind the watermark: exceeds the 30s allowance.
        _event("e3", "VNM", "2026-01-01T00:29:55Z"),
        _event("e4", "VNM", "2026-01-01T00:00:00Z"),
    ]
    result = process_bounded_events(events, config, optimized=False)
    assert result["counts"]["allowed_late"] == 1
    assert result["counts"]["too_late"] == 1
    assert result["too_late"][0]["event_id"] == "e4"


def test_invalid_events_are_excluded_from_windows_and_counted() -> None:
    config = FlinkStreamingConfig.fixture()
    events = [
        _event("e1", "VNM", "2026-01-01T00:00:01Z"),
        {"event_id": "bad", "event_type": "trade", "ticker": "VNM"},
    ]
    result = process_bounded_events(events, config, optimized=False)
    assert result["counts"]["invalid"] == 1
    assert result["counts"]["valid"] == 1
    assert result["counts"]["window_results"] == 1
