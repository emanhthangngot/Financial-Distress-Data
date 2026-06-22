"""Regression tests for None propagation in OBT ratio helpers.

Background: the OBT builder used ``float(row.get("current_assets") or 0)`` to
materialize a numerator; when ``current_assets`` is ``None`` the ``or 0`` falls
through to ``0`` and the resulting ratio becomes ``0.0`` instead of ``None``.
The same anti-pattern affected the other ratio helpers (ROA, ROE, EBIT
coverage). These tests pin the desired behavior: any ratio whose numerator OR
denominator is missing must return ``None`` (rendered as SQL ``NULL``), never
``0`` or ``0.0``.
"""

from __future__ import annotations

import pytest

from src.transforms.gold.obt_company_quarter_risk import (
    build_obt_company_quarter_risk,
)


def _base_row(**overrides):
    row = {
        "ticker": "AAA",
        "report_period": "2024Q1",
        "current_assets": 800.0,
        "current_liabilities": 200.0,
        "total_assets": 1000.0,
        "total_liabilities": 400.0,
        "equity": 500.0,
        "ebit": 50.0,
        "interest_expense": 10.0,
        "net_income": 25.0,
    }
    row.update(overrides)
    return row


def test_current_ratio_returns_none_when_current_assets_missing():
    row = _base_row(current_assets=None)
    [obt] = build_obt_company_quarter_risk([row], labels=[])
    assert obt["current_ratio"] is None


def test_current_ratio_returns_none_when_current_liabilities_missing():
    row = _base_row(current_liabilities=None)
    [obt] = build_obt_company_quarter_risk([row], labels=[])
    assert obt["current_ratio"] is None


def test_current_ratio_returns_none_when_denominator_zero():
    row = _base_row(current_liabilities=0)
    [obt] = build_obt_company_quarter_risk([row], labels=[])
    assert obt["current_ratio"] is None


def test_current_ratio_computes_normally_when_inputs_numeric():
    row = _base_row(current_assets=800.0, current_liabilities=200.0)
    [obt] = build_obt_company_quarter_risk([row], labels=[])
    assert obt["current_ratio"] == pytest.approx(4.0)


def test_roa_returns_none_when_net_income_missing():
    row = _base_row(net_income=None)
    [obt] = build_obt_company_quarter_risk([row], labels=[])
    assert obt["roa"] is None


def test_roa_returns_none_when_total_assets_missing():
    row = _base_row(total_assets=None)
    [obt] = build_obt_company_quarter_risk([row], labels=[])
    assert obt["roa"] is None


def test_roa_computes_normally_when_inputs_numeric():
    row = _base_row(net_income=50.0, total_assets=1000.0)
    [obt] = build_obt_company_quarter_risk([row], labels=[])
    assert obt["roa"] == pytest.approx(0.05)


def test_roe_returns_none_when_equity_missing():
    row = _base_row(equity=None)
    [obt] = build_obt_company_quarter_risk([row], labels=[])
    assert obt["roe"] is None


def test_roe_returns_none_when_net_income_missing():
    row = _base_row(net_income=None)
    [obt] = build_obt_company_quarter_risk([row], labels=[])
    assert obt["roe"] is None


def test_roe_computes_normally_when_inputs_numeric():
    row = _base_row(net_income=50.0, equity=500.0)
    [obt] = build_obt_company_quarter_risk([row], labels=[])
    assert obt["roe"] == pytest.approx(0.1)


def test_ebit_coverage_returns_none_when_interest_expense_missing():
    row = _base_row(interest_expense=None)
    [obt] = build_obt_company_quarter_risk([row], labels=[])
    assert obt["ebit_interest_coverage"] is None


def test_ebit_coverage_returns_none_when_ebit_missing():
    row = _base_row(ebit=None)
    [obt] = build_obt_company_quarter_risk([row], labels=[])
    assert obt["ebit_interest_coverage"] is None


def test_ebit_coverage_computes_normally_when_inputs_numeric():
    row = _base_row(ebit=50.0, interest_expense=10.0)
    [obt] = build_obt_company_quarter_risk([row], labels=[])
    assert obt["ebit_interest_coverage"] == pytest.approx(5.0)


def test_debt_to_equity_returns_none_when_equity_missing():
    row = _base_row(equity=None)
    [obt] = build_obt_company_quarter_risk([row], labels=[])
    assert obt["debt_to_equity"] is None


def test_debt_to_asset_returns_none_when_total_assets_missing():
    row = _base_row(total_assets=None)
    [obt] = build_obt_company_quarter_risk([row], labels=[])
    assert obt["debt_to_asset"] is None
