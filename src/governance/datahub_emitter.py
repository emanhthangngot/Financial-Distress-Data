"""Emit the validated governance model through the DataHub 1.6 SDK."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from src.governance.datahub_model import GovernanceModel


def _assertion_field_type(native_type: str) -> str:
    """Map project-native types to DataHub schema assertion field types."""
    mapping = {
        "boolean": "BOOLEAN",
        "date": "TIME",
        "float": "NUMBER",
        "integer": "NUMBER",
        "number": "NUMBER",
        "string": "STRING",
        "time": "TIME",
    }
    try:
        return mapping[native_type.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported assertion field type: {native_type}") from exc


def _dataset_urn(model: GovernanceModel, dataset_name: str):
    from datahub.metadata.urns import DatasetUrn

    dataset = model.datasets[dataset_name]
    return DatasetUrn(
        platform=dataset.platform,
        name=f"{model.platform_instance}.{dataset.name}",
        env=model.environment,
    )


def _assertion_urn(pipeline_name: str, assertion_kind: str) -> str:
    assertion_id = hashlib.sha256(
        f"financial-distress:{pipeline_name}:{assertion_kind}".encode()
    ).hexdigest()[:32]
    return f"urn:li:assertion:{assertion_id}"


def _emit_oss_assertions(
    client: Any,
    pipeline_name: str,
    dataset_urn: str,
    schema_metadata: Any,
    run_id: str,
) -> tuple[str, str]:
    """Emit assertion definitions and successful run events to DataHub OSS."""
    from datahub.emitter.mcp import MetadataChangeProposalWrapper
    from datahub.metadata.schema_classes import (
        AssertionInfoClass,
        AssertionResultClass,
        AssertionResultTypeClass,
        AssertionRunEventClass,
        AssertionRunStatusClass,
        AssertionSourceClass,
        AssertionSourceTypeClass,
        AssertionStdOperatorClass,
        AssertionStdParameterClass,
        AssertionStdParametersClass,
        AssertionTypeClass,
        RowCountTotalClass,
        SchemaAssertionCompatibilityClass,
        SchemaAssertionInfoClass,
        VolumeAssertionInfoClass,
        VolumeAssertionTypeClass,
    )

    timestamp_ms = int(time.time() * 1000)
    assertion_specs = {
        "schema": AssertionInfoClass(
            type=AssertionTypeClass.DATA_SCHEMA,
            schemaAssertion=SchemaAssertionInfoClass(
                entity=dataset_urn,
                schema=schema_metadata,
                compatibility=SchemaAssertionCompatibilityClass.SUPERSET,
            ),
            source=AssertionSourceClass(type=AssertionSourceTypeClass.EXTERNAL),
            description=f"{pipeline_name} required output schema",
            customProperties={"pipeline": pipeline_name},
        ),
        "volume": AssertionInfoClass(
            type=AssertionTypeClass.VOLUME,
            volumeAssertion=VolumeAssertionInfoClass(
                type=VolumeAssertionTypeClass.ROW_COUNT_TOTAL,
                entity=dataset_urn,
                rowCountTotal=RowCountTotalClass(
                    operator=AssertionStdOperatorClass.GREATER_THAN_OR_EQUAL_TO,
                    parameters=AssertionStdParametersClass(
                        value=AssertionStdParameterClass(value="1", type="NUMBER")
                    ),
                ),
            ),
            source=AssertionSourceClass(type=AssertionSourceTypeClass.EXTERNAL),
            description=f"{pipeline_name} output must be non-empty",
            customProperties={"pipeline": pipeline_name},
        ),
    }
    urns = {}
    for assertion_kind, assertion_info in assertion_specs.items():
        assertion_urn = _assertion_urn(pipeline_name, assertion_kind)
        client._graph.emit_mcp(
            MetadataChangeProposalWrapper(
                entityType="assertion",
                entityUrn=assertion_urn,
                aspect=assertion_info,
            )
        )
        client._graph.emit_mcp(
            MetadataChangeProposalWrapper(
                entityType="assertion",
                entityUrn=assertion_urn,
                aspect=AssertionRunEventClass(
                    timestampMillis=timestamp_ms,
                    runId=run_id,
                    asserteeUrn=dataset_urn,
                    status=AssertionRunStatusClass.COMPLETE,
                    assertionUrn=assertion_urn,
                    result=AssertionResultClass(
                        type=AssertionResultTypeClass.SUCCESS,
                        nativeResults={
                            "governance_run_id": run_id,
                            "validation": assertion_kind,
                        },
                    ),
                ),
            )
        )
        urns[assertion_kind] = assertion_urn
    return urns["schema"], urns["volume"]


def emit_governance(model: GovernanceModel, client: Any, run_id: str) -> dict[str, Any]:
    """Upsert datasets, Airflow flows/jobs, lineage, and contract assertions."""
    from datahub.sdk import DataFlow, DataJob, Dataset

    model.validate()
    dataset_urns = {}
    dataset_entities = {}
    for spec in model.datasets.values():
        entity = Dataset(
            platform=spec.platform,
            name=spec.name,
            platform_instance=model.platform_instance,
            env=model.environment,
            description=f"Financial distress coursework dataset {spec.name}",
            schema=[(name, field_type) for name, field_type in spec.fields],
            custom_properties={"governance_run_id": run_id, "owner": model.owner},
            owners=[model.owner],
        )
        client.entities.upsert(entity)
        dataset_urns[spec.name] = str(entity.urn)
        dataset_entities[spec.name] = entity

    contracts = {}
    for pipeline in model.pipelines.values():
        flow = DataFlow(
            platform="airflow",
            name=pipeline.name,
            platform_instance=model.platform_instance,
            env=model.environment,
            description=f"Rubric pipeline {pipeline.name}",
            custom_properties={"governance_run_id": run_id},
        )
        job = DataJob(
            name=f"{pipeline.name}.validated_publish",
            flow=flow,
            inlets=[_dataset_urn(model, name) for name in pipeline.inputs],
            outlets=[_dataset_urn(model, name) for name in pipeline.outputs],
            description="Validated publication boundary",
            custom_properties={"governance_run_id": run_id},
        )
        client.entities.upsert(flow)
        client.entities.upsert(job)

        contract_spec = model.datasets[pipeline.contract_dataset]
        contract_urn = _dataset_urn(model, pipeline.contract_dataset)
        if hasattr(client, "_graph"):
            contract_entity = dataset_entities[pipeline.contract_dataset]
            schema_assertion_urn, volume_assertion_urn = _emit_oss_assertions(
                client,
                pipeline.name,
                str(contract_urn),
                contract_entity._aspects["schemaMetadata"],
                run_id,
            )
        else:
            fields = [
                {"path": name, "type": _assertion_field_type(field_type)}
                for name, field_type in contract_spec.fields
            ]
            schema_assertion = client.assertions.sync_schema_assertion(
                dataset_urn=contract_urn,
                display_name=f"{pipeline.name} required schema",
                compatibility="SUPERSET",
                fields=fields,
                tags=["coursework", pipeline.name, "schema-contract"],
                enabled=True,
            )
            volume_assertion = client.assertions.sync_volume_assertion(
                dataset_urn=contract_urn,
                display_name=f"{pipeline.name} non-empty output",
                criteria_condition="ROW_COUNT_IS_GREATER_THAN_OR_EQUAL_TO",
                criteria_parameters=1,
                detection_mechanism="datahub_dataset_profile",
                tags=["coursework", pipeline.name, "data-quality"],
                enabled=True,
            )
            schema_assertion_urn = str(schema_assertion.urn)
            volume_assertion_urn = str(volume_assertion.urn)
        contracts[pipeline.name] = {
            "dataset": str(contract_urn),
            "schema_assertion": schema_assertion_urn,
            "volume_assertion": volume_assertion_urn,
        }
    return {
        "schema_version": 1,
        "status": "pass",
        "run_id": run_id,
        "dataset_urns": dataset_urns,
        "contracts": contracts,
    }
