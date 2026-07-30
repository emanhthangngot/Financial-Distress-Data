"""
Lightweight schema registry for the lakehouse.

Persists canonical schemas for each Bronze, Silver, and Gold table to
``project_metadata.schema_registry``. The PySpark transforms consult this registry to widen columns
safely during schema evolution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml


class SchemaValidationError(ValueError):
    """Raised when a row cannot satisfy a typed schema contract."""


@dataclass(frozen=True)
class SchemaContract:
    dataset_name: str
    schema_version: str
    required: list[str]
    nullable: list[str]
    field_types: dict[str, str] | None = None
    enum_values: dict[str, list[Any]] | None = None
    blank_as_null: bool = True

    def validate_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """Normalize and type one row or raise a field-specific validation error."""
        normalized = {str(key).strip().lower(): value for key, value in row.items()}
        output: dict[str, Any] = {}
        for field in [*self.required, *self.nullable]:
            value = normalized.get(field)
            if self.blank_as_null and isinstance(value, str) and not value.strip():
                value = None
            if field in self.required and value is None:
                raise SchemaValidationError(f"missing required field: {field}")
            if value is not None:
                value = _coerce_value(field, value, (self.field_types or {}).get(field, "string"))
                allowed = (self.enum_values or {}).get(field)
                if allowed is not None and value not in allowed:
                    raise SchemaValidationError(
                        f"invalid enum value for {field}: {value!r}; expected one of {allowed}"
                    )
            output[field] = value
        return output


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError from exc
    parsed = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _coerce_value(field: str, value: Any, field_type: str) -> Any:
    try:
        if field_type == "string":
            return str(value).strip()
        if field_type == "integer":
            return int(value)
        if field_type == "float":
            return float(value)
        if field_type == "boolean":
            if isinstance(value, bool):
                return value
            normalized = str(value).strip().lower()
            if normalized in {"true", "1", "yes"}:
                return True
            if normalized in {"false", "0", "no"}:
                return False
            raise ValueError
        if field_type == "date":
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            return date.fromisoformat(str(value).strip())
        if field_type == "timestamp":
            return _parse_timestamp(value)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"invalid {field_type} value for {field}: {value!r}") from exc
    raise SchemaValidationError(f"unsupported field type for {field}: {field_type}")


DEFAULT_CONTRACTS = {
    "companies": SchemaContract(
        "companies",
        "v1",
        ["ticker", "company_name", "exchange", "created_ts"],
        ["industry", "sector", "listing_date", "delisted_flag", "company_size"],
    ),
    "financial_statements": SchemaContract(
        "financial_statements",
        "v1",
        [
            "ticker",
            "report_period",
            "fiscal_year",
            "fiscal_quarter",
            "total_assets",
            "total_liabilities",
            "equity",
            "created_ts",
        ],
        [
            "current_assets",
            "current_liabilities",
            "revenue",
            "ebit",
            "interest_expense",
            "net_income",
            "operating_cash_flow",
            "retained_earnings",
            "statement_type",
            "report_release_date",
            "event_timestamp",
        ],
    ),
    "market_prices_daily": SchemaContract(
        "market_prices_daily",
        "v1",
        ["ticker", "trading_date", "close_price", "volume", "created_ts"],
        [
            "open_price",
            "high_price",
            "low_price",
            "market_cap",
            "shares_outstanding",
            "event_timestamp",
        ],
    ),
}


class InMemorySchemaRegistry:
    def __init__(self, contracts: dict[str, SchemaContract] | None = None) -> None:
        self.contracts = contracts or DEFAULT_CONTRACTS

    def get_current(self, dataset_name: str) -> SchemaContract:
        try:
            return self.contracts[dataset_name]
        except KeyError as exc:
            raise KeyError(f"unknown dataset contract: {dataset_name}") from exc

    @classmethod
    def from_yaml(cls, path: str | Path) -> InMemorySchemaRegistry:
        """Build a registry from the checked-in typed schema configuration."""
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError("schema contract config must use schema_version 1")
        contracts = {}
        for name, raw in payload.get("datasets", {}).items():
            contracts[name] = SchemaContract(
                dataset_name=name,
                schema_version=str(raw["version"]),
                required=list(raw["required"]),
                nullable=list(raw.get("nullable", [])),
                field_types=dict(raw.get("field_types", {})),
                enum_values={key: list(values) for key, values in raw.get("enums", {}).items()},
                blank_as_null=bool(raw.get("blank_as_null", True)),
            )
        return cls(contracts)

    def export_json(self, output_path: str | Path) -> None:
        payload: dict[str, Any] = {
            name: {
                "schema_version": contract.schema_version,
                "required": contract.required,
                "nullable": contract.nullable,
                "field_types": contract.field_types or {},
                "enums": contract.enum_values or {},
                "blank_as_null": contract.blank_as_null,
            }
            for name, contract in self.contracts.items()
        }
        Path(output_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
