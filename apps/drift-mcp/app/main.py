"""Async FastAPI facade over the pure Phase 2 drift generator."""

from __future__ import annotations

import asyncio
import time
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, Literal, Protocol

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.drift.generator import apply_drift, build_drift_report
from src.drift.generator_config import DriftScenario, ShiftSpec


class MetricsHook(Protocol):
    def observe(self, route: str, status_code: int, elapsed_seconds: float) -> None: ...

    def observe_tokens(self, model: str, direction: str, count: int) -> None: ...

    def observe_ttft(self, model: str, elapsed_seconds: float) -> None: ...


class NoopMetrics:
    def observe(self, route: str, status_code: int, elapsed_seconds: float) -> None:
        del route, status_code, elapsed_seconds

    def observe_tokens(self, model: str, direction: str, count: int) -> None:
        del model, direction, count

    def observe_ttft(self, model: str, elapsed_seconds: float) -> None:
        del model, elapsed_seconds

    def render(self) -> bytes:
        return b""


class PrometheusMetrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "fd_http_requests_total",
            "HTTP requests completed by the service.",
            ("route", "status"),
            registry=self.registry,
        )
        self.latency = Histogram(
            "fd_http_request_duration_seconds",
            "HTTP request latency.",
            ("route",),
            registry=self.registry,
        )
        self.tokens = Counter(
            "fd_model_tokens_total",
            "Model token counts supplied by agent/model integrations.",
            ("model", "direction"),
            registry=self.registry,
        )
        self.ttft = Histogram(
            "fd_model_ttft_seconds",
            "Model time to first token supplied by model integrations.",
            ("model",),
            registry=self.registry,
        )

    def observe(self, route: str, status_code: int, elapsed_seconds: float) -> None:
        self.requests.labels(route=route, status=str(status_code)).inc()
        self.latency.labels(route=route).observe(elapsed_seconds)

    def observe_tokens(self, model: str, direction: str, count: int) -> None:
        if count < 0:
            raise ValueError("token count cannot be negative")
        self.tokens.labels(model=model, direction=direction).inc(count)

    def observe_ttft(self, model: str, elapsed_seconds: float) -> None:
        if elapsed_seconds < 0:
            raise ValueError("TTFT cannot be negative")
        self.ttft.labels(model=model).observe(elapsed_seconds)

    def render(self) -> bytes:
        return generate_latest(self.registry)


class ShiftPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["multiplicative", "additive"]
    magnitude: float = Field(ge=-1000, le=1000)


class ScenarioPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=128)
    seed: int
    start_quarter: int = Field(ge=1, le=4)
    affected_fraction: float = Field(ge=0, le=1)
    feature_shifts: dict[str, ShiftPayload] = Field(min_length=1, max_length=32)
    target_metric: Literal["debt_to_asset", "close_price"]
    observed_stat: Literal["mean", "std"]
    expected_direction: Literal["increase", "decrease"]
    threshold: float = Field(gt=0, le=10)

    def to_domain(self) -> DriftScenario:
        scenario = DriftScenario(
            name=self.name,
            seed=self.seed,
            start_quarter=self.start_quarter,
            affected_fraction=self.affected_fraction,
            feature_shifts={
                name: ShiftSpec(mode=shift.mode, magnitude=shift.magnitude)
                for name, shift in self.feature_shifts.items()
            },
            target_metric=self.target_metric,
            observed_stat=self.observed_stat,
            expected_direction=self.expected_direction,
            threshold=self.threshold,
        )
        scenario.validate()
        return scenario


class DriftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rows: list[dict[str, Any]] = Field(min_length=1, max_length=10_000)
    scenario: ScenarioPayload

    @model_validator(mode="after")
    def validate_rows(self) -> DriftRequest:
        missing_ticker = [index for index, row in enumerate(self.rows) if not row.get("ticker")]
        if missing_ticker:
            raise ValueError(f"rows require ticker; missing at indexes {missing_ticker[:10]}")
        return self


class DriftResponse(BaseModel):
    report: dict[str, Any]
    affected_tickers: list[str]


class HealthResponse(BaseModel):
    status: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


def _error(status: int, code: str, message: str, details: Any = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(
            error=ErrorDetail(code=code, message=message, details=details)
        ).model_dump(),
    )


def _calculate_drift(payload: DriftRequest) -> DriftResponse:
    scenario = payload.scenario.to_domain()
    drifted = apply_drift(payload.rows, scenario)
    report = build_drift_report(payload.rows, drifted.rows, scenario)
    return DriftResponse(
        report=report,
        affected_tickers=sorted(drifted.affected_tickers),
    )


def create_app(metrics: MetricsHook | None = None, mount_mcp: bool = True) -> FastAPI:
    metric_hook = metrics or PrometheusMetrics()
    mcp_runtime = None
    if mount_mcp:
        from .mcp_server import create_mcp_runtime

        mcp_runtime = create_mcp_runtime()

    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        async with AsyncExitStack() as stack:
            if mcp_runtime is not None:
                await stack.enter_async_context(mcp_runtime.api)
                await stack.enter_async_context(
                    mcp_runtime.application.router.lifespan_context(mcp_runtime.application)
                )
            yield

    application = FastAPI(title="real-time-drift-api", version="1.0.0", lifespan=lifespan)
    application.state.metrics = metric_hook
    if mcp_runtime is not None:
        application.mount("/mcp", mcp_runtime.application)

    @application.middleware("http")
    async def metric_middleware(request: Request, call_next):
        started = time.monotonic()
        response = await call_next(request)
        metric_hook.observe(request.url.path, response.status_code, time.monotonic() - started)
        return response

    @application.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        details = [
            {key: value for key, value in item.items() if key != "ctx"} for item in exc.errors()
        ]
        return _error(
            422,
            "validation_error",
            "request validation failed",
            details,
        )

    @application.get("/healthz", response_model=HealthResponse)
    async def healthz() -> HealthResponse:
        return HealthResponse(status="ok")

    @application.get("/metrics", include_in_schema=False)
    async def metrics_endpoint() -> Response:
        render = getattr(metric_hook, "render", lambda: b"")
        return Response(content=render(), media_type=CONTENT_TYPE_LATEST)

    @application.get("/readyz", response_model=HealthResponse)
    async def readyz() -> HealthResponse:
        return HealthResponse(status="ready")

    @application.post("/v1/drift/report", response_model=DriftResponse)
    async def drift_report(payload: DriftRequest) -> DriftResponse:
        return await asyncio.to_thread(_calculate_drift, payload)

    return application


app = create_app()
