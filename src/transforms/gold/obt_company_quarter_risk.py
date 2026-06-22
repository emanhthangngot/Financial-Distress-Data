"""
One-big-table (OBT) builder for company-quarter risk features.

Joins the Gold dimensions, facts, and the rule-based distress label into a single wide table for
analyst exploration. The OBT is registered as a DuckDB view for DBeaver evidence.
"""

from __future__ import annotations

from typing import Any


def build_obt_company_quarter_risk(
    financial_facts: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    market_facts: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    label_by_key = {(row["ticker"], row["report_period"]): row for row in labels}
    output = []
    for row in financial_facts:
        label = label_by_key.get((row["ticker"], row["report_period"]), {})
        total_assets = (
            float(row["total_assets"]) if row.get("total_assets") not in (None, 0) else None
        )
        total_liabilities = (
            float(row["total_liabilities"]) if row.get("total_liabilities") is not None else None
        )
        equity = float(row["equity"]) if row.get("equity") not in (None, 0) else None
        current_liabilities = (
            float(row["current_liabilities"])
            if row.get("current_liabilities") not in (None, 0)
            else None
        )
        interest_expense = (
            float(row["interest_expense"]) if row.get("interest_expense") not in (None, 0) else None
        )
        obt = {
            **row,
            "current_ratio": (
                None
                if current_liabilities is None
                else float(row.get("current_assets") or 0) / current_liabilities
            ),
            "debt_to_asset": (
                None
                if total_assets is None or total_liabilities is None
                else total_liabilities / total_assets
            ),
            "debt_to_equity": (
                None if equity is None or total_liabilities is None else total_liabilities / equity
            ),
            "roa": (
                None if total_assets is None else float(row.get("net_income") or 0) / total_assets
            ),
            "roe": None if equity is None else float(row.get("net_income") or 0) / equity,
            "ebit_interest_coverage": (
                None if interest_expense is None else float(row.get("ebit") or 0) / interest_expense
            ),
            "distress_label": label.get("distress_label"),
            "distress_reason": label.get("distress_reason"),
            "z_score": label.get("z_score"),
            "label_source": label.get("label_source"),
            "label_confidence": label.get("label_confidence"),
            "training_eligible": label.get("training_eligible"),
        }
        output.append(obt)
    return output
