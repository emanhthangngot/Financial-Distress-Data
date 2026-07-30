from __future__ import annotations

import importlib
import inspect
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.metadata.metadata_writer import MetadataWriter
from src.metadata.schema_registry import InMemorySchemaRegistry
from src.quality.dq_checks import check_freshness, check_referential_integrity
from src.streaming.events import StreamEvent
from src.transforms.bronze_to_silver import bronze_to_silver
from src.transforms.compute_distress_labels import compute_distress_label
from src.transforms.silver_to_gold import build_fact_market_alert, build_fact_news_sentiment


def _atomic_publisher_class():
    return importlib.import_module("src.io.atomic_publish").AtomicDirectoryPublisher


def _merge_dim_company(existing, snapshots):
    module = importlib.import_module("src.transforms.gold.dim_company")
    return module.merge_dim_company(existing, snapshots)


def test_schema_registry_is_loaded_from_typed_config():
    contract = InMemorySchemaRegistry.from_yaml("configs/schema-contracts.yaml").get_current(
        "market_prices_daily"
    )

    assert contract.field_types["close_price"] == "float"
    assert contract.field_types["created_ts"] == "timestamp"
    assert contract.blank_as_null is True


def test_typed_silver_normalizes_blanks_and_quarantines_invalid_values():
    contract = InMemorySchemaRegistry.from_yaml("configs/schema-contracts.yaml").get_current(
        "market_prices_daily"
    )
    rows = [
        {
            "ticker": " AAA ",
            "trading_date": "2026-01-02",
            "close_price": "10.5",
            "volume": "100",
            "created_ts": "2026-01-02T09:00:00Z",
            "market_cap": " ",
        },
        {
            "ticker": "BBB",
            "trading_date": "not-a-date",
            "close_price": "unknown",
            "volume": "100",
            "created_ts": "bad-time",
        },
    ]

    silver, failed = bronze_to_silver(
        rows,
        contract.required,
        contract.nullable,
        ["ticker", "trading_date"],
        field_types=contract.field_types,
        enum_values=contract.enum_values,
        blank_as_null=contract.blank_as_null,
        run_id="run-typed",
    )

    assert silver[0]["ticker"] == "AAA"
    assert silver[0]["close_price"] == 10.5
    assert silver[0]["volume"] == 100
    assert silver[0]["market_cap"] is None
    assert failed[0]["run_id"] == "run-typed"
    assert "invalid" in failed[0]["failure_reason"]


def test_dedup_compares_timezone_aware_timestamps_and_rejects_invalid_timestamp():
    contract = InMemorySchemaRegistry.from_yaml("configs/schema-contracts.yaml").get_current(
        "companies"
    )
    rows = [
        {
            "ticker": "AAA",
            "company_name": "old",
            "exchange": "HOSE",
            "created_ts": "2026-01-01T10:00:00+07:00",
        },
        {
            "ticker": "AAA",
            "company_name": "new",
            "exchange": "HOSE",
            "created_ts": "2026-01-01T04:00:00Z",
        },
        {
            "ticker": "BBB",
            "company_name": "bad",
            "exchange": "HOSE",
            "created_ts": "yesterday-ish",
        },
    ]

    silver, failed = bronze_to_silver(
        rows,
        contract.required,
        contract.nullable,
        ["ticker"],
        field_types=contract.field_types,
    )

    assert [row["company_name"] for row in silver] == ["new"]
    assert len(failed) == 1
    assert "created_ts" in failed[0]["failure_reason"]


def test_scd2_merge_preserves_history_across_runs_and_ignores_no_change():
    first = _merge_dim_company(
        [],
        [
            {
                "ticker": "AAA",
                "company_name": "Alpha",
                "exchange": "HOSE",
                "industry": None,
                "sector": "Industrial",
                "created_ts": "2026-01-01T00:00:00Z",
            }
        ],
    )
    unchanged = _merge_dim_company(
        first,
        [{**first[0], "created_ts": "2026-02-01T00:00:00Z"}],
    )
    changed = _merge_dim_company(
        unchanged,
        [{**first[0], "industry": "Manufacturing", "created_ts": "2026-03-01T00:00:00Z"}],
    )

    assert len(unchanged) == 1
    assert len(changed) == 2
    assert changed[0]["valid_to_ts"] == "2026-03-01T00:00:00+00:00"
    assert changed[0]["is_current"] is False
    assert changed[1]["is_current"] is True
    assert changed[0]["company_version_key"] != changed[1]["company_version_key"]


@pytest.mark.parametrize("builder", [build_fact_market_alert, build_fact_news_sentiment])
def test_event_fact_dedup_keeps_latest_created_version(builder):
    base = {
        "event_id": "event-1",
        "ticker": "AAA",
        "event_timestamp": "2026-01-02T09:00:00Z",
        "created_ts": "2026-01-02T09:01:00Z",
        "alert_type": "old",
        "sentiment_score": -0.2,
        "risk_keyword_flag": False,
        "severity_score": 0.2,
    }
    facts = builder([base, {**base, "created_ts": "2026-01-02T09:02:00Z", "alert_type": "new"}])

    assert len(facts) == 1
    assert facts[0]["created_ts"] == "2026-01-02T09:02:00Z"


