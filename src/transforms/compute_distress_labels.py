"""
Rule-based financial-distress labeler.

Computes the per-company-per-quarter distress label used by the Gold zone and downstream ML.
Encapsulates ``RULE_VERSION`` and the threshold table so rule changes are auditable in git history.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from src.transforms.sector_policy import load_sector_policy

RULE_VERSION = "v1"
LABEL_SOURCE = "rule_based_v1"
ZERO_LIABILITIES_X4_CAP = Decimal("99.0")


@dataclass(frozen=True)
class DistressLabel:
    ticker: str
    report_period: str
    event_timestamp: str | None
    created_ts: str | None
    distress_label: int | None
    distress_reason: str
    z_score: float | None
    label_source: str = LABEL_SOURCE
    label_confidence: str | None = None
    training_eligible: bool = False
    rule_version: str = RULE_VERSION
    company_version_key: str | None = None
    known_from_ts: Any = None
    decision_ts: Any = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "report_period": self.report_period,
            "event_timestamp": self.event_timestamp,
            "created_ts": self.created_ts,
            "distress_label": self.distress_label,
            "distress_reason": self.distress_reason,
            "z_score": self.z_score,
            "label_source": self.label_source,
            "label_confidence": self.label_confidence,
            "training_eligible": self.training_eligible,
            "rule_version": self.rule_version,
            "company_version_key": self.company_version_key,
            "known_from_ts": self.known_from_ts,
            "decision_ts": self.decision_ts,
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


def _normalized_text(value: Any) -> str:
    return str(value or "").strip().lower()


def is_financial_sector(row: dict[str, Any]) -> bool:
    policy = load_sector_policy()
    text_values = {
        _normalized_text(row.get("sector")),
        _normalized_text(row.get("industry")),
        _normalized_text(row.get("gics_sector")),
        _normalized_text(row.get("gics_industry_group")),
    }
    code_values = {
        str(row.get("gics_sector_code") or "").strip(),
        str(row.get("gics_code") or "").strip()[:2],
    }
    return bool(text_values & policy.terms or code_values & policy.codes)


def _quarter_index(report_period: Any) -> int | None:
    if report_period is None:
        return None
    value = str(report_period).strip().upper()
    if len(value) != 6 or value[4] != "Q":
        return None
    try:
        year = int(value[:4])
        quarter = int(value[5])
    except ValueError:
        return None
    if quarter not in {1, 2, 3, 4}:
        return None
    return year * 4 + quarter


def _is_immediately_previous_quarter(
    current_row: dict[str, Any], previous_row: dict[str, Any] | None
) -> bool:
    if previous_row is None:
        return False
    current_index = _quarter_index(current_row.get("report_period"))
    previous_index = _quarter_index(previous_row.get("report_period"))
    return (
        current_index is not None
        and previous_index is not None
        and current_index - previous_index == 1
    )


def z_double_prime(row: dict[str, Any]) -> float | None:
    total_assets = row.get("total_assets")
    total_liabilities = row.get("total_liabilities")
    total_liabilities_decimal = _decimal(total_liabilities)
    working_capital = None
    if row.get("current_assets") is not None and row.get("current_liabilities") is not None:
        current_assets = _decimal(row.get("current_assets"))
        current_liabilities = _decimal(row.get("current_liabilities"))
        working_capital = current_assets - current_liabilities

    equity_to_liabilities = (
        ZERO_LIABILITIES_X4_CAP
        if total_liabilities_decimal == 0
        else _safe_divide(row.get("equity"), total_liabilities)
    )
    ratios = [
        _safe_divide(working_capital, total_assets),
        _safe_divide(row.get("retained_earnings"), total_assets),
        _safe_divide(row.get("ebit"), total_assets),
        equity_to_liabilities,
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
    consecutive_period = _is_immediately_previous_quarter(row, previous_row)

    return {
        "high_debt_to_asset": bool(debt_to_asset is not None and debt_to_asset > Decimal("0.8")),
        "low_current_ratio": bool(current_ratio is not None and current_ratio < Decimal("1.0")),
        "two_quarter_net_loss": bool(
            net_income is not None
            and previous_net_income is not None
            and consecutive_period
            and net_income < 0
            and previous_net_income < 0
        ),
        "negative_equity": bool(equity is not None and equity < 0),
        "weak_interest_coverage": bool(coverage is not None and coverage < Decimal("1.0")),
    }


def compute_distress_label(
    row: dict[str, Any], previous_row: dict[str, Any] | None = None
) -> DistressLabel:
    """Compute the distress label for a single company-quarter row.

    Data-flow contract (staging -> fact -> label):

    - ``row`` is a flattened fact row produced by the **staging** step
      (DAG 06 Silver -> Gold). The staging step joins the typed
      ``dim_company`` and ``fact_financials`` intermediates and projects
      the source-of-truth columns listed below into a single record.
    - The function reads **only** these source-of-truth columns from
      ``row`` (plus the optional ``previous_row`` for trend rules):

      - ``ticker`` — company identifier (string)
      - ``report_period`` — fiscal quarter key (string, e.g. ``"2024Q1"``)
      - ``total_assets`` — period-end total assets (numeric)
      - ``total_liabilities`` — period-end total liabilities (numeric)
      - ``current_assets``, ``current_liabilities`` — for working-capital
        ratio and current ratio
      - ``retained_earnings``, ``ebit`` — for Altman z_double_prime
      - ``market_value_equity``, ``total_revenue`` — for Altman z_double_prime
      - ``sector`` — used by ``is_financial_sector`` to gate the exclusion
        policy
      - ``event_timestamp`` / ``report_release_date`` / ``created_ts`` —
        propagated into the output label metadata
    - The function does **not** read raw Silver columns; any change to
      the upstream ``dim_company`` or ``fact_financials`` schema must be
      reflected in the staging projection before this function is correct.

    ``previous_row`` (optional) is a prior-quarter fact row with the same
    column contract; it is consumed by trend-based warning rules
    (``warning_rules``) only.
    """
    if is_financial_sector(row):
        return DistressLabel(
            ticker=str(row.get("ticker")),
            report_period=str(row.get("report_period")),
            event_timestamp=row.get("event_timestamp") or row.get("report_release_date"),
            created_ts=row.get("created_ts"),
            distress_label=None,
            distress_reason="financial_sector_excluded",
            z_score=None,
            label_confidence=None,
            training_eligible=False,
            company_version_key=row.get("company_version_key"),
            known_from_ts=row.get("known_from_ts"),
            decision_ts=row.get("known_from_ts"),
        )

    z_score = z_double_prime(row)
    warnings = warning_rules(row, previous_row)
    triggered = sorted(name for name, is_true in warnings.items() if is_true)
    warning_count = len(triggered)
    reasons = triggered.copy()
    label_confidence: str | None
    training_eligible: bool

    if z_score is None:
        if warning_count >= 2:
            label = 1
            label_confidence = "medium"
            training_eligible = True
            reasons.append("z_score_null")
        else:
            label = None
            label_confidence = None
            training_eligible = False
            reasons.append("insufficient_data")
    elif z_score < 1.1 or warning_count >= 2:
        label = 1
        label_confidence = "high" if z_score < 1.1 else "medium"
        training_eligible = True
        if z_score < 1.1:
            reasons.append("z_score_distress_zone")
    elif z_score > 2.6 and warning_count < 2:
        label = 0
        label_confidence = "high"
        training_eligible = True
        reasons.append("z_score_safe_zone")
    else:
        label = 0
        label_confidence = "low"
        training_eligible = False
        reasons.append("gray_zone_monitor")
    if _decimal(row.get("total_liabilities")) == 0 and z_score is not None:
        reasons.append("zero_liabilities_x4_capped")

    return DistressLabel(
        ticker=str(row.get("ticker")),
        report_period=str(row.get("report_period")),
        event_timestamp=row.get("event_timestamp") or row.get("report_release_date"),
        created_ts=row.get("created_ts"),
        distress_label=label,
        distress_reason=";".join(dict.fromkeys(reasons)),
        z_score=z_score,
        label_confidence=label_confidence,
        training_eligible=training_eligible,
        company_version_key=row.get("company_version_key"),
        known_from_ts=row.get("known_from_ts"),
        decision_ts=row.get("known_from_ts"),
    )


def compute_labels(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest_rows = [row for row in rows if row.get("is_latest_vintage") is not False]
    rows_sorted = sorted(
        latest_rows, key=lambda item: (item.get("ticker"), item.get("report_period"))
    )
    # Holds the last *observed* row per ticker (whatever sort produced). Whether
    # that row is strictly the prior quarter is decided downstream by the gating
    # check  inside compute_distress_label.
    last_observed_row_by_ticker: dict[str, dict[str, Any]] = {}
    labels: list[dict[str, Any]] = []
    for row in rows_sorted:
        ticker = str(row.get("ticker"))
        label = compute_distress_label(row, last_observed_row_by_ticker.get(ticker))
        labels.append(label.as_dict())
        last_observed_row_by_ticker[ticker] = row
    return labels
