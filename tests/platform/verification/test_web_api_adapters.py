"""Fixture-backed adapter and middleware coverage for the Phase 05 Web APIs."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from tests.platform.apps.conftest import load_app_module


class MinimalMetrics:
    def __init__(self) -> None:
        self.events: list[tuple[str, int]] = []

    def observe(self, route: str, status_code: int, _elapsed_seconds: float) -> None:
        self.events.append((route, status_code))

    def observe_tokens(self, _model: str, _direction: str, _count: int) -> None:
        pass

    def observe_ttft(self, _model: str, _elapsed_seconds: float) -> None:
        pass

    def render(self) -> bytes:
        return b"minimal-metrics"


class RichMetrics(MinimalMetrics):
    def __init__(self) -> None:
        super().__init__()
        self.in_flight: list[tuple[str, int]] = []
        self.failures: list[tuple[str, str]] = []
        self.spans: list[str] = []

    def observe_http(
        self, route: str, status_code: int, elapsed_seconds: float, method: str
    ) -> None:
        del method
        self.events.append((route, status_code))
        assert elapsed_seconds >= 0

    def request_in_flight(self, route: str, amount: int) -> None:
        self.in_flight.append((route, amount))

    def observe_failure(self, operation: str, reason: str) -> None:
        self.failures.append((operation, reason))

    @contextmanager
    def span(self, name: str, _attributes, *, headers):
        del headers
        self.spans.append(name)
        yield SimpleNamespace(set_attribute=lambda _name, _value: None)


class FakeWriter:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        return None


class FakeCursor:
    def __init__(self, row):
        self.row = row
        self.statements: list[tuple[str, object]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def execute(self, statement: str, parameters=None) -> None:
        self.statements.append((statement, parameters))

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, row):
        self.cursor_instance = FakeCursor(row)

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def cursor(self):
        return self.cursor_instance


@pytest.mark.asyncio
async def test_feature_adapters_and_production_configuration(monkeypatch) -> None:
    module = load_app_module("feature-mcp", "main")
    monkeypatch.delenv("FEAST_REPO_PATH", raising=False)
    monkeypatch.delenv("RAG_DATABASE_URL", raising=False)
    monkeypatch.delenv("PHASE2_PG_PASSWORD", raising=False)
    features, rag = module.production_clients_from_env()
    assert isinstance(features, module.UnconfiguredFeatureClient)
    assert isinstance(rag, module.UnconfiguredRagClient)

    monkeypatch.setenv("PHASE2_PG_PASSWORD", "secret")
    _, password_rag = module.production_clients_from_env()
    assert isinstance(password_rag, module.PostgresRagLookupClient)
    assert "password=secret" in password_rag._dsn

    class Result:
        def to_dict(self):
            return {"company_features:risk_score": [0.73], "other": [None]}

    class Store:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def get_online_features(self, **_kwargs):
            return Result()

    fake_feast = ModuleType("feast")
    fake_feast.FeatureStore = Store
    monkeypatch.setitem(sys.modules, "feast", fake_feast)
    yaml_adapter = module.FeastOnlineFeatureClient("feature_repo/feature_store.yaml")
    assert yaml_adapter._feature_store().kwargs == {
        "fs_yaml_file": module.Path("feature_repo/feature_store.yaml")
    }
    repo_adapter = module.FeastOnlineFeatureClient("feature_repo/structured")
    assert repo_adapter._feature_store().kwargs == {"repo_path": "feature_repo/structured"}
    assert await repo_adapter.get_by_id("AAA", ("company_features:risk_score",)) == {
        "risk_score": 0.73
    }

    async def run_in_thread(function, *args):
        return function(*args)

    monkeypatch.setattr(module.asyncio, "to_thread", run_in_thread)
    unavailable_store = module.FeastOnlineFeatureClient("feature_repo/structured")
    unavailable_store._store = SimpleNamespace(
        get_online_features=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    with pytest.raises(module.ServiceUnavailable, match="online feature lookup"):
        await unavailable_store.get_by_id("AAA", ("risk_score",))

    writer = FakeWriter()
    monkeypatch.setattr(
        module.asyncio, "open_connection", AsyncMock(return_value=(object(), writer))
    )
    yaml_adapter._store = Store()
    assert await yaml_adapter.ready() is True
    assert writer.closed is True


@pytest.mark.asyncio
async def test_postgres_rag_adapter_and_feature_endpoints(monkeypatch) -> None:
    module = load_app_module("feature-mcp", "main")
    row = ("chunk-1", "excerpt", "fixture://report", "AAA", "2026-01-01", "public")
    connection = FakeConnection(row)
    fake_psycopg = ModuleType("psycopg")
    fake_psycopg.connect = lambda _dsn: connection
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)

    async def run_in_thread(function, *args):
        return function(*args)

    monkeypatch.setattr(module.asyncio, "to_thread", run_in_thread)
    adapter = module.PostgresRagLookupClient("postgresql://fixture")
    assert await adapter.get_by_id("chunk-1") == dict(
        zip(
            ("chunk_id", "chunk_text", "source_uri", "company", "report_date", "access_class"),
            row,
            strict=True,
        )
    )
    assert await adapter.get_by_id("same-row") == dict(
        zip(
            ("chunk_id", "chunk_text", "source_uri", "company", "report_date", "access_class"),
            row,
            strict=True,
        )
    )
    missing_connection = FakeConnection(None)
    fake_psycopg.connect = lambda _dsn: missing_connection
    assert await adapter.get_by_id("missing") is None
    fake_psycopg.connect = lambda _dsn: (_ for _ in ()).throw(RuntimeError("down"))
    with pytest.raises(module.ServiceUnavailable, match="RAG lookup failed"):
        await adapter.get_by_id("chunk-1")

    ready_connection = FakeConnection((1,))
    fake_psycopg.connect = lambda _dsn: ready_connection
    assert await adapter.ready() is True
    fake_psycopg.connect = lambda _dsn: (_ for _ in ()).throw(RuntimeError("down"))
    assert await adapter.ready() is False

    features = AsyncMock()
    features.get_by_id.side_effect = [{"risk_score": 0.73}, module.ServiceUnavailable("gone")]
    features.ready.return_value = True
    rag = AsyncMock()
    rag.get_by_id.return_value = None
    rag.ready.return_value = True
    app = module.create_app(features, rag, MinimalMetrics(), mount_mcp=False)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        feature_payload = {"user_id": "AAA", "feature_names": ["risk_score"]}
        assert (await client.post("/v1/features/by-id", json=feature_payload)).status_code == 200
        assert (await client.post("/v1/features/by-id", json=feature_payload)).status_code == 503
        assert (await client.post("/v1/rag/by-id", json={"chunk_id": "missing"})).status_code == 404
        assert (await client.get("/metrics")).text == "minimal-metrics"


@pytest.mark.asyncio
async def test_web_api_middleware_and_lifespans_cover_failure_paths() -> None:
    for app_name in ("feature-mcp", "drift-mcp"):
        module = load_app_module(app_name, "main")
        for metrics in (RichMetrics(), MinimalMetrics()):
            if app_name == "feature-mcp":
                app = module.create_app(AsyncMock(), AsyncMock(), metrics, mount_mcp=False)
            else:
                app = module.create_app(metrics, mount_mcp=False)

            async with app.router.lifespan_context(app):
                if app_name == "feature-mcp":
                    assert app.state.feature_client is not None
                    assert app.state.rag_client is not None
            app.add_api_route(
                "/boom",
                lambda: (_ for _ in ()).throw(RuntimeError("boom")),
                methods=["GET"],
            )
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                base_url="http://test",
            ) as client:
                assert (await client.get("/healthz")).status_code == 200
                response = await client.get("/boom", headers={"x-request-id": "req-1"})
            assert response.status_code == 500
            assert ("/boom", 500) in metrics.events
            if isinstance(metrics, RichMetrics):
                assert ("http.request", "RuntimeError") in metrics.failures
                assert ("/boom", 1) in metrics.in_flight
                assert ("/boom", -1) in metrics.in_flight
                assert metrics.spans


def test_drift_noop_metrics_and_domain_payload() -> None:
    module = load_app_module("drift-mcp", "main")
    metrics = module.NoopMetrics()
    metrics.observe("/test", 200, 0.1)
    metrics.observe_tokens("model", "input", 2)
    metrics.observe_ttft("model", 0.1)
    assert metrics.render() == b""
    payload = module.ScenarioPayload(
        name="stress",
        seed=1,
        start_quarter=1,
        affected_fraction=0.5,
        feature_shifts={"close_price": {"mode": "additive", "magnitude": 1}},
        target_metric="close_price",
        observed_stat="mean",
        expected_direction="increase",
        threshold=0.1,
    )
    assert payload.to_domain().name == "stress"
