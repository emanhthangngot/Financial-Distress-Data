from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

RULE_VERSION = "v1"


@dataclass(frozen=True)
class DistressLabel:
    ticker: str
    report_period: str
    event_timestamp: str | None
    created_ts: str | None
    distress_label: int | None
    distress_reason: str
    z_score: float | None
    rule_version: str = RULE_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "report_period": self.report_period,
            "event_timestamp": self.event_timestamp,
            "created_ts": self.created_ts,
            "distress_label": self.distress_label,
            "distress_reason": self.distress_reason,
            "z_score": self.z_score,
            "rule_version": self.rule_version,
        }


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _safe_divide(numerator: Any, denominator: Any) -> Decimal | None:
    n_value = _decimal(numerator)
    d_value = _decimal(denominator)
    if n_value is None or d_value is None or d_value == 0:
        return None
    return n_value / d_value


def _round_float(value: Decimal | None, places: str = "0.0001") -> float | None:
    if value is None:
        return None
    return float(value.quantize(Decimal(places), rounding=ROUND_HALF_UP))


def z_double_prime(row: dict[str, Any]) -> float | None:
    total_assets = row.get("total_assets")
    total_liabilities = row.get("total_liabilities")
    working_capital = None
    if row.get("current_assets") is not None and row.get("current_liabilities") is not None:
        current_assets = _decimal(row.get("current_assets"))
        current_liabilities = _decimal(row.get("current_liabilities"))
        working_capital = current_assets - current_liabilities

    ratios = [
        _safe_divide(working_capital, total_assets),
        _safe_divide(row.get("retained_earnings"), total_assets),
        _safe_divide(row.get("ebit"), total_assets),
        _safe_divide(row.get("equity"), total_liabilities),
    ]
    if any(ratio is None for ratio in ratios):
        return None
    components = [
        Decimal("6.56") * ratios[0],
        Decimal("3.26") * ratios[1],
        Decimal("6.72") * ratios[2],
        Decimal("1.05") * ratios[3],
    ]
    return _round_float(sum(components))


def warning_rules(
    row: dict[str, Any], previous_row: dict[str, Any] | None = None
) -> dict[str, bool]:
    debt_to_asset = _safe_divide(row.get("total_liabilities"), row.get("total_assets"))
    current_ratio = _safe_divide(row.get("current_assets"), row.get("current_liabilities"))
    coverage = _safe_divide(row.get("ebit"), row.get("interest_expense"))
    net_income = _decimal(row.get("net_income"))
    previous_net_income = _decimal(previous_row.get("net_income")) if previous_row else None
    equity = _decimal(row.get("equity"))

    return {
        "high_debt_to_asset": bool(debt_to_asset is not None and debt_to_asset > Decimal("0.8")),
        "low_current_ratio": bool(current_ratio is not None and current_ratio < Decimal("1.0")),
        "two_quarter_net_loss": bool(
            net_income is not None
            and previous_net_income is not None
            and net_income < 0
            and previous_net_income < 0
        ),
        "negative_equity": bool(equity is not None and equity < 0),
        "weak_interest_coverage": bool(coverage is not None and coverage < Decimal("1.0")),
    }


def compute_distress_label(
    row: dict[str, Any], previous_row: dict[str, Any] | None = None
) -> DistressLabel:
    z_score = z_double_prime(row)
    warnings = warning_rules(row, previous_row)
    triggered = sorted(name for name, is_true in warnings.items() if is_true)
    warning_count = len(triggered)
    reasons = triggered.copy()

    if z_score is None:
        if warning_count >= 2:
            label = 1
            reasons.append("z_score_null")
        else:
            label = None
            reasons.append("insufficient_data")
    elif z_score < 1.1 or warning_count >= 2:
        label = 1
        if z_score < 1.1:
            reasons.append("z_score_distress_zone")
    elif z_score > 2.6 and warning_count < 2:
        label = 0
        reasons.append("z_score_safe_zone")
    else:
        label = 0
        reasons.append("gray_zone_monitor")

    return DistressLabel(
        ticker=str(row.get("ticker")),
        report_period=str(row.get("report_period")),
        event_timestamp=row.get("event_timestamp") or row.get("report_release_date"),
        created_ts=row.get("created_ts"),
        distress_label=label,
        distress_reason=";".join(dict.fromkeys(reasons)),
        z_score=z_score,
    )


def compute_labels(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows_sorted = sorted(rows, key=lambda item: (item.get("ticker"), item.get("report_period")))
    previous_by_ticker: dict[str, dict[str, Any]] = {}
    labels: list[dict[str, Any]] = []
    for row in rows_sorted:
        ticker = str(row.get("ticker"))
        label = compute_distress_label(row, previous_by_ticker.get(ticker))
        labels.append(label.as_dict())
        previous_by_ticker[ticker] = row
    return labels
