from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.streaming.flink_contract import (
    FlinkStreamingConfig,
    load_flink_streaming_config,
    process_bounded_events,
)

CONFIG = Path("configs/flink-streaming.yaml")


def _event(event_id: str, event_second: int, ingest_second: int, *, ticker: str = "AAA"):
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return {
        "event_id": event_id,
        "event_type": "price_update",
        "ticker": ticker,
        "event_timestamp": (start + timedelta(seconds=event_second)).isoformat(),
        "ingest_timestamp": (start + timedelta(seconds=ingest_second)).isoformat(),
        "price": 10.0,
        "volume": 100,
    }


def test_flink_config_is_pinned_and_validated(tmp_path: Path):
    config = load_flink_streaming_config(CONFIG)

    assert config.flink_version == "1.20.3"
    assert config.optimized.parallelism == 4
    assert config.optimized.checkpointing is True
    assert config.optimized.deduplicate is True

    raw = json.loads(json.dumps(config.to_dict()))
    raw["window_seconds"] = 0
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="window_seconds"):
        load_flink_streaming_config(invalid)


def test_bounded_processor_proves_on_time_allowed_late_too_late_and_duplicate():
    config = FlinkStreamingConfig.fixture(
        max_out_of_orderness_seconds=2,
        allowed_lateness_seconds=3,
        window_seconds=10,
    )
    events = [
        _event("on-time", 10, 10),
        _event("advance-watermark", 20, 20),
        _event("allowed-late", 17, 21),
        _event("too-late", 10, 22),
        _event("on-time", 10, 23),
    ]

    report = process_bounded_events(events, config, optimized=True)

    assert report["counts"] == {
        "input": 5,
        "valid": 4,
        "invalid": 0,
        "duplicates": 1,
        "allowed_late": 1,
        "too_late": 1,
        "window_results": 2,
    }
    assert [row["event_id"] for row in report["too_late"]] == ["too-late"]
    assert report["windows"][0]["window_start"] == "2026-01-01T00:00:10+00:00"


def test_baseline_preserves_duplicates_while_optimized_removes_them():
    config = FlinkStreamingConfig.fixture(max_out_of_orderness_seconds=5)
    events = [_event("same", 1, 1), _event("same", 1, 2)]

    baseline = process_bounded_events(events, config, optimized=False)
    optimized = process_bounded_events(events, config, optimized=True)

    assert baseline["counts"]["valid"] == 2
    assert baseline["counts"]["duplicates"] == 0
    assert optimized["counts"]["valid"] == 1
    assert optimized["counts"]["duplicates"] == 1


def test_invalid_price_event_types_are_routed_instead_of_crashing():
    config = FlinkStreamingConfig.fixture()
    missing_event_type = _event("missing-type", 1, 1)
    missing_event_type.pop("event_type")
    invalid_timestamp = _event("bad-time", 2, 2)
    invalid_timestamp["event_timestamp"] = "not-a-timestamp"

    report = process_bounded_events([missing_event_type, invalid_timestamp], config, optimized=True)

    assert report["counts"]["invalid"] == 2
    assert report["counts"]["valid"] == 0


def test_window_output_has_explicit_ticker_and_event_time_grain():
    config = FlinkStreamingConfig.fixture(window_seconds=10)
    events = [_event("a", 1, 1), _event("b", 2, 2), _event("c", 2, 2, ticker="BBB")]

    report = process_bounded_events(events, config, optimized=True)

    assert report["windows"] == [
        {
            "ticker": "AAA",
            "window_start": "2026-01-01T00:00:00+00:00",
            "window_end": "2026-01-01T00:00:10+00:00",
            "event_count": 2,
            "average_price": 10.0,
            "total_volume": 200,
        },
        {
            "ticker": "BBB",
            "window_start": "2026-01-01T00:00:00+00:00",
            "window_end": "2026-01-01T00:00:10+00:00",
            "event_count": 1,
            "average_price": 10.0,
            "total_volume": 100,
        },
    ]


def test_runtime_artifacts_expose_kafka_watermark_state_window_and_checkpoint_contracts():
    job = Path("flink/jobs/price_event_job.py").read_text(encoding="utf-8")
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "KafkaSource.builder" in job
    assert "WatermarkStrategy.for_bounded_out_of_orderness" in job
    assert "ValueStateDescriptor" in job
    assert "TumblingEventTimeWindows.of" in job
    assert "OutputTag" in job
    assert "enable_checkpointing" in job
    assert "flink-jobmanager" in compose
    assert "flink-taskmanager" in compose


def test_benchmark_runner_records_repeated_protocol_and_truth_counts(tmp_path: Path):
    from scripts.run_flink_benchmark import main

    output = tmp_path / "optimized.json"
    import sys

    original = sys.argv
    sys.argv = [
        "run_flink_benchmark.py",
        "--variant",
        "optimized",
        "--profile",
        "ci",
        "--runs",
        "2",
        "--warmups",
        "0",
        "--output",
        str(output),
    ]
    try:
        assert main() == 0
    finally:
        sys.argv = original

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["input_events"] == 200
    assert report["protocol"]["runs"] == 2
    assert report["counts"]["duplicates"] > 0
    assert report["duration"]["events_per_second"] > 0


def test_checked_in_flink_evidence_passes_correlated_audit():
    from scripts.audit_flink_evidence import audit

    report = audit(Path("docs/evidence/flink"))

    assert report["status"] == "pass"
    assert all(report["checks"].values())
    assert report["metrics"]["runtime_duplicates_removed"] == 959
    assert report["metrics"]["restart_completed_checkpoints"] >= 1
