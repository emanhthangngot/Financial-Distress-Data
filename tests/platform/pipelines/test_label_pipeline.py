"""Pins src/ml/label_pipeline.py: exact 6-column-plus-source schema,
financial-sector exclusion, label_version stamping, idempotent rebuild."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ml.label_pipeline import (
    LABEL_SOURCE,
    LABEL_VERSION,
    build_labels,
    run_label_build,
    run_label_drift_build_task,
    write_labels_postgres,
)

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


class _FakeCursor:
    def __init__(self, store: list[dict]) -> None:
        self.store = store

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def execute(self, query: str, params: dict) -> None:
        self.store.append(params)


class _FakeConn:
    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.committed = False

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self.rows)

    def commit(self) -> None:
        self.committed = True


def test_write_labels_postgres_upserts_every_row_and_commits() -> None:
    rows = build_labels([_statement_row("G0001"), _statement_row("G0002", sector="Banks")])
    conn = _FakeConn()
    written = write_labels_postgres(rows, conn)
    assert written == 2
    assert len(conn.rows) == 2
    assert conn.committed is True


def test_write_labels_postgres_is_a_noop_on_empty_rows() -> None:
    conn = _FakeConn()
    assert write_labels_postgres([], conn) == 0
    assert conn.committed is False


def test_run_label_build_without_dsn_builds_but_does_not_write(monkeypatch) -> None:
    monkeypatch.delenv("PHASE2_REQUIRE_PG", raising=False)
    monkeypatch.delenv("PHASE2_PG_DSN", raising=False)
    repo_root = Path(__file__).resolve().parents[3]
    result = run_label_build(repo_root / "configs" / "generator-config.yaml", profile="ci")
    assert result["labels_built"] > 0
    assert result["labels_written"] == 0


def test_run_label_drift_build_task_reads_env_and_writes_no_dsn(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("PHASE2_PG_DSN", raising=False)
    monkeypatch.setenv("PHASE2_DRIFT_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.chdir(Path(__file__).resolve().parents[3])
    result = run_label_drift_build_task()
    assert result["labels_built"] > 0
    assert result["labels_written"] == 0
    assert result["drift_passed"] is True  # the shipped financial_deterioration config passes
    assert str(tmp_path) in result["drift_report_path"]  # never wrote into the real outputs/


def test_run_label_drift_build_task_raises_on_failed_drift_assertion(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("PHASE2_PG_DSN", raising=False)
    monkeypatch.setenv("PHASE2_DRIFT_OUTPUT_ROOT", str(tmp_path / "drift-output"))
    monkeypatch.chdir(Path(__file__).resolve().parents[3])
    # A threshold no real run could ever clear.
    bad_config = tmp_path / "drift.yaml"
    bad_config.write_text(
        """
schema_version: 1
scenarios:
  financial_deterioration:
    seed: 4001
    start_quarter: 2
    affected_fraction: 0.5
    feature_shifts:
      total_liabilities:
        mode: multiplicative
        magnitude: 0.60
    target_metric: debt_to_asset
    observed_stat: mean
    expected_direction: increase
    threshold: 999.0
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("PHASE2_DRIFT_CONFIG", str(bad_config))
    with pytest.raises((RuntimeError, Exception)):
        run_label_drift_build_task()
