"""
Common contract for source adapters in the financial-distress pipeline.

Defines the ``SourceAdapter`` protocol that all vendor adapters must implement, plus shared helpers
for symbol normalization, pagination, and error classification. Concrete adapters live in sibling
modules.
"""

from __future__ import annotations

from typing import Protocol


class SourceAdapter(Protocol):
    source_name: str

    def fetch_companies(self) -> list[dict]:
        raise NotImplementedError

    def fetch_financial_statements(self, ticker: str, start_year: int, end_year: int) -> list[dict]:
        raise NotImplementedError

    def fetch_market_prices(self, ticker: str, start_year: int, end_year: int) -> list[dict]:
        raise NotImplementedError
