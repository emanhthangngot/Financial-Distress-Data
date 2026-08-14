"""Focused validation tests for the local ML core.

The tests deliberately use stdlib-only fixtures so they remain useful in the
dependency-light CI image.  Equivalence partitions cover clean/leaked/empty
frames; boundary checks cover the exact PIT timestamp and A/B weight edges.
"""

from __future__ import annotations

import pytest

from src.ml.ab_router import ABRouter
from src.ml.data_versioning import snapshot_id, version_data
from src.ml.leakage_guard import LeakageError, assert_no_leakage
from src.ml.pipelines.distributed_training import DistributedTrainer
from src.ml.pipelines.training_pipeline import TrainingPipeline
from src.ml.reproducibility_manifest import build_manifest


def _rows() -> list[dict[str, object]]:
    return [
        {
            "feature_timestamp": "2024-01-01T00:00:00",
            "decision_timestamp": "2024-01-01T00:00:00",
            "signal": -2.0,
            "label": 0,
        },
        {
            "feature_timestamp": "2024-01-02T00:00:00",
            "decision_timestamp": "2024-01-02T00:00:00",
            "signal": 2.0,
            "label": 1,
        },
        {
            "feature_timestamp": "2024-01-03T00:00:00",
            "decision_timestamp": "2024-01-03T00:00:00",
            "signal": 2.5,
            "label": 1,
        },
        {
            "feature_timestamp": "2024-01-04T00:00:00",
            "decision_timestamp": "2024-01-04T00:00:00",
            "signal": -1.5,
            "label": 0,
        },
    ]


def test_equivalence_partition_clean_and_empty_frames() -> None:
    assert assert_no_leakage([]) is None
    assert assert_no_leakage(_rows()) is None


def test_leakage_partition_names_offending_rows() -> None:
    leaked = _rows()
    leaked[1]["feature_timestamp"] = "2024-01-03T00:00:01"
    with pytest.raises(LeakageError, match="rows: 1") as error:
        assert_no_leakage(leaked)
    assert error.value.offending_rows[0]["index"] == 1


def test_boundary_timestamp_is_not_leakage() -> None:
    assert_no_leakage([{"event_timestamp": "2024-01-01", "label_timestamp": "2024-01-01"}])


def test_manifest_and_data_version_are_deterministic() -> None:
    rows = _rows()
    first = build_manifest(
        "iceberg-42", source_sha="abc", image_digest="sha256:def", environment={"lock": "1"}
    )
    second = build_manifest(
        "iceberg-42", source_sha="abc", image_digest="sha256:def", environment={"lock": "1"}
    )
    assert first == second
    assert first.digest() == second.digest()
    assert snapshot_id(rows) == snapshot_id(list(reversed(rows)))
    assert version_data(rows).as_dict() == version_data(rows).as_dict()


def test_router_is_stable_and_validates_weight_boundaries() -> None:
    router = ABRouter({"stable": 0.8, "canary": 0.2}, salt="test")
    assert [router.route("customer-1") for _ in range(3)] == ["stable"] * 3
    assert set(router.route(str(index)) for index in range(100)) <= {"stable", "canary"}
    with pytest.raises(ValueError):
        ABRouter({"stable": 0, "canary": 0})
    with pytest.raises(ValueError):
        ABRouter({"stable": -1, "canary": 2})


def test_training_and_distributed_local_paths_are_reproducible() -> None:
    rows = _rows()
    config = {"feature_columns": ["signal"], "label_col": "label"}
    first = TrainingPipeline().run(rows, config=config, snapshot_id="iceberg-42", source_sha="abc")
    second = TrainingPipeline().run(rows, config=config, snapshot_id="iceberg-42", source_sha="abc")
    assert first.metrics == second.metrics
    distributed = DistributedTrainer(worker_count=2).train_local(rows, config)
    assert distributed.worker_count == 2
    assert distributed.shard_sizes == (2, 2)
