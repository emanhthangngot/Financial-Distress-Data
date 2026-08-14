"""Scheduled Phase 2 drift monitoring and retrain trigger wrapper."""

from __future__ import annotations

import os
import urllib.request
from collections.abc import Callable, Sequence
from datetime import timedelta
from typing import Any

from dags._stage1_dag_utils import DEFAULT_ARGS, airflow_imports


def _psi(reference: Sequence[float], current: Sequence[float], buckets: int = 10) -> float:
    import math

    if not reference or not current:
        return 0.0
    lo, hi = min([*reference, *current]), max([*reference, *current])
    if lo == hi:
        return 0.0
    width = (hi - lo) / buckets

    def fractions(values: Sequence[float]) -> list[float]:
        counts = [0] * buckets
        for value in values:
            counts[min(buckets - 1, max(0, int((value - lo) / width)))] += 1
        return [max(count / len(values), 1e-6) for count in counts]

    expected, observed = fractions(reference), fractions(current)
    return sum(
        (after - before) * math.log(after / before)
        for before, after in zip(expected, observed, strict=True)
    )


def trigger_retrain(
    endpoint: str, payload: dict[str, Any], *, timeout: float = 10.0
) -> dict[str, Any]:
    """Call the Kubeflow-compatible retrain endpoint with JSON evidence."""

    import json

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        raw = response.read().decode("utf-8")
    return json.loads(raw) if raw else {"triggered": True}


def run_drift_monitoring_task(
    reference: Sequence[float] | None = None,
    current: Sequence[float] | None = None,
    *,
    threshold: float = 0.2,
    retrain: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compute PSI and trigger retraining when the configured threshold is met."""

    reference_values = list(reference or [])
    current_values = list(current or [])
    psi = _psi(reference_values, current_values)
    drifted = psi >= threshold
    result: dict[str, Any] = {
        "psi": psi,
        "threshold": threshold,
        "drifted": drifted,
        "retrain": None,
    }
    if drifted:
        payload = {"reason": "feature_drift", "psi": psi, "threshold": threshold}
        callback = retrain
        if callback is None:
            endpoint = os.getenv("KUBEFLOW_RETRAIN_ENDPOINT")
            if endpoint:

                def endpoint_callback(body: dict[str, Any]) -> dict[str, Any]:
                    return trigger_retrain(endpoint, body)

                callback = endpoint_callback
        if callback is not None:
            result["retrain"] = callback(payload)
    return result


DAG, PythonOperator = airflow_imports()
DAG_ID = "phase2_drift_monitoring"

if DAG is not None:
    with DAG(
        dag_id=DAG_ID,
        default_args={**DEFAULT_ARGS, "retries": 2, "retry_delay": timedelta(seconds=30)},
        schedule=None,
        catchup=False,
        tags=["financial-distress", "phase2", "ml", "monitoring", "drift"],
    ) as dag:
        PythonOperator(task_id="monitoring", python_callable=run_drift_monitoring_task)
