"""Deterministic contracts shared by the rubric Airflow pipelines."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from src.transforms.features.pit import _parse_timestamp


class PipelineValidationError(RuntimeError):
    """Block publication when an orchestration quality gate fails."""


def stable_pipeline_run_id(dag_id: str, logical_date: datetime) -> str:
    """Build one shared run ID for every pipeline in a logical interval."""
    interval = logical_date.strftime("%Y%m%dT%H%M%S")
    digest = hashlib.sha256(logical_date.isoformat().encode()).hexdigest()[:10]
    return f"coursework-{interval}-{digest}"


def validate_required_counts(
    counts: dict[str, int], required_datasets: tuple[str, ...]
) -> dict[str, int]:
    """Return counts only when every required dataset is non-empty."""
    missing = [name for name in required_datasets if counts.get(name, 0) <= 0]
    if missing:
        raise PipelineValidationError(
            "publication blocked for empty datasets: " + ", ".join(missing)
        )
    return counts


def validate_feature_snapshot(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Reject missing timestamps and any feature newer than its reference event."""
    if not rows:
        raise PipelineValidationError("feature snapshot is empty")
    for row in rows:
        if not row.get("created_ts"):
            raise PipelineValidationError("feature row is missing created_ts")
        reference = _parse_timestamp(row.get("event_timestamp"))
        feature = _parse_timestamp(row.get("feature_event_timestamp") or row.get("event_timestamp"))
        if feature > reference:
            raise PipelineValidationError(
                f"future feature detected for ticker {row.get('ticker', 'unknown')}"
            )
    return {"feature_rows": len(rows), "future_rows": 0}


def validate_feature_audit(audit: dict[str, int]) -> dict[str, int]:
    """Validate the compact PIT audit passed between Airflow tasks."""
    if audit.get("feature_rows", 0) <= 0:
        raise PipelineValidationError("feature snapshot is empty")
    if audit.get("future_rows", 0) != 0:
        raise PipelineValidationError("future feature rows detected")
    return audit
