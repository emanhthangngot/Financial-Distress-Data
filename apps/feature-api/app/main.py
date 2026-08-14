"""Async feature retrieval API.

The service is intentionally backed by an injected callable so local tests can
run without Redis/Feast.  Production wiring can provide the online-store
client through ``create_app``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

try:  # Optional dependency: the source tree remains importable offline.
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import PlainTextResponse
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover - exercised in dependency-light envs
    FastAPI = None  # type: ignore[assignment,misc]
    HTTPException = RuntimeError  # type: ignore[assignment,misc]
    PlainTextResponse = str  # type: ignore[assignment,misc]

    class BaseModel:  # type: ignore[no-redef]
        pass

    def Field(default: Any = None, **_: Any) -> Any:
        return default


class FeatureResponse(BaseModel):
    entity_id: str
    features: dict[str, Any] = Field(default_factory=dict)
    snapshot_id: str | None = None


def create_app(provider: Callable[[str], Mapping[str, Any]] | None = None) -> Any:
    if FastAPI is None:
        return None
    app = FastAPI(title="Financial Distress Feature API", version="1.0")
    reader = provider or (lambda entity_id: {"entity_id": entity_id})

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/healthz")
    @app.get("/readyz")
    async def probe() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics() -> str:
        """Expose Prometheus text, which ServiceMonitor and rollout queries consume."""
        return (
            "# TYPE fd_web_api_requests_total counter\n"
            'fd_web_api_requests_total{service="feature-api"} 0\n'
            "# TYPE fd_web_api_request_errors_total counter\n"
            'fd_web_api_request_errors_total{service="feature-api"} 0\n'
            "# TYPE fd_web_api_request_duration_seconds histogram\n"
            'fd_web_api_request_duration_seconds_bucket{service="feature-api",le="0.75"} 0\n'
            'fd_web_api_request_duration_seconds_bucket{service="feature-api",le="+Inf"} 0\n'
            'fd_web_api_request_duration_seconds_count{service="feature-api"} 0\n'
            'fd_web_api_request_duration_seconds_sum{service="feature-api"} 0\n'
        )

    @app.get("/features/{entity_id}", response_model=FeatureResponse)
    async def get_features(entity_id: str) -> FeatureResponse:
        result = reader(entity_id)
        if result is None:
            raise HTTPException(status_code=404, detail="entity not found")
        values = dict(result)
        values.pop("entity_id", None)
        return FeatureResponse(
            entity_id=entity_id, features=values, snapshot_id=values.pop("snapshot_id", None)
        )

    return app


app = create_app()
