"""Async FastAPI service for dependency-injected online feature and RAG reads."""

from __future__ import annotations

import asyncio
import os
import time
from contextlib import AsyncExitStack, asynccontextmanager, nullcontext
from pathlib import Path
from typing import Annotated, Any, Protocol

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from src.observability.telemetry import (
    CONTENT_TYPE_LATEST,
    Telemetry,
    metadata_from_headers,
    redact_fields,
)

Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")]


class OnlineFeatureClient(Protocol):
    async def get_by_id(self, user_id: str, feature_names: tuple[str, ...]) -> dict[str, Any]: ...

    async def ready(self) -> bool: ...


class RagLookupClient(Protocol):
    async def get_by_id(self, chunk_id: str) -> dict[str, Any] | None: ...

    async def ready(self) -> bool: ...


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
    """Per-app registry with legacy aliases and service-labeled metrics."""

    def __init__(self, service: str = "feature-mcp") -> None:
        super().__init__(service=service)


class UnconfiguredFeatureClient:
    async def get_by_id(self, user_id: str, feature_names: tuple[str, ...]) -> dict[str, Any]:
        del user_id, feature_names
        raise ServiceUnavailable("online feature client is not configured")

    async def ready(self) -> bool:
        return False


class UnconfiguredRagClient:
    async def get_by_id(self, chunk_id: str) -> dict[str, Any] | None:
        del chunk_id
        raise ServiceUnavailable("RAG lookup client is not configured")

    async def ready(self) -> bool:
        return False


class ServiceUnavailable(RuntimeError):
    pass


class FeastOnlineFeatureClient:
    """Lazy Feast adapter; synchronous SDK work never blocks the event loop."""

    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = str(repo_path)
        self._store: Any | None = None

    def _feature_store(self) -> Any:
        if self._store is None:
            from feast import FeatureStore

            path = Path(self.repo_path)
            if path.suffix in {".yaml", ".yml"}:
                self._store = FeatureStore(fs_yaml_file=path)
            else:
                self._store = FeatureStore(repo_path=self.repo_path)
        return self._store

    def _get_online_features(self, user_id: str, feature_names: tuple[str, ...]) -> dict[str, Any]:
        response = self._feature_store().get_online_features(
            features=list(feature_names),
            entity_rows=[{"ticker": user_id}],
        )
        values = response.to_dict()
        result: dict[str, Any] = {}
        for requested in feature_names:
            output_name = requested.rsplit(":", 1)[-1]
            candidates = (requested, output_name)
            column = next((values[name] for name in candidates if name in values), None)
            result[output_name] = column[0] if column else None
        return result

    async def get_by_id(self, user_id: str, feature_names: tuple[str, ...]) -> dict[str, Any]:
        try:
            return await asyncio.to_thread(self._get_online_features, user_id, feature_names)
        except Exception as exc:
            raise ServiceUnavailable("online feature lookup failed") from exc

    async def ready(self) -> bool:
        try:
            await asyncio.to_thread(self._feature_store)
            host = os.getenv("FEAST_REDIS_HOST", "platform-redis")
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, int(os.getenv("FEAST_REDIS_PORT", "6379"))),
                timeout=2.0,
            )
            del reader
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False


