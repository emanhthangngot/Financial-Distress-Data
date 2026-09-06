"""RestIcebergCatalog contract tests (phase-04-data-plane.md).

Never hits a live Lakekeeper: a fake HTTP client is injected via the
``http_client`` constructor parameter, so these tests exercise the real
request/response handling without a network dependency.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.lakehouse.catalog import CatalogConfig, CatalogError
from src.lakehouse.rest_catalog import (
    RestCatalogError,
    RestIcebergCatalog,
    TableIdentifier,
)


class FakeResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


class FakeHttpClient:
    def __init__(self, routes: dict[str, FakeResponse]) -> None:
        self.routes = routes
        self.requested_urls: list[str] = []

    def get(self, url: str, *, headers: dict[str, str], timeout: float) -> FakeResponse:
        self.requested_urls.append(url)
        for path, response in self.routes.items():
            if url.endswith(path):
                return response
        raise AssertionError(f"unexpected URL requested: {url}")


def _rest_config() -> CatalogConfig:
    return CatalogConfig(name="lakekeeper", uri="http://lakekeeper:8181/catalog", mode="rest")


def test_rest_catalog_requires_rest_mode() -> None:
    memory_config = CatalogConfig(mode="memory")
    with pytest.raises(CatalogError, match="mode='rest'"):
        RestIcebergCatalog(memory_config, http_client=FakeHttpClient({}))


def test_list_namespaces_parses_segment_lists() -> None:
    client = FakeHttpClient(
        {
            "/v1/lakekeeper/namespaces": FakeResponse(
                200, {"namespaces": [["bronze"], ["silver"], ["gold"]]}
            )
        }
    )
    catalog = RestIcebergCatalog(_rest_config(), http_client=client)

    assert catalog.list_namespaces() == ["bronze", "silver", "gold"]


def test_namespace_exists_true_and_false() -> None:
    client = FakeHttpClient(
        {"/v1/lakekeeper/namespaces": FakeResponse(200, {"namespaces": [["bronze"]]})}
    )
    catalog = RestIcebergCatalog(_rest_config(), http_client=client)

    assert catalog.namespace_exists("bronze") is True
    assert catalog.namespace_exists("silver") is False


def test_list_tables_returns_identifiers() -> None:
    client = FakeHttpClient(
        {
            "/v1/lakekeeper/namespaces/gold/tables": FakeResponse(
                200,
                {
                    "identifiers": [
                        {"namespace": ["gold"], "name": "dim_company"},
                        {"namespace": ["gold"], "name": "fact_financial_statement"},
                    ]
                },
            )
        }
    )
    catalog = RestIcebergCatalog(_rest_config(), http_client=client)

    tables = catalog.list_tables("gold")
    assert tables == [
        TableIdentifier(namespace="gold", name="dim_company"),
        TableIdentifier(namespace="gold", name="fact_financial_statement"),
    ]


def test_table_exists_true_and_false() -> None:
    client = FakeHttpClient(
        {
            "/v1/lakekeeper/namespaces/gold/tables": FakeResponse(
                200, {"identifiers": [{"namespace": ["gold"], "name": "dim_company"}]}
            )
        }
    )
    catalog = RestIcebergCatalog(_rest_config(), http_client=client)

    assert catalog.table_exists("gold", "dim_company") is True
    assert catalog.table_exists("gold", "fact_market_price") is False


def test_list_bronze_silver_gold_tables_success() -> None:
    client = FakeHttpClient(
        {
            "/v1/lakekeeper/namespaces": FakeResponse(
                200, {"namespaces": [["bronze"], ["silver"], ["gold"], ["ml"], ["ops"]]}
            ),
            "/v1/lakekeeper/namespaces/bronze/tables": FakeResponse(
                200, {"identifiers": [{"namespace": ["bronze"], "name": "raw_companies"}]}
            ),
            "/v1/lakekeeper/namespaces/silver/tables": FakeResponse(
                200, {"identifiers": [{"namespace": ["silver"], "name": "stg_companies"}]}
            ),
            "/v1/lakekeeper/namespaces/gold/tables": FakeResponse(
                200, {"identifiers": [{"namespace": ["gold"], "name": "dim_company"}]}
            ),
        }
    )
    catalog = RestIcebergCatalog(_rest_config(), http_client=client)

    result = catalog.list_bronze_silver_gold_tables()
    assert set(result.keys()) == {"bronze", "silver", "gold"}
    assert result["bronze"] == [TableIdentifier(namespace="bronze", name="raw_companies")]


def test_list_bronze_silver_gold_tables_fails_closed_when_namespace_missing() -> None:
    """A live catalog with only bronze/silver registered must raise, not silently omit gold."""
    client = FakeHttpClient(
        {"/v1/lakekeeper/namespaces": FakeResponse(200, {"namespaces": [["bronze"], ["silver"]]})}
    )
    catalog = RestIcebergCatalog(_rest_config(), http_client=client)

    with pytest.raises(RestCatalogError, match="gold"):
        catalog.list_bronze_silver_gold_tables()


def test_error_status_raises_rest_catalog_error() -> None:
    client = FakeHttpClient({"/v1/lakekeeper/namespaces": FakeResponse(503, {})})
    catalog = RestIcebergCatalog(_rest_config(), http_client=client)

    with pytest.raises(RestCatalogError, match="503"):
        catalog.list_namespaces()


def test_connection_error_raises_rest_catalog_error() -> None:
    class BrokenClient:
        def get(self, url: str, *, headers: dict[str, str], timeout: float) -> Any:
            raise ConnectionError("connection refused")

    catalog = RestIcebergCatalog(_rest_config(), http_client=BrokenClient())

    with pytest.raises(RestCatalogError, match="connection refused"):
        catalog.list_namespaces()


def test_bearer_token_is_sent_when_configured() -> None:
    captured_headers: dict[str, str] = {}

    class RecordingClient:
        def get(self, url: str, *, headers: dict[str, str], timeout: float) -> FakeResponse:
            captured_headers.update(headers)
            return FakeResponse(200, {"namespaces": []})

    config = CatalogConfig(
        name="lakekeeper", uri="http://lakekeeper:8181/catalog", mode="rest", token="secret-token"
    )
    catalog = RestIcebergCatalog(config, http_client=RecordingClient())
    catalog.list_namespaces()

    assert captured_headers["Authorization"] == "Bearer secret-token"
