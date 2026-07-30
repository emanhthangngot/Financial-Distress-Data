"""Validated metadata model for DataHub lineage, schemas, and contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class DatasetSpec:
    """One governed dataset and its minimal schema."""

    name: str
    platform: str
    fields: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class PipelineSpec:
    """One pipeline's dataset lineage and representative contract output."""

    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    contract_dataset: str


@dataclass(frozen=True)
class GovernanceModel:
    """Validated governance registry used for deterministic DataHub emission."""

    schema_version: int
    datahub_version: str
    environment: str
    platform_instance: str
    owner: str
    datasets: dict[str, DatasetSpec]
    pipelines: dict[str, PipelineSpec]

    def validate(self) -> None:
        if self.schema_version != 1:
            raise ValueError("schema_version must be 1")
        if not self.datahub_version or not self.datasets or not self.pipelines:
            raise ValueError("DataHub version, datasets and pipelines are required")
        for pipeline in self.pipelines.values():
            referenced = (*pipeline.inputs, *pipeline.outputs, pipeline.contract_dataset)
            missing = [name for name in referenced if name not in self.datasets]
            if missing:
                raise ValueError(f"{pipeline.name} references unknown datasets: {missing}")
            if pipeline.contract_dataset not in pipeline.outputs:
                raise ValueError(f"{pipeline.name} contract_dataset must be one of its outputs")
            if not pipeline.inputs or not pipeline.outputs:
                raise ValueError(f"{pipeline.name} requires input and output lineage")
        for dataset in self.datasets.values():
            if not dataset.platform or not dataset.fields:
                raise ValueError(f"{dataset.name} requires platform and schema fields")


def load_governance_model(path: str | Path) -> GovernanceModel:
    """Load and validate a governance YAML file."""
    raw: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    datasets = {
        name: DatasetSpec(
            name=name,
            platform=value["platform"],
            fields=tuple(tuple(field) for field in value["fields"]),
        )
        for name, value in raw.pop("datasets").items()
    }
    pipelines = {
        name: PipelineSpec(
            name=name,
            inputs=tuple(value["inputs"]),
            outputs=tuple(value["outputs"]),
            contract_dataset=value["contract_dataset"],
        )
        for name, value in raw.pop("pipelines").items()
    }
    model = GovernanceModel(datasets=datasets, pipelines=pipelines, **raw)
    model.validate()
    return model


def audit_governance_model(model: GovernanceModel) -> dict[str, Any]:
    """Summarize governance coverage without requiring a live DataHub server."""
    model.validate()
    return {
        "schema_version": 1,
        "status": "pass",
        "datahub_version": model.datahub_version,
        "dataset_count": len(model.datasets),
        "pipeline_count": len(model.pipelines),
        "lineage_edges": sum(
            len(pipeline.inputs) + len(pipeline.outputs) for pipeline in model.pipelines.values()
        ),
        "contracts": {
            name: {
                "dataset": pipeline.contract_dataset,
                "schema_assertion": True,
                "volume_assertion": True,
            }
            for name, pipeline in model.pipelines.items()
        },
    }
