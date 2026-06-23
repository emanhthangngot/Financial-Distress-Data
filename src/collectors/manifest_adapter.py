"""W24 Idea 2 - declarative ingestion manifest adapter.

Reads ``configs/ingestion_manifest.yaml`` and exposes a single
``fetch(symbol, source_id)`` entry point that dispatches to a
per-endpoint handler. The fixture handler is offline-safe and ships in
this module so the adapter can be exercised in tests and CI without
network access. Live endpoints are intentionally not implemented: the
manifest is a declaration of intent, and turning a source on is an
explicit code-reviewable action.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

# Handler signature: ``(symbol, field_map) -> dict`` where every key in
# ``field_map`` must appear in the returned record.
Handler = Callable[[str, dict[str, str]], dict[str, Any]]


def _fixture_handler(symbol: str, field_map: dict[str, str]) -> dict[str, Any]:
    """Return a deterministic synthetic record for ``symbol``.

    The fixture handler exists so the manifest can be exercised in CI
    and local development without touching the network. It produces a
    record whose keys line up with the source's ``field_map``.
    """
    ts = datetime.now(UTC).isoformat()
    raw = {
        "symbol": symbol,
        "close_price": 100.0,
        "volume": 1000,
        "ts": ts,
    }
    return {manifest_key: raw[handler_key] for manifest_key, handler_key in field_map.items()}


# Endpoint dispatch table. Add a new entry here when implementing a
# live handler; the manifest just references the endpoint key.
_HANDLERS: dict[str, Handler] = {
    "fixture": _fixture_handler,
}


class ManifestAdapter:
    """Adapter that dispatches ``fetch()`` to per-source handlers.

    Parameters
    ----------
    manifest_path
        Path to the YAML manifest. Must contain a top-level ``sources``
        list whose entries expose the required fields.
    """

    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = Path(manifest_path)
        if not self.manifest_path.exists():
            raise FileNotFoundError(
                f"manifest not found: {self.manifest_path}"
            )
        raw = yaml.safe_load(self.manifest_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or "sources" not in raw:
            raise ValueError(
                f"manifest {self.manifest_path} missing 'sources' list"
            )
        sources = raw["sources"]
        if not isinstance(sources, list):
            raise ValueError(
                f"manifest {self.manifest_path} 'sources' must be a list"
            )
        self._sources: list[dict[str, Any]] = list(sources)

    def sources(self) -> list[dict[str, Any]]:
        """Return the list of source declarations."""
        return list(self._sources)

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        for src in self._sources:
            if src.get("source_id") == source_id:
                return src
        return None

    def fetch(self, symbol: str, source_id: str) -> dict[str, Any] | None:
        """Return a record for ``symbol`` from ``source_id``.

        Returns ``None`` if the source is missing or disabled. Raises
        ``KeyError`` if the source's ``endpoint`` has no registered
        handler.
        """
        src = self.get_source(source_id)
        if src is None:
            return None
        if not src.get("enabled", False):
            return None
        endpoint = src.get("endpoint")
        handler = _HANDLERS.get(endpoint)
        if handler is None:
            raise KeyError(
                f"no handler registered for endpoint {endpoint!r}"
            )
        field_map = src.get("field_map") or {}
        if not isinstance(field_map, dict):
            raise ValueError(
                f"source {source_id} 'field_map' must be a dict"
            )
        return handler(symbol, field_map)
