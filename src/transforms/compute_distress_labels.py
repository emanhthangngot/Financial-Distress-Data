from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml

RULE_VERSION = "v1"
LABEL_SOURCE = "rule_based_v1"
ZERO_LIABILITIES_X4_CAP = Decimal("99.0")
FINANCIAL_SECTOR_TERMS = {
    "bank",
    "banks",
    "banking",
    "insurance",
    "insurers",
    "securities",
    "brokerage",
    "diversified financials",
    "financial services",
}
FINANCIAL_GICS_CODES = {"40", "4010", "4020", "4030"}


@dataclass(frozen=True)
class SectorExclusion:
    """Configured sectors excluded from rule-based distress labeling."""

    terms: frozenset[str]
    gics_codes: frozenset[str]


DEFAULT_SECTOR_EXCLUSION = SectorExclusion(
    frozenset(FINANCIAL_SECTOR_TERMS), frozenset(FINANCIAL_GICS_CODES)
)


def load_sector_exclusion(path: str | Path) -> SectorExclusion:
    """Load sector and GICS exclusions from YAML."""
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return SectorExclusion(
        frozenset(_normalized_text(value) for value in payload["z_score_excluded_sectors"]),
        frozenset(str(value).strip() for value in payload["z_score_excluded_gics"]),
    )


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


def is_financial_sector(
    row: dict[str, Any], sector_exclusion: SectorExclusion | None = None
) -> bool:
    policy = sector_exclusion or DEFAULT_SECTOR_EXCLUSION
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
    return bool(text_values & policy.terms or code_values & policy.gics_codes)


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
    row: dict[str, Any],
    previous_row: dict[str, Any] | None = None,
    sector_exclusion: SectorExclusion | None = None,
) -> DistressLabel:
    if is_financial_sector(row, sector_exclusion):
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
    )


def _enrich_with_company_sector(
    rows: list[dict[str, Any]], company_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    companies_by_ticker: dict[str, list[dict[str, Any]]] = {}
    for company in company_rows:
        companies_by_ticker.setdefault(str(company.get("ticker", "")).upper(), []).append(company)
    for companies in companies_by_ticker.values():
        companies.sort(key=lambda item: str(item.get("created_ts", "")), reverse=True)

    enriched = []
    for row in rows:
        ticker = str(row.get("ticker", "")).upper()
        reference = str(
            row.get("event_timestamp")
            or row.get("report_release_date")
            or row.get("created_ts")
            or ""
        )
        company = next(
            (
                item
                for item in companies_by_ticker.get(ticker, [])
                if str(item.get("created_ts", "")) <= reference
            ),
            {},
        )
        enriched.append(
            {
                **row,
                **{
                    field: company.get(field)
                    for field in (
                        "sector",
                        "industry",
                        "gics_sector",
                        "gics_industry_group",
                        "gics_sector_code",
                        "gics_code",
                    )
                    if row.get(field) is None and company.get(field) is not None
                },
            }
        )
    return enriched


def compute_labels(
    rows: list[dict[str, Any]],
    company_rows: list[dict[str, Any]] | None = None,
    sector_exclusion: SectorExclusion | None = None,
) -> list[dict[str, Any]]:
    source_rows = _enrich_with_company_sector(rows, company_rows) if company_rows else rows
    rows_sorted = sorted(
        source_rows, key=lambda item: (item.get("ticker"), item.get("report_period"))
    )
    previous_by_ticker: dict[str, dict[str, Any]] = {}
    labels: list[dict[str, Any]] = []
    for row in rows_sorted:
        ticker = str(row.get("ticker"))
        label = compute_distress_label(
            row, previous_by_ticker.get(ticker), sector_exclusion=sector_exclusion
        )
        labels.append(label.as_dict())
        previous_by_ticker[ticker] = row
    return labels