def test_all_stream_event_types_have_deterministic_ids():
    values = ("AAA", "2026-01-01T09:00:00Z", "2026-01-01T09:00:01Z", "price_drop")

    assert StreamEvent.alert(*values).event_id == StreamEvent.alert(*values).event_id


def test_sector_exclusion_is_loaded_from_yaml():
    module = importlib.import_module("src.transforms.compute_distress_labels")
    policy = module.load_sector_exclusion("configs/sector_exclusion.yaml")
    label = compute_distress_label(
        {
            "ticker": "AAA",
            "report_period": "2026Q1",
            "sector": "Banks",
            "created_ts": "2026-04-01T00:00:00Z",
        },
        sector_exclusion=policy,
    )

    assert label.distress_reason == "financial_sector_excluded"
    assert "banks" in policy.terms


def test_failed_rows_can_be_persisted_with_run_lineage():
    writer = MetadataWriter()
    writer.log_failed_records(
        "companies",
        [{"failure_reason": "invalid ticker", "raw_payload": {"ticker": ""}}],
        run_id="run-rejected",
    )

    assert writer.failed_records[0]["run_id"] == "run-rejected"
    assert writer.failed_records[0]["raw_payload"] == {"ticker": ""}


def test_null_foreign_key_is_reported_as_referential_integrity_failure():
    result = check_referential_integrity(
        [{"company_key": None}], {None, "known"}, "facts", "company_key"
    )

    assert result.status == "fail"
    assert result.metric_value == 1.0


def test_future_event_timestamp_is_a_freshness_failure():
    result = check_freshness(
        [{"event_timestamp": "2026-01-01T02:00:00Z"}],
        "events",
        reference_timestamp="2026-01-01T01:00:00Z",
        sla_minutes=60,
    )

    assert result.status == "fail"
    assert result.metric_value == -60.0


def test_atomic_publication_preserves_previous_snapshot_when_validation_fails(tmp_path: Path):
    published = tmp_path / "published"
    published.mkdir()
    (published / "data.txt").write_text("old", encoding="utf-8")
    publisher = _atomic_publisher_class()(published)

    with pytest.raises(RuntimeError, match="DQ failed"):
        publisher.publish(
            "run-2",
            lambda staging: (staging / "data.txt").write_text("new", encoding="utf-8"),
            lambda _staging: (_ for _ in ()).throw(RuntimeError("DQ failed")),
        )

    assert (published / "data.txt").read_text(encoding="utf-8") == "old"


def test_atomic_publication_promotes_validated_snapshot(tmp_path: Path):
    published = tmp_path / "published"
    published.mkdir()
    (published / "data.txt").write_text("old", encoding="utf-8")
    publisher = _atomic_publisher_class()(published)

    publisher.publish(
        "run-2",
        lambda staging: (staging / "data.txt").write_text("new", encoding="utf-8"),
        lambda staging: (staging / "data.txt").is_file(),
    )

    assert (published / "data.txt").read_text(encoding="utf-8") == "new"
    assert publisher.current_run_id == "run-2"


def test_timestamp_types_are_utc_aware_after_validation():
    contract = InMemorySchemaRegistry.from_yaml("configs/schema-contracts.yaml").get_current(
        "companies"
    )
    row = contract.validate_row(
        {
            "ticker": "AAA",
            "company_name": "Alpha",
            "exchange": "HOSE",
            "created_ts": "2026-01-01T07:00:00+07:00",
        }
    )

    assert row["created_ts"] == datetime(2026, 1, 1, tzinfo=UTC)


def test_optional_input_returns_typed_empty_value_only_when_path_is_missing():
    module = importlib.import_module("src.io.optional_input")

    assert module.read_optional(lambda: (_ for _ in ()).throw(FileNotFoundError()), list) == []


def test_optional_input_propagates_corrupt_input():
    module = importlib.import_module("src.io.optional_input")

    with pytest.raises(ValueError, match="corrupt parquet"):
        module.read_optional(
            lambda: (_ for _ in ()).throw(ValueError("corrupt parquet")),
            list,
        )


def test_company_sector_is_joined_before_distress_labeling():
    module = importlib.import_module("src.transforms.compute_distress_labels")
    financial = [{"ticker": "AAA", "report_period": "2026Q1", "created_ts": "2026-04-01T00:00:00Z"}]
    companies = [
        {
            "ticker": "AAA",
            "sector": "Banks",
            "industry": "Banking",
            "created_ts": "2026-01-01T00:00:00Z",
        }
    ]

    labels = module.compute_labels(financial, company_rows=companies)

    assert labels[0]["distress_reason"] == "financial_sector_excluded"


