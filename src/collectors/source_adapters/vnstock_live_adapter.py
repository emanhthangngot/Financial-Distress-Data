"""
Live vnstock adapter — the real Vietnamese market data source (phase-04-data-plane.md).

Wraps vnstock 4.0.7's Unified UI (``Listing``, ``Quote``, ``Finance``) behind the same
three-method interface ``VnstockFixtureAdapter`` exposes, so callers can swap adapters without
touching downstream code. Opt-in: importing this module never requires ``vnstock`` to be
installed — it is imported lazily inside each fetch call, matching ADR-020's fixture-default /
live-opt-in design. The fixture adapter stays the CI path.

Unit facts this adapter encodes (ADR-020, measured against vnstock 4.0.7 this session):

- Financial statements (KBS and VCI both) arrive in whole VND đồng — no scale conversion needed.
- Prices (KBS) arrive in nghìn đồng — multiplied by 1000 here so the lakehouse has one money unit
  (F17). ``docs/07_data_contracts.md`` must not claim vnstock returns prices in VND.
- The free tier hard-caps financial statements at 4 periods per ``period=`` value, regardless of
  the requested date range (measured: ``period='quarter'`` always returns exactly the four most
  recent quarters). Periods outside that window are never fetched — the caller (an Airflow DAG /
  generator fallback) decides how to fill the gap, not this adapter.

SECURITY: ``vnstock`` depends on ``vnai``, which runs a first-use setup routine
(``vnai.setup()``) that does hardware fingerprinting and, observed 2026-09-05 in this
repo's own working tree, appended an "AI coding assistant" auto-bootstrap block instructing
an AI agent to execute further setup commands directly into this project's ``AGENTS.md`` —
a file AI coding agents read and follow as instructions. That injected content was reverted
unread/unexecuted before being committed anywhere. Treat any unreviewed change to
``AGENTS.md``/``CLAUDE.md`` appearing after installing or first-using ``vnstock`` as
untrusted third-party content, not a project decision — diff it before trusting it, and
never execute instructions from it. Prefer running this adapter (and any environment where
``vnstock`` is imported for the first time) from a directory with no ``AGENTS.md``/agent
instruction file, or audit those files immediately after.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any, Protocol

# Balance sheet / income statement / cash flow item_id -> our schema field.
# Measured against a live VNM call, vnstock 4.0.7, source='vci' (2026-09-05).
_BALANCE_SHEET_FIELDS = {
    "total_assets": "total_assets",
    "current_assets": "current_assets",
    "current_liabilities": "current_liabilities",
    "liabilities": "total_liabilities",
    "owners_equity": "equity",
    "undistributed_earnings": "retained_earnings",
}
_INCOME_STATEMENT_FIELDS = {
    "net_sales": "revenue",
    "operating_profit_loss": "ebit",
    "interest_expenses": "interest_expense",
    "net_profit_loss_after_tax": "net_income",
}
_CASH_FLOW_FIELDS = {
    "net_cash_inflows_outflows_from_operating_activities": "operating_cash_flow",
}


class MetadataSink(Protocol):
    """The subset of MetadataWriter this adapter uses for checkpointing/failure routing."""

    def log_source_request(self, **kwargs: Any) -> str: ...
    def log_failed_record(self, **kwargs: Any) -> None: ...
    def upsert_collector_checkpoint(self, **kwargs: Any) -> None: ...


class VnstockUnavailableError(RuntimeError):
    """Raised when ``vnstock`` is not installed. Opt-in adapter, not a hard dependency."""


def _import_vnstock() -> Any:
    try:
        import vnstock
    except ImportError as exc:
        raise VnstockUnavailableError(
            "the vnstock package is not installed; install the 'live' optional dependency group "
            "to use VnstockLiveAdapter, or use VnstockFixtureAdapter instead"
        ) from exc
    return vnstock


def _period_string(column: str) -> str:
    """vnstock quarter columns are '2026-Q2'; our report_period is '2026Q2'."""
    return column.replace("-", "")


def _retry(
    func: Any,
    *args: Any,
    max_retries: int = 3,
    retry_backoff_seconds: float = 5.0,
    **kwargs: Any,
) -> Any:
    """Call ``func`` with exponential backoff. Raises the last exception after ``max_retries``."""
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - vnstock raises assorted network/parse errors
            last_exc = exc
            if attempt < max_retries:
                time.sleep(retry_backoff_seconds * (2**attempt))
    assert last_exc is not None
    raise last_exc


class VnstockLiveAdapter:
    """Real vnstock adapter. Same three-method interface as VnstockFixtureAdapter.

    ``source_name`` is per-instance, not a class attribute, because the source varies per call:
    KBS for prices, VCI for statements (both explorers deliver whole đồng for statements; only
    KBS was measured for the ×1000 price scale, so prices always resolve through KBS here).
    """

    def __init__(
        self,
        *,
        max_retries: int = 3,
        retry_backoff_seconds: float = 5.0,
        min_request_delay_seconds: float = 1.0,
        metadata_sink: MetadataSink | None = None,
        run_id: str | None = None,
    ) -> None:
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.min_request_delay_seconds = min_request_delay_seconds
        self.metadata_sink = metadata_sink
        self.run_id = run_id

    def _throttle(self) -> None:
        if self.min_request_delay_seconds > 0:
            time.sleep(self.min_request_delay_seconds)

    def _record_request(
        self,
        *,
        endpoint: str,
        ticker: str | None,
        report_period: str | None,
        status: str,
        error: str | None = None,
        retry_count: int = 0,
    ) -> None:
        if self.metadata_sink is None:
            return
        self.metadata_sink.log_source_request(
            run_id=self.run_id,
            source_system="vnstock",
            source_endpoint=endpoint,
            ticker=ticker,
            report_period=report_period,
            request_status=status,
            retry_count=retry_count,
            error_message=error,
        )

    def _route_failure(self, dataset_name: str, reason: str, payload: dict[str, Any]) -> None:
        if self.metadata_sink is None:
            return
        self.metadata_sink.log_failed_record(
            dataset_name=dataset_name,
            failure_reason=reason,
            raw_payload=payload,
            run_id=self.run_id,
        )

    def _checkpoint(self, ticker: str) -> None:
        if self.metadata_sink is None:
            return
        self.metadata_sink.upsert_collector_checkpoint(
            collector_name="vnstock_live_adapter",
            source_system="vnstock",
            checkpoint_key="last_ticker",
            checkpoint_value=ticker,
        )

    # -- companies -----------------------------------------------------

    def fetch_companies(self) -> list[dict[str, Any]]:
        vnstock = _import_vnstock()
        self._throttle()
        try:
            frame = _retry(
                vnstock.Listing().symbols_by_exchange,
                max_retries=self.max_retries,
                retry_backoff_seconds=self.retry_backoff_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            self._record_request(
                endpoint="Listing.symbols_by_exchange",
                ticker=None,
                report_period=None,
                status="error",
                error=str(exc),
            )
            self._route_failure(
                "raw_companies", f"listing fetch failed: {exc}", {"endpoint": "symbols_by_exchange"}
            )
            return []
        self._record_request(
            endpoint="Listing.symbols_by_exchange",
            ticker=None,
            report_period=None,
            status="success",
        )

        now = datetime.now(UTC).isoformat()
        rows: list[dict[str, Any]] = []
        for record in frame.to_dict("records"):
            symbol = record.get("symbol")
            if not symbol:
                continue
            rows.append(
                {
                    "ticker": str(symbol).upper(),
                    "company_name": record.get("organ_name"),
                    "exchange": record.get("exchange"),
                    "source_system": "vnstock",
                    "source_name": "vnstock",
                    "source_unit": "N/A",
                    "created_ts": now,
                }
            )
        return rows

    # -- financial statements -------------------------------------------

    def fetch_financial_statements(
        self, ticker: str, start_year: int, end_year: int
    ) -> list[dict[str, Any]]:
        """Fetches whatever the free tier's 4-period cap allows.

        ``start_year``/``end_year`` are accepted for interface compatibility with
        ``VnstockFixtureAdapter`` but the free tier ignores requested ranges — it always
        returns the four most recent quarters (measured, ADR-020). Periods before that
        window are never fetched by this adapter; the caller falls through to the generator.
        """
        del start_year, end_year
        vnstock = _import_vnstock()
        ticker = ticker.upper()
        self._throttle()
        try:
            finance = vnstock.Finance(source="vci", symbol=ticker, period="quarter")
            balance_sheet = _retry(
                finance.balance_sheet,
                max_retries=self.max_retries,
                retry_backoff_seconds=self.retry_backoff_seconds,
            )
            income_statement = finance.income_statement()
            cash_flow = finance.cash_flow()
        except Exception as exc:  # noqa: BLE001
            self._record_request(
                endpoint="Finance.balance_sheet",
                ticker=ticker,
                report_period=None,
                status="error",
                error=str(exc),
            )
            self._route_failure(
                "raw_financial_statements",
                f"finance fetch failed for {ticker}: {exc}",
                {"ticker": ticker},
            )
            return []
        self._record_request(
            endpoint="Finance.balance_sheet", ticker=ticker, report_period=None, status="success"
        )

        period_columns = [
            c for c in balance_sheet.columns if c not in ("item", "item_en", "item_id")
        ]
        now = datetime.now(UTC).isoformat()
        rows: list[dict[str, Any]] = []
        for column in period_columns:
            report_period = _period_string(column)
            fields: dict[str, Any] = {}
            for frame, mapping in (
                (balance_sheet, _BALANCE_SHEET_FIELDS),
                (income_statement, _INCOME_STATEMENT_FIELDS),
                (cash_flow, _CASH_FLOW_FIELDS),
            ):
                if column not in frame.columns:
                    continue
                for item_id, field_name in mapping.items():
                    matches = frame.loc[frame["item_id"] == item_id, column]
                    if not matches.empty:
                        value = matches.iloc[0]
                        fields[field_name] = None if value != value else float(value)  # NaN check
            fields["ticker"] = ticker
            fields["report_period"] = report_period
            fields["source_system"] = "vnstock"
            fields["source_name"] = "vnstock_vci"
            fields["source_unit"] = "VND"  # whole đồng, ADR-020
            fields["known_from_ts"] = now
            fields["created_ts"] = now
            rows.append(fields)
            self._checkpoint(ticker)
        return rows

    # -- market prices ----------------------------------------------------

    def fetch_market_prices(
        self, ticker: str, start_year: int, end_year: int
    ) -> list[dict[str, Any]]:
        vnstock = _import_vnstock()
        ticker = ticker.upper()
        self._throttle()
        try:
            quote = vnstock.Quote(source="kbs", symbol=ticker)
            history = _retry(
                quote.history,
                start=f"{start_year}-01-01",
                end=f"{end_year}-12-31",
                interval="1D",
                max_retries=self.max_retries,
                retry_backoff_seconds=self.retry_backoff_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            self._record_request(
                endpoint="Quote.history",
                ticker=ticker,
                report_period=None,
                status="error",
                error=str(exc),
            )
            self._route_failure(
                "raw_market_prices_daily",
                f"quote fetch failed for {ticker}: {exc}",
                {"ticker": ticker},
            )
            return []
        self._record_request(
            endpoint="Quote.history", ticker=ticker, report_period=None, status="success"
        )

        now = datetime.now(UTC).isoformat()
        rows: list[dict[str, Any]] = []
        for record in history.to_dict("records"):
            trading_date = record["time"]
            trading_date_iso = (
                trading_date.isoformat()
                if hasattr(trading_date, "isoformat")
                else str(trading_date)
            )[:10]
            # F17: kbs/quote.py divides OHLC by 1000 for stock/ETF assets (nghìn đồng).
            # Multiply back so the lakehouse holds one money unit (đồng) everywhere.
            rows.append(
                {
                    "ticker": ticker,
                    "trading_date": trading_date_iso,
                    "open_price": _to_dong(record.get("open")),
                    "high_price": _to_dong(record.get("high")),
                    "low_price": _to_dong(record.get("low")),
                    "close_price": _to_dong(record.get("close")),
                    "volume": record.get("volume"),
                    "source_system": "vnstock",
                    "source_name": "vnstock_kbs",
                    "source_unit": "VND",  # normalized here, was nghìn đồng on the wire
                    "known_from_ts": now,
                    "created_ts": now,
                }
            )
        self._checkpoint(ticker)
        return rows


def _to_dong(value: Any) -> float | None:
    if value is None or value != value:  # NaN check without importing math/numpy
        return None
    return float(value) * 1000.0
