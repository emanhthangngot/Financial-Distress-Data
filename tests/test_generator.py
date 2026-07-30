from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from src.generator.config import GeneratorConfig, load_generator_config
from src.generator.offline import generate_offline_data
from src.generator.profile import build_generator_profile, logical_digest
from src.generator.storage import LocalSourceWriter
from src.generator.streaming import generate_stream_events
from src.metadata.schema_registry import InMemorySchemaRegistry

CONFIG_PATH = Path("configs/generator-config.yaml")


def _ci_config() -> GeneratorConfig:
    return load_generator_config(CONFIG_PATH, profile="ci")


def test_config_profiles_are_typed_and_validated():
    config = _ci_config()

    assert config.seed == 42
    assert config.offline.companies == 100
    assert config.streaming.events == 200
    assert config.output.format == "jsonl"

    with pytest.raises(ValueError, match="duplicate_rate"):
        replace(config.offline, duplicate_rate=1.1).validate()


def test_same_seed_and_config_produce_identical_logical_records():
    config = _ci_config()

    first_offline = generate_offline_data(config)
    second_offline = generate_offline_data(config)
    first_stream = generate_stream_events(config)
    second_stream = generate_stream_events(config)

    assert logical_digest(first_offline.logical_rows()) == logical_digest(
        second_offline.logical_rows()
    )
    assert logical_digest(first_stream) == logical_digest(second_stream)


def test_offline_generator_meets_skew_cardinality_schema_and_duplicate_contracts():
    config = _ci_config()
    result = generate_offline_data(config)
    companies = result.companies
    base_companies = [row for row in companies if not row["is_injected_duplicate"]]

    dominant = sum(row["sector"] == config.offline.dominant_sector for row in base_companies)
    assert dominant / len(base_companies) == pytest.approx(
        config.offline.dominant_sector_rate, abs=0.01
    )
    assert len({row["source_record_id"] for row in base_companies}) == len(base_companies)
    assert len({row["high_cardinality_id"] for row in base_companies}) == (
        config.offline.high_cardinality_ids
    )
    assert result.offline_duplicate_rate == pytest.approx(config.offline.duplicate_rate, abs=0.011)

    old_rows = [row for row in result.financial_statements if row["schema_version"] == 1]
    new_rows = [row for row in result.financial_statements if row["schema_version"] == 2]
    assert old_rows and new_rows
    assert all(row["operating_cash_flow"] is None for row in old_rows)
    assert all(row["operating_cash_flow"] is not None for row in new_rows)


def test_stream_generator_meets_burst_lateness_out_of_order_and_duplicate_contracts():
    config = _ci_config()
    events = generate_stream_events(config)
    profile = build_generator_profile(config, generate_offline_data(config), events)
    stream = profile["streaming"]

    assert stream["duplicate_rate"] == pytest.approx(config.streaming.duplicate_rate, abs=0.006)
    assert stream["late_rate"] == pytest.approx(config.streaming.late_rate, abs=0.006)
    assert stream["out_of_order_rate"] == pytest.approx(
        config.streaming.out_of_order_rate, abs=0.006
    )
    assert stream["peak_to_baseline_ratio"] >= config.streaming.burst_multiplier * 0.8
    assert all(event["topic"] == "financial.price_events" for event in events)


def test_local_source_writer_round_trips_rows_and_manifest(tmp_path: Path):
    config = replace(_ci_config(), output=replace(_ci_config().output, root=str(tmp_path)))
    offline = generate_offline_data(config)
    events = generate_stream_events(config)
    profile = build_generator_profile(config, offline, events)

    manifest = LocalSourceWriter().write(config, offline, events, profile)

    assert manifest["run_id"] == config.run_id
    assert manifest["datasets"]["companies"]["rows"] == len(offline.companies)
    company_path = tmp_path / config.run_id / "offline" / "companies.jsonl"
    company_rows = [json.loads(line) for line in company_path.read_text().splitlines()]
    assert logical_digest(company_rows) == manifest["datasets"]["companies"]["sha256"]
    assert (tmp_path / config.run_id / "profile.json").is_file()


def test_profile_covers_every_generator_rubric_characteristic():
    config = _ci_config()
    offline = generate_offline_data(config)
    profile = build_generator_profile(config, offline, generate_stream_events(config))

    assert set(profile["offline"]) >= {
        "sector_distribution",
        "exchange_distribution",
        "exact_cardinality",
        "schema_versions",
        "duplicate_rate",
        "rows_by_dataset",
    }
    assert set(profile["streaming"]) >= {
        "events",
        "window_counts",
        "peak_to_baseline_ratio",
        "late_rate",
        "out_of_order_rate",
        "duplicate_rate",
    }
    assert profile["storage"]["minio_format"] == "parquet"


def test_generated_batch_rows_satisfy_existing_bronze_ingest_contracts():
    generated = generate_offline_data(_ci_config())
    registry = InMemorySchemaRegistry.from_yaml("configs/schema-contracts.yaml")

    for dataset_name, rows in generated.datasets().items():
        contract = registry.get_current(dataset_name)
        for row in rows:
            assert contract.validate_row(row)
