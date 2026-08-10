"""Async FastAPI facade over the pure Phase 2 drift generator."""

from __future__ import annotations

import asyncio
import time
from contextlib import AsyncExitStack, asynccontextmanager, nullcontext
from typing import Any, Literal, Protocol

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.drift.generator import apply_drift, build_drift_report
from src.drift.generator_config import DriftScenario, ShiftSpec
from src.observability.telemetry import (
    CONTENT_TYPE_LATEST,
    Telemetry,
    metadata_from_headers,
    redact_fields,
)


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


class PrometheusMetrics(Telemetry):
    def __init__(self, service: str = "drift-mcp") -> None:
        super().__init__(service=service)


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

        mcp_runtime = create_mcp_runtime(
            metric_hook if callable(getattr(metric_hook, "observe_tool_call", None)) else None
        )

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
        route = request.url.path
        observe_http = getattr(metric_hook, "observe_http", metric_hook.observe)
        request_in_flight = getattr(metric_hook, "request_in_flight", None)
        if callable(request_in_flight):
            request_in_flight(route, 1)
        metadata = metadata_from_headers(request.headers).as_attributes()
        span_factory = getattr(metric_hook, "span", None)
        span_context = (
            span_factory(
                "drift_mcp.http_request",
                {
                    **metadata,
                    "operation": route,
                    "method": request.method,
                },
                headers=request.headers,
            )
            if callable(span_factory)
            else nullcontext()
        )
        try:
            with span_context as span:
                try:
                    response = await call_next(request)
                except Exception as exc:
                    elapsed = time.monotonic() - started
                    if callable(getattr(metric_hook, "observe_http", None)):
                        observe_http(route, 500, elapsed, request.method)
                    else:
                        metric_hook.observe(route, 500, elapsed)
                    failure = getattr(metric_hook, "observe_failure", None)
                    if callable(failure):
                        failure("http.request", type(exc).__name__)
                    raise
                if span is not None:
                    span.set_attribute("status_code", response.status_code)
                elapsed = time.monotonic() - started
                if callable(getattr(metric_hook, "observe_http", None)):
                    observe_http(route, response.status_code, elapsed, request.method)
                else:
                    metric_hook.observe(route, response.status_code, elapsed)
                return response
        finally:
            if callable(request_in_flight):
                request_in_flight(route, -1)

    @application.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        details = [
            {key: value for key, value in item.items() if key != "ctx"} for item in exc.errors()
        ]
        return _error(
            422,
            "validation_error",
            "request validation failed",
            redact_fields({"details": details})["details"],
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
