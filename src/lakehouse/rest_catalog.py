"""
Iceberg REST Catalog client — the real Lakekeeper HTTP boundary (phase-04-data-plane.md).

``src/lakehouse/catalog.py``'s ``CatalogConfig(mode="rest")`` has always been accepted but never
backed by a real client — ``load_catalog`` silently returned the in-memory ``LocalIcebergCatalog``
regardless of ``mode``. This module is that real client: it speaks the Iceberg REST Catalog OpenAPI
spec (v1) against a live Lakekeeper instance so ``list_bronze_silver_gold_tables`` can prove the
Bronze/Silver/Gold namespaces are actually registered, not just declared in ``CatalogConfig``.

Never falls back to a fabricated "success" on a network error: every method raises
``RestCatalogError`` (a live-service failure) or ``CatalogError`` (a contract violation) rather
than returning an empty list that could be misread as "the catalog has no tables yet".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from src.lakehouse.catalog import CatalogConfig, CatalogError

MEDALLION_NAMESPACES: tuple[str, ...] = ("bronze", "silver", "gold")


class RestCatalogError(RuntimeError):
    """Raised when the live Lakekeeper REST catalog is unreachable or returns an error."""


class HttpClient(Protocol):
    """The subset of ``requests``' interface this module needs — injectable for tests."""

    def get(self, url: str, *, headers: dict[str, str], timeout: float) -> Any: ...


def _default_http_client() -> HttpClient:
    try:
        import requests
    except ImportError as exc:  # pragma: no cover - requests is a declared runtime dependency
        raise RestCatalogError(
            "the 'requests' package is required for RestIcebergCatalog; install the 'runtime' "
            "optional dependency group"
        ) from exc
    return requests


@dataclass(frozen=True)
class TableIdentifier:
    namespace: str
    name: str

    @property
    def full_name(self) -> str:
        return f"{self.namespace}.{self.name}"


class RestIcebergCatalog:
    """Real Iceberg REST Catalog (Lakekeeper) client.

    Talks the v1 REST spec: ``GET {uri}/v1/{prefix}/namespaces`` and
    ``GET {uri}/v1/{prefix}/namespaces/{namespace}/tables``. ``prefix`` defaults to the catalog
    name (Lakekeeper's convention: one warehouse per catalog name), overridable for deployments
    that key warehouses differently.
    """

    def __init__(
        self,
        config: CatalogConfig,
        *,
        prefix: str | None = None,
        http_client: HttpClient | None = None,
        request_timeout_seconds: float = 10.0,
    ) -> None:
        if config.mode != "rest":
            raise CatalogError(
                f"RestIcebergCatalog requires CatalogConfig(mode='rest'), got {config.mode!r}"
            )
        self.config = config
        self.prefix = prefix or config.name
        self._http = http_client or _default_http_client()
        self.request_timeout_seconds = request_timeout_seconds

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"
        return headers

    def _get(self, path: str) -> dict[str, Any]:
        url = f"{self.config.uri.rstrip('/')}{path}"
        try:
            response = self._http.get(
                url, headers=self._headers(), timeout=self.request_timeout_seconds
            )
        except Exception as exc:  # noqa: BLE001 - network errors vary by transport
            raise RestCatalogError(f"request to {url} failed: {exc}") from exc
        status = getattr(response, "status_code", None)
        if status is None or status >= 400:
            raise RestCatalogError(f"{url} returned status {status}")
        try:
            return response.json()
        except Exception as exc:  # noqa: BLE001
            raise RestCatalogError(f"{url} returned a non-JSON body: {exc}") from exc

    def list_namespaces(self) -> list[str]:
        """GET /v1/{prefix}/namespaces — top-level namespaces (bronze/silver/gold/ml/ops)."""
        payload = self._get(f"/v1/{self.prefix}/namespaces")
        namespaces = payload.get("namespaces", [])
        # Each entry is a list of path segments, e.g. ["bronze"] or ["bronze", "sub"].
        return [".".join(segments) for segments in namespaces]

    def namespace_exists(self, namespace: str) -> bool:
        return namespace in self.list_namespaces()

    def list_tables(self, namespace: str) -> list[TableIdentifier]:
        """GET /v1/{prefix}/namespaces/{namespace}/tables."""
        payload = self._get(f"/v1/{self.prefix}/namespaces/{namespace}/tables")
        identifiers = payload.get("identifiers", [])
        return [
            TableIdentifier(namespace=entry.get("namespace", [namespace])[-1], name=entry["name"])
            for entry in identifiers
        ]

    def table_exists(self, namespace: str, table_name: str) -> bool:
        return any(t.name == table_name for t in self.list_tables(namespace))

    def list_bronze_silver_gold_tables(self) -> dict[str, list[TableIdentifier]]:
        """The phase-04 acceptance check: list every registered table per medallion zone.

        Raises RestCatalogError (not an empty dict) if any zone's namespace is unreachable or
        does not exist — an unregistered zone is a real gap, never silently reported as "0
        tables" alongside zones that did resolve.
        """
        live_namespaces = set(self.list_namespaces())
        missing = [ns for ns in MEDALLION_NAMESPACES if ns not in live_namespaces]
        if missing:
            raise RestCatalogError(
                f"medallion namespace(s) not registered in Lakekeeper: {missing}"
            )
        return {zone: self.list_tables(zone) for zone in MEDALLION_NAMESPACES}


__all__ = [
    "MEDALLION_NAMESPACES",
    "HttpClient",
    "RestCatalogError",
    "RestIcebergCatalog",
    "TableIdentifier",
]
