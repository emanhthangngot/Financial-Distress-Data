from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from src.governance.datahub_emitter import _assertion_field_type
from src.governance.datahub_graphql import (
    DataHubGraphQLError,
    upsert_data_contracts,
    verify_governance_entities,
)
from src.governance.datahub_model import (
    audit_governance_model,
    load_governance_model,
)

CONFIG = Path("configs/datahub/governance.yaml")


def test_governance_model_covers_three_pipelines_lineage_and_contracts():
    model = load_governance_model(CONFIG)
    audit = audit_governance_model(model)

    assert audit["status"] == "pass"
    assert audit["pipeline_count"] == 3
    assert audit["dataset_count"] >= 15
    assert audit["lineage_edges"] >= 20
    assert set(audit["contracts"]) == {
        "ingest_source_to_bronze",
        "build_silver_gold",
        "build_offline_features",
    }


def test_governance_model_rejects_contract_outside_pipeline_outputs(tmp_path: Path):
    raw = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    raw["pipelines"]["build_offline_features"]["contract_dataset"] = "bronze.companies"
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="contract_dataset"):
        load_governance_model(invalid)


def test_datahub_emitter_upserts_datasets_flows_jobs_and_assertions():
    pytest.importorskip("datahub")
    from src.governance.datahub_emitter import emit_governance

    class Entities:
        def __init__(self):
            self.items = []

        def upsert(self, item):
            self.items.append(item)

    class Assertions:
        def __init__(self):
            self.schemas = []
            self.volumes = []

        def sync_schema_assertion(self, **kwargs):
            self.schemas.append(kwargs)
            return SimpleNamespace(urn=f"urn:li:assertion:schema-{len(self.schemas)}")

        def sync_volume_assertion(self, **kwargs):
            self.volumes.append(kwargs)
            return SimpleNamespace(urn=f"urn:li:assertion:volume-{len(self.volumes)}")

    client = SimpleNamespace(entities=Entities(), assertions=Assertions())

    report = emit_governance(load_governance_model(CONFIG), client, "phase7-test")

    assert report["status"] == "pass"
    assert len(client.entities.items) == 21
    assert len(client.assertions.schemas) == 3
    assert len(client.assertions.volumes) == 3
    assert set(report["contracts"]) == {
        "ingest_source_to_bronze",
        "build_silver_gold",
        "build_offline_features",
    }


def test_assertion_type_mapping_handles_dates_and_rejects_unknown_types():
    assert _assertion_field_type("date") == "TIME"
    assert _assertion_field_type("integer") == "NUMBER"
    with pytest.raises(ValueError, match="Unsupported"):
        _assertion_field_type("currency")


def test_dataset_lineage_urn_matches_platform_instance_entity_urn():
    pytest.importorskip("datahub")
    from src.governance.datahub_emitter import _dataset_urn

    model = load_governance_model(CONFIG)
    urn = str(_dataset_urn(model, "bronze.companies"))

    assert "financial-distress-local.bronze.companies" in urn


def test_contract_upsert_bundles_schema_and_quality_assertions(monkeypatch):
    calls = []

    def fake_execute(server, query, variables, **kwargs):
        calls.append((server, query, variables, kwargs))
        return {"upsertDataContract": {"urn": f"urn:li:dataContract:{len(calls)}"}}

    monkeypatch.setattr("src.governance.datahub_graphql.execute_graphql", fake_execute)
    contracts = {
        "dp1": {
            "dataset": "urn:li:dataset:dp1",
            "schema_assertion": "urn:li:assertion:schema",
            "volume_assertion": "urn:li:assertion:volume",
        }
    }

    result = upsert_data_contracts("http://datahub", contracts, token="token")

    assert result == {"dp1": "urn:li:dataContract:1"}
    assert calls[0][2]["input"] == {
        "entityUrn": "urn:li:dataset:dp1",
        "schema": [{"assertionUrn": "urn:li:assertion:schema"}],
        "dataQuality": [{"assertionUrn": "urn:li:assertion:volume"}],
    }


def test_verification_rejects_missing_contract(monkeypatch):
    monkeypatch.setattr(
        "src.governance.datahub_graphql.execute_graphql",
        lambda *args, **kwargs: {
            "dataset": {
                "urn": "urn:li:dataset:dp1",
                "schemaMetadata": {"fields": [{"fieldPath": "ticker"}]},
                "lineage": {"total": 1},
                "assertions": {"total": 2},
                "contract": None,
            }
        },
    )
    contracts = {
        "dp1": {
            "dataset": "urn:li:dataset:dp1",
            "schema_assertion": "urn:li:assertion:schema",
            "volume_assertion": "urn:li:assertion:volume",
        }
    }

    with pytest.raises(DataHubGraphQLError, match="contract is missing"):
        verify_governance_entities("http://datahub", contracts)
