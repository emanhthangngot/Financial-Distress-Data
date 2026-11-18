"""ML track class contracts (platform .esign contract, phase-01).

These are *signature contracts*, not implementations. They lock the five
named ML classes before implementation begins. Each method carries a
docstring that states its behaviour and the platform .esign reference.

The contracts are intentionally side-effect free (documentation-level):
implementations live under ``src/ml/`` in later phases and must satisfy
these signatures plus the rubric-matrix evidence contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class TrainingDataService(ABC):
    """Reads Feast historical features, joins labels, and returns a validated
    training frame with snapshot lineage.

    Design reference: docs/platform/low-level-design.md (ML-1).
    """

    @abstractmethod
    def read_historical_features(self, feature_view: str, entity_rows: Any) -> Any:
        """Read historical features from the Feast offline store for entity rows."""

    @abstractmethod
    def join_labels(self, features: Any, label_table: str) -> Any:
        """Join the label table by ticker + event_timestamp using PIT rules."""

    @abstractmethod
    def validate_schema(self, df: Any) -> None:
        """Raise if the frame violates the documented training schema."""

    @abstractmethod
    def snapshot_lineage(self, df: Any) -> dict[str, Any]:
        """Return data snapshot ID, parent ID, changed partitions and Feast
        registry revision for this training frame."""


class PointInTimeSplitService(ABC):
    """Derives non-overlapping time boundaries and train/validation/test
    frames without future leakage."""

    @abstractmethod
    def get_split_boundaries(self, df: Any) -> dict[str, Any]:
        """Return {'train_end', 'validation_end', 'test_end'} timestamps."""

    @abstractmethod
    def split_by_time(self, df: Any) -> tuple[Any, Any, Any]:
        """Split into (train, validation, test) DataFrames by time, no leakage."""

    @abstractmethod
    def assert_no_leakage(self, df: Any, split: tuple[Any, Any, Any]) -> None:
        """Assert features never reference data after the label timestamp."""


class FeatureMaterializationService(ABC):
    """Owns batch/stream materialization checkpoints, TTL and idempotency."""

    @abstractmethod
    def materialize_offline_to_online(
        self, feature_view: str, start_ts: Any, end_ts: Any
    ) -> dict[str, Any]:
        """Materialize an interval from offline store to online store
        idempotently and return job evidence."""

    @abstractmethod
    def push_stream_features_offline(self, events: Any) -> dict[str, Any]:
        """Push stream features to the offline store with a checkpoint."""

    @abstractmethod
    def push_stream_features_online(self, events: Any) -> dict[str, Any]:
        """Push stream features to the online store with a checkpoint."""

    @abstractmethod
    def ttl_policy(self) -> dict[str, str]:
        """Return per-feature-view TTL with a documented business rationale."""


class ModelTrainingService(ABC):
    """Trains and evaluates distributed baseline models, logging reproducible
    MLflow runs."""

    @abstractmethod
    def train(self, train_df: Any, config: dict[str, Any]) -> Any:
        """Train a baseline (logistic regression or XGBoost) on the training
        frame using distributed training (Kubeflow Trainer)."""

    @abstractmethod
    def evaluate(self, model: Any, validation_df: Any) -> dict[str, float]:
        """Return PR-AUC, distress recall, calibration metrics, and a
        confusion matrix summary."""

    @abstractmethod
    def log_run(self, model: Any, metrics: dict[str, float], data_version: str) -> str:
        """Log weights, hyperparameters, metrics, signature/card, data snapshot
        ID, code SHA and environment digest to MLflow; return run ID."""


class ModelPromotionService(ABC):
    """Applies promotion gates, resolves an immutable artifact URI, opens a
    GitOps PR, canaries, and emits Git-revert rollback metadata."""

    @abstractmethod
    def check_gates(self, candidate_id: str) -> dict[str, Any]:
        """Evaluate DQ pass, no leakage, metric/calibration thresholds, signed
        image, and complete evidence manifest; return per-gate status."""

    @abstractmethod
    def resolve_immutable_uri(self, candidate_id: str) -> str:
        """Resolve the MLflow production alias to an immutable S3 artifact URI."""

    @abstractmethod
    def open_gitops_pr(self, uri: str, image_digest: str) -> str:
        """Open a GitOps PR changing the desired model/agent digest; return PR URL."""

    @abstractmethod
    def rollback_metadata(self, revision: str) -> dict[str, Any]:
        """Emit Git-revert rollback metadata for the previous production digest."""
