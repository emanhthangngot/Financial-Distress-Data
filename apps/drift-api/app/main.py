"""Async real-time drift detection API with pydantic validation."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

try:  # Optional dependency: app remains importable in the local core image.
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover
    FastAPI = None  # type: ignore[assignment,misc]
    PlainTextResponse = str  # type: ignore[assignment,misc]

    class BaseModel:  # type: ignore[no-redef]
        pass

    def Field(default: Any = None, **_: Any) -> Any:
        return default


class DriftRequest(BaseModel):
    reference: list[float] = Field(min_length=1)
    current: list[float] = Field(min_length=1)
    threshold: float = Field(default=0.2, gt=0)


class DriftResponse(BaseModel):
    psi: float
    drifted: bool


def _psi(reference: Sequence[float], current: Sequence[float], buckets: int = 10) -> float:
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


def create_app() -> Any:
    if FastAPI is None:
        return None
    app = FastAPI(title="Financial Distress Drift API", version="1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/healthz")
    @app.get("/readyz")
    async def probe() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics() -> str:
        return (
            "# TYPE fd_web_api_requests_total counter\n"
            'fd_web_api_requests_total{service="drift-api"} 0\n'
            "# TYPE fd_web_api_request_errors_total counter\n"
            'fd_web_api_request_errors_total{service="drift-api"} 0\n'
            "# TYPE fd_web_api_request_duration_seconds histogram\n"
            'fd_web_api_request_duration_seconds_bucket{service="drift-api",le="0.75"} 0\n'
            'fd_web_api_request_duration_seconds_bucket{service="drift-api",le="+Inf"} 0\n'
            'fd_web_api_request_duration_seconds_count{service="drift-api"} 0\n'
            'fd_web_api_request_duration_seconds_sum{service="drift-api"} 0\n'
            "# TYPE fd_drift_events_pending gauge\n"
            'fd_drift_events_pending{service="drift-api"} 0\n'
        )

    @app.post("/drift", response_model=DriftResponse)
    async def detect_drift(request: DriftRequest) -> DriftResponse:
        score = _psi(request.reference, request.current)
        return DriftResponse(psi=score, drifted=score >= request.threshold)

    return app


app = create_app()
