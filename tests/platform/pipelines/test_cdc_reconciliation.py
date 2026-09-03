from __future__ import annotations

import pytest

from src.cdc.config import CDCConfig, CDCConfigError
from src.cdc.flink_cdc_job import build_job_spec, normalize_change
from src.cdc.reconcile import reconcile_paths, run_reconciliation_task


def test_cdc_config_is_connector_and_sink_contract() -> None:
    config = CDCConfig.from_mapping(
        {
            "host": "postgres",
            "port": "5433",
            "table_include_list": "public.events,public.labels",
        }
    )
    props = config.connector_properties()
    assert props["connector"] == "postgres-cdc"
    assert props["slot.name"] == config.slot_name
    assert props["table-names"] == "public.events,public.labels"
    assert build_job_spec(config).sink["catalog-type"] == "rest"


def test_cdc_config_rejects_non_logical_replication() -> None:
    try:
        CDCConfig().validate_logical_replication("replica")
    except CDCConfigError as exc:
        assert "wal_level" in str(exc)
    else:  # pragma: no cover - assertion style keeps exception type explicit
        raise AssertionError("non-logical WAL must be rejected")


def test_reconciliation_reports_matching_keys_and_window() -> None:
    generator = [
        {"business_key": "a", "event_timestamp": "2026-01-01T00:00:00Z"},
        {"business_key": "b", "event_timestamp": "2026-01-01T00:00:01Z"},
        {"business_key": "outside", "event_timestamp": "2025-01-01T00:00:00Z"},
    ]
    cdc = [dict(row) for row in generator[:2]]
    report = reconcile_paths(
        generator,
        cdc,
        start_ts="2026-01-01T00:00:00Z",
        end_ts="2026-01-01T00:00:05Z",
    )
    assert report.matched
    assert report["generator_count"] == report["cdc_count"] == 2


def test_reconciliation_identifies_path_only_keys_and_duplicates() -> None:
    report = reconcile_paths(
        [{"business_key": "a"}, {"business_key": "a"}],
        [{"business_key": "b"}],
    )
    assert report.status == "mismatch"
    assert report.generator_only == frozenset({("a",)})
    assert report.cdc_only == frozenset({("b",)})
    assert report.duplicate_generator_keys == frozenset({("a",)})


def test_debezium_change_normalization_preserves_delete_key() -> None:
    row = normalize_change({"op": "d", "before": {"business_key": "a"}, "ts_ms": 1})
    assert row["business_key"] == "a"
    assert row["_cdc_operation"] == "delete"
    assert row["_cdc_source_ts_ms"] == 1


def test_reconciliation_task_rejects_missing_or_empty_inputs() -> None:
    with pytest.raises(RuntimeError, match="requires injected"):
        run_reconciliation_task()
    with pytest.raises(RuntimeError, match="input rows are empty"):
        run_reconciliation_task(generator_rows=[], cdc_rows=[])
