"""Pins src/ml/label_pipeline.py: exact 6-column-plus-source schema,
financial-sector exclusion, label_version stamping, idempotent rebuild."""

from __future__ import annotations

from src.ml.label_pipeline import LABEL_SOURCE, LABEL_VERSION, build_labels

_EXPECTED_COLUMNS = {
    "ticker",
    "event_timestamp",
    "label",
    "label_version",
    "created_ts",
    "training_eligible",
    "label_source",
}


def _statement_row(ticker: str, sector: str = "Technology") -> dict:
    return {
        "ticker": ticker,
        "report_period": "2026Q2",
        "sector": sector,
        "total_assets": 1_000_000,
        "total_liabilities": 400_000,
        "current_assets": 300_000,
        "current_liabilities": 200_000,
        "retained_earnings": 100_000,
        "ebit": 50_000,
        "equity": 600_000,
        "interest_expense": 5_000,
        "net_income": 20_000,
        "event_timestamp": "2026-05-15T00:00:00+00:00",
        "created_ts": "2026-05-15T00:00:00+00:00",
    }


def test_build_labels_returns_exact_schema() -> None:
    rows = build_labels([_statement_row("G0001")])
    assert len(rows) == 1
    assert set(rows[0]) == _EXPECTED_COLUMNS
    assert rows[0]["label_version"] == LABEL_VERSION
    assert rows[0]["label_source"] == LABEL_SOURCE


def test_financial_sector_rows_are_not_training_eligible() -> None:
    rows = build_labels([_statement_row("G0002", sector="Banks")])
    assert rows[0]["training_eligible"] is False


def test_build_labels_is_idempotent() -> None:
    input_rows = [_statement_row("G0001"), _statement_row("G0002", sector="Banks")]
    first = build_labels(input_rows)
    second = build_labels(input_rows)
    assert first == second
