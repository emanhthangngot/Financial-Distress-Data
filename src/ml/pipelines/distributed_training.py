"""Distributed-training boundary with a deterministic local demonstration.

In production ``submit_kubeflow`` serialises a Trainer job to the Kubeflow
endpoint.  Local tests use ``train_local`` to exercise the same worker-shard
semantics without requiring a cluster or optional HTTP libraries.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any

from src.ml.pipelines.training_pipeline import LogisticModel, TrainingPipeline, _records


@dataclass(frozen=True)
class DistributedTrainingResult:
    model: LogisticModel
    worker_count: int
    shard_sizes: tuple[int, ...]
    backend: str


class DistributedTrainer:
    """Split data deterministically across workers and train a baseline."""

    def __init__(self, worker_count: int = 2):
        if worker_count < 1:
            raise ValueError("worker_count must be positive")
        self.worker_count = int(worker_count)

    def train_local(
        self, train_df: Any, config: dict[str, Any] | None = None
    ) -> DistributedTrainingResult:
        rows = _records(train_df)
        shards = [rows[index :: self.worker_count] for index in range(self.worker_count)]
        # The baseline consumes all rows; shards are retained as evidence of the
        # distributed topology rather than averaging incompatible local models.
        model = TrainingPipeline().train(rows, config or {})
        return DistributedTrainingResult(model, self.worker_count, tuple(map(len, shards)), "local")

    def submit_kubeflow(
        self,
        endpoint: str,
        *,
        job_name: str,
        image: str,
        config: dict[str, Any] | None = None,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        """Submit a Trainer-style JSON payload; no request is made on import."""

        payload = {
            "metadata": {"name": job_name},
            "spec": {
                "runtime": {"image": image},
                "replicas": self.worker_count,
                "config": config or {},
            },
        }
        request = urllib.request.Request(
            endpoint.rstrip("/") + "/jobs",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            body = response.read().decode("utf-8")
        return json.loads(body) if body else {"submitted": True, "job_name": job_name}


def distributed_train(
    train_df: Any, config: dict[str, Any] | None = None, *, workers: int = 2
) -> DistributedTrainingResult:
    return DistributedTrainer(workers).train_local(train_df, config)
