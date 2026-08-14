"""Deterministic, dependency-light training pipeline.

The implementation uses a small logistic-regression baseline in pure Python,
which keeps local/offline verification possible without scikit-learn.  A
scikit-learn/XGBoost implementation can be injected by callers later without
changing the lineage, leakage, or registry boundaries.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from src.ml.data_versioning import DataVersion, version_data
from src.ml.leakage_guard import assert_no_leakage
from src.ml.mlflow_registry import MLflowRegistry
from src.ml.reproducibility_manifest import ReproducibilityManifest, build_manifest


def _records(frame: Any) -> list[dict[str, Any]]:
    if hasattr(frame, "to_dict"):
        try:
            return [dict(row) for row in frame.to_dict(orient="records")]
        except TypeError:
            pass
    if isinstance(frame, Mapping):
        return [dict(frame)]
    return [dict(row) for row in frame]


@dataclass(frozen=True)
class LogisticModel:
    feature_columns: tuple[str, ...]
    coefficients: tuple[float, ...]
    intercept: float

    def score(self, row: Mapping[str, Any]) -> float:
        value = self.intercept + sum(
            coefficient * float(row.get(column, 0.0))
            for column, coefficient in zip(self.feature_columns, self.coefficients, strict=True)
        )
        value = max(-60.0, min(60.0, value))
        return 1.0 / (1.0 + math.exp(-value))

    def predict_proba(self, rows: Any) -> list[float]:
        return [self.score(row) for row in _records(rows)]

    def predict(self, rows: Any, threshold: float = 0.5) -> list[int]:
        return [int(value >= threshold) for value in self.predict_proba(rows)]


@dataclass(frozen=True)
class TrainingResult:
    model: LogisticModel
    metrics: dict[str, float]
    data_version: DataVersion
    manifest: ReproducibilityManifest
    model_version: str | None = None


def _fit_logistic(
    rows: list[dict[str, Any]], columns: Sequence[str], label_col: str
) -> LogisticModel:
    if not rows:
        raise ValueError("training frame is empty")
    labels = [int(row[label_col]) for row in rows]
    if any(label not in (0, 1) for label in labels):
        raise ValueError("binary labels must be 0 or 1")
    weights = [0.0] * len(columns)
    intercept = 0.0
    # Fixed iteration/order makes the baseline bit-for-bit reproducible.
    for _ in range(250):
        grad_w = [0.0] * len(columns)
        grad_b = 0.0
        for row, label in zip(rows, labels, strict=True):
            linear = intercept + sum(
                weight * float(row.get(column, 0.0))
                for weight, column in zip(weights, columns, strict=True)
            )
            probability = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, linear))))
            error = probability - label
            for index, column in enumerate(columns):
                grad_w[index] += error * float(row.get(column, 0.0))
            grad_b += error
        scale = 0.05 / len(rows)
        weights = [
            weight - scale * gradient for weight, gradient in zip(weights, grad_w, strict=True)
        ]
        intercept -= scale * grad_b
    return LogisticModel(tuple(columns), tuple(weights), intercept)


def evaluate_model(
    model: LogisticModel, rows: Any, *, label_col: str = "label"
) -> dict[str, float]:
    records = _records(rows)
    if not records:
        return {
            "pr_auc": 0.0,
            "distress_recall": 0.0,
            "accuracy": 0.0,
            "calibration_error": 0.0,
            "tp": 0.0,
            "tn": 0.0,
            "fp": 0.0,
            "fn": 0.0,
        }
    labels = [int(row[label_col]) for row in records]
    probabilities = model.predict_proba(records)
    predictions = [int(value >= 0.5) for value in probabilities]
    tp = sum(
        prediction == label == 1 for prediction, label in zip(predictions, labels, strict=True)
    )
    tn = sum(
        prediction == label == 0 for prediction, label in zip(predictions, labels, strict=True)
    )
    fp = sum(
        prediction == 1 and label == 0
        for prediction, label in zip(predictions, labels, strict=True)
    )
    fn = sum(
        prediction == 0 and label == 1
        for prediction, label in zip(predictions, labels, strict=True)
    )
    positives = sum(labels)
    ordered = sorted(zip(probabilities, labels, strict=True), reverse=True)
    seen_positive = 0
    precision_sum = 0.0
    for rank, (_, label) in enumerate(ordered, 1):
        if label:
            seen_positive += 1
            precision_sum += seen_positive / rank
    pr_auc = precision_sum / positives if positives else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    calibration = sum(
        abs(probability - label) for probability, label in zip(probabilities, labels, strict=True)
    ) / len(labels)
    return {
        "pr_auc": round(pr_auc, 8),
        "distress_recall": round(recall, 8),
        "accuracy": round((tp + tn) / len(labels), 8),
        "calibration_error": round(calibration, 8),
        "tp": float(tp),
        "tn": float(tn),
        "fp": float(fp),
        "fn": float(fn),
    }


class TrainingPipeline:
    """Run PIT validation, deterministic training, evaluation and registration."""

    def __init__(self, registry: MLflowRegistry | None = None):
        self.registry = registry

    def train(self, train_df: Any, config: dict[str, Any] | None = None) -> LogisticModel:
        config = config or {}
        rows = _records(train_df)
        columns = tuple(
            config.get("feature_columns")
            or [
                key
                for key in rows[0]
                if key
                not in {
                    "label",
                    "label_timestamp",
                    "decision_timestamp",
                    "event_timestamp",
                    "feature_timestamp",
                }
            ]
        )
        return _fit_logistic(rows, columns, str(config.get("label_col", "label")))

    def evaluate(self, model: LogisticModel, validation_df: Any) -> dict[str, float]:
        return evaluate_model(model, validation_df)

    def log_run(self, model: LogisticModel, metrics: dict[str, float], data_version: str) -> str:
        """Log a run through the injected registry and return its run/version ID.

        The local adapter has no separate run service, so the data version is
        used as a stable run identity while MLflow callers may override this
        method at their integration boundary.
        """

        if self.registry is None:
            return str(data_version)
        record = self.registry.register(
            "financial-distress-baseline",
            f"local://model/{data_version}",
            run_id=str(data_version),
            manifest={"metrics": metrics, "data_version": data_version},
        )
        return str(record.get("run_id") or record["version"])

    def run(
        self,
        train_df: Any,
        validation_df: Any | None = None,
        *,
        snapshot_id: str | None = None,
        source_sha: str | None = None,
        image_digest: str = "unknown",
        config: dict[str, Any] | None = None,
    ) -> TrainingResult:
        config = config or {}
        train_rows = _records(train_df)
        assert_no_leakage(train_rows)
        version = version_data(train_rows, source="iceberg")
        if snapshot_id and snapshot_id != version.snapshot_id:
            # An external snapshot ID is authoritative but still recorded in the manifest.
            snapshot = str(snapshot_id)
        else:
            snapshot = version.snapshot_id
        model = self.train(train_rows, config)
        metrics = self.evaluate(model, validation_df if validation_df is not None else train_rows)
        manifest = build_manifest(
            snapshot,
            source_sha=source_sha,
            image_digest=image_digest,
            data_version=version.version,
        )
        model_version = None
        if self.registry is not None:
            record = self.registry.register(
                str(config.get("model_name", "financial-distress-baseline")),
                str(config.get("artifact_uri", f"local://model/{manifest.digest()}")),
                manifest=manifest.as_dict(),
            )
            model_version = str(record["version"])
        return TrainingResult(model, metrics, version, manifest, model_version)


def run_training(train_df: Any, validation_df: Any | None = None, **kwargs: Any) -> TrainingResult:
    return TrainingPipeline().run(train_df, validation_df, **kwargs)