class PostgresRagLookupClient:
    """Short-lived psycopg adapter for by-ID RAG reads and readiness."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _lookup(self, chunk_id: str) -> dict[str, Any] | None:
        import psycopg

        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT chunk_id, chunk_text, source_uri, company, report_date, access_class
                FROM ml.rag_chunk
                WHERE chunk_id = %s
                """,
                (chunk_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        names = ("chunk_id", "chunk_text", "source_uri", "company", "report_date", "access_class")
        return dict(zip(names, row, strict=True))

    async def get_by_id(self, chunk_id: str) -> dict[str, Any] | None:
        try:
            return await asyncio.to_thread(self._lookup, chunk_id)
        except Exception as exc:
            raise ServiceUnavailable("RAG lookup failed") from exc

    def _ready(self) -> bool:
        import psycopg

        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone() == (1,)

    async def ready(self) -> bool:
        try:
            return await asyncio.to_thread(self._ready)
        except Exception:
            return False


def production_clients_from_env() -> tuple[OnlineFeatureClient, RagLookupClient]:
    feast_repo = os.getenv("FEAST_REPO_PATH")
    rag_dsn = os.getenv("RAG_DATABASE_URL")
    if not rag_dsn and os.getenv("PLATFORM_PG_PASSWORD"):
        rag_dsn = (
            f"host={os.getenv('PLATFORM_PG_HOST', 'platform-postgres')} "
            f"port={os.getenv('PLATFORM_PG_PORT', '5432')} "
            f"dbname={os.getenv('PLATFORM_PG_DATABASE', 'ml')} "
            f"user={os.getenv('PLATFORM_PG_USER', 'platform')} "
            f"password={os.environ['PLATFORM_PG_PASSWORD']} connect_timeout=3"
        )
    features: OnlineFeatureClient = (
        FeastOnlineFeatureClient(feast_repo) if feast_repo else UnconfiguredFeatureClient()
    )
    rag: RagLookupClient = PostgresRagLookupClient(rag_dsn) if rag_dsn else UnconfiguredRagClient()
    return features, rag


class FeatureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: Identifier
    feature_names: tuple[Identifier, ...] = Field(min_length=1, max_length=64)


class FeatureResponse(BaseModel):
    user_id: str
    features: dict[str, Any]


class RagRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: Identifier


class RagChunk(BaseModel):
    model_config = ConfigDict(extra="allow")
    chunk_id: str
    chunk_text: str = Field(max_length=100_000)
    source_uri: str = Field(min_length=1, max_length=2048)


class HealthResponse(BaseModel):
    status: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


def _error(status: int, code: str, message: str, details: Any = None) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, details=details))
    return JSONResponse(status_code=status, content=body.model_dump())


def create_app(
    feature_client: OnlineFeatureClient | None = None,
    rag_client: RagLookupClient | None = None,
    metrics: MetricsHook | None = None,
    mount_mcp: bool = True,
) -> FastAPI:
    production_features, production_rag = production_clients_from_env()
    features = feature_client or production_features
    rag = rag_client or production_rag
    metric_hook = metrics or PrometheusMetrics()
    mcp_runtime = None
    if mount_mcp:
        from .mcp_server import create_mcp_runtime

        mcp_runtime = create_mcp_runtime(
            metric_hook if callable(getattr(metric_hook, "observe_tool_call", None)) else None
        )

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        async with AsyncExitStack() as stack:
            application.state.feature_client = features
            application.state.rag_client = rag
            if mcp_runtime is not None:
                await stack.enter_async_context(mcp_runtime.api)
                await stack.enter_async_context(
                    mcp_runtime.application.router.lifespan_context(mcp_runtime.application)
                )
            yield

    application = FastAPI(title="feature-rag-api", version="1.0.0", lifespan=lifespan)
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
                "feature_mcp.http_request",
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
                    (
                        observe_http(route, 500, elapsed, request.method)
                        if callable(getattr(metric_hook, "observe_http", None))
                        else metric_hook.observe(route, 500, elapsed)
                    )
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

    @application.exception_handler(ServiceUnavailable)
    async def unavailable_error(_request: Request, exc: ServiceUnavailable):
        return _error(503, "dependency_unavailable", str(exc))

    @application.get("/healthz", response_model=HealthResponse)
    async def healthz() -> HealthResponse:
        return HealthResponse(status="ok")

    @application.get("/metrics", include_in_schema=False)
    async def metrics_endpoint() -> Response:
        render = getattr(metric_hook, "render", lambda: b"")
        return Response(content=render(), media_type=CONTENT_TYPE_LATEST)

    @application.get(
        "/readyz", response_model=HealthResponse, responses={503: {"model": ErrorResponse}}
    )
    async def readyz() -> HealthResponse | JSONResponse:
        if await features.ready() and await rag.ready():
            return HealthResponse(status="ready")
        return _error(503, "not_ready", "one or more lookup dependencies are unavailable")

    @application.post("/v1/features/by-id", response_model=FeatureResponse)
    async def feature_by_id(payload: FeatureRequest) -> FeatureResponse:
        values = await features.get_by_id(payload.user_id, payload.feature_names)
        return FeatureResponse(user_id=payload.user_id, features=values)

    @application.post(
        "/v1/rag/by-id",
        response_model=RagChunk,
        responses={404: {"model": ErrorResponse}},
    )
    async def rag_by_id(payload: RagRequest) -> RagChunk | JSONResponse:
        chunk = await rag.get_by_id(payload.chunk_id)
        if chunk is None:
            return _error(404, "not_found", f"chunk {payload.chunk_id!r} was not found")
        return RagChunk.model_validate(chunk)

    return application


app = create_app()