def test_feature_rows_include_event_and_creation_timestamps():
    module = importlib.import_module("src.transforms.features.pit")
    row = module.build_feat_company_market_30d(
        [
            {
                "ticker": "AAA",
                "trading_date": "2026-01-01",
                "created_ts": "2026-01-01T01:00:00Z",
            }
        ]
    )[0]

    assert row["event_timestamp"] == "2026-01-01"
    assert row["created_ts"] == "2026-01-01T01:00:00Z"


def test_dq_rule_config_has_typed_executable_rules():
    module = importlib.import_module("src.quality.rule_config")
    rules = module.load_dq_rule_config("configs/dq_rules.yaml")

    assert rules["critical"][0].type == "schema"
    assert all(
        rule.severity in {"critical", "warning"} for group in rules.values() for rule in group
    )


def test_spark_runtime_uses_typed_schema_and_optional_input_policy():
    module = importlib.import_module("src.jobs.stage1_spark_lakehouse_job")
    source = inspect.getsource(module.run_stage1_spark_lakehouse)

    assert "InMemorySchemaRegistry.from_yaml" in source
    assert "read_optional" in source
    assert "except Exception" not in source


def test_spark_silver_contract_accepts_typed_fields():
    module = importlib.import_module("src.transforms.silver.spark")
    parameters = inspect.signature(module.bronze_to_silver_spark).parameters

    assert "field_types" in parameters
    assert "enum_values" in parameters


def test_spark_feature_contract_preserves_created_timestamp():
    module = importlib.import_module("src.jobs.stage1_spark_lakehouse_job")

    for function in (
        module.build_feat_company_financial_4q_spark,
        module.build_feat_company_market_30d_spark,
        module.build_feat_company_news_30d_spark,
    ):
        assert '"created_ts"' in inspect.getsource(function)


def test_spark_scd2_accepts_existing_history_and_runtime_reads_it():
    module = importlib.import_module("src.jobs.stage1_spark_lakehouse_job")

    assert "existing_dim_company_df" in inspect.signature(module.build_dim_company_spark).parameters
    source = inspect.getsource(module.run_stage1_spark_lakehouse)
    assert "gold/dim_company/" in source
    assert "existing_dim_company_df" in source


def test_spark_runtime_stages_then_promotes_and_persists_rejections():
    module = importlib.import_module("src.jobs.stage1_spark_lakehouse_job")
    source = inspect.getsource(module.run_stage1_spark_lakehouse)

    assert 'output_root = f"_staging/{run_id}/"' in source
    assert "persist_failed_rows" in source
    assert "validate_publication_counts" in source
    assert "promote_staged_prefixes" in source


def test_spark_label_policy_is_loaded_from_sector_config():
    module = importlib.import_module("src.jobs.stage1_spark_lakehouse_job")
    source = inspect.getsource(module.run_stage1_spark_lakehouse)

    assert "load_sector_exclusion" in source
    assert "sector_exclusion=" in source


def test_spark_runtime_validates_configured_dq_rules():
    module = importlib.import_module("src.jobs.stage1_spark_lakehouse_job")
    source = inspect.getsource(module.run_stage1_spark_lakehouse)

    assert "load_dq_rule_config" in source


def test_python_evidence_pipeline_uses_same_typed_schema_config():
    module = importlib.import_module("src.jobs.stage1_evidence_job")

    assert "InMemorySchemaRegistry.from_yaml" in inspect.getsource(module._silver_dataset)


def test_spark_union_aligns_missing_nullable_columns_before_select():
    module = importlib.import_module("src.jobs.stage1_spark_lakehouse_job")
    source = inspect.getsource(module.run_stage1_spark_lakehouse)

    assert "_align_spark_columns(" in source
    assert "batch_prices_df, cols, prices_contract.field_types" in source


def test_spark_news_fact_deduplicates_latest_event_version():
    module = importlib.import_module("src.jobs.stage1_spark_lakehouse_job")
    source = inspect.getsource(module.build_fact_news_sentiment_spark)

    assert 'Window.partitionBy("event_id")' in source
    assert "desc_nulls_last" in source


def test_runtime_freshness_does_not_use_stale_fixture_reference():
    module = importlib.import_module("src.jobs.stage1_dq_job")
    source = inspect.getsource(module.build_actual_dq_checks)

    assert "utc_now_iso" in source
    assert "2025-03-01" not in source


def test_spark_dq_runs_before_publication_promotion():
    module = importlib.import_module("src.jobs.stage1_spark_lakehouse_job")
    source = inspect.getsource(module.run_stage1_spark_lakehouse)

    assert source.index("validate_spark_outputs") < source.index("promote_staged_prefixes")


def test_fixture_only_numbered_dags_are_retired_after_rubric_pipelines_replace_them():
    for path in (
        "dags/04_stream_market_events_to_kafka.py",
        "dags/05_transform_bronze_to_silver.py",
        "dags/06_pyspark_silver_to_gold.py",
        "dags/07_run_data_quality_checks.py",
        "dags/08_minio_duckdb_register_tables.py",
    ):
        assert not Path(path).exists()
    for path in (
        "dags/ingest_source_to_bronze.py",
        "dags/build_silver_gold.py",
        "dags/build_offline_features.py",
    ):
        assert Path(path).is_file()
