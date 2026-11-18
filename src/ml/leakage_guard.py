"""Point-in-time leakage checks for feature/label training joins."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime
from typing import Any


class LeakageError(ValueError):
    """Raised when a feature is observed after the label decision boundary."""

    def __init__(self, message: str, offending_rows: list[dict[str, Any]]):
        super().__init__(message)
        self.offending_rows = offending_rows


def _rows(value: Any) -> list[dict[str, Any]]:
    if hasattr(value, "to_dict"):
        try:
            return [dict(row) for row in value.to_dict(orient="records")]
        except TypeError:
            pass
    if isinstance(value, Mapping):
        return [dict(value)]
    return [dict(row) for row in value]


def _time(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, datetime.min.time(), tzinfo=UTC)
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            try:
                return float(text)
            except ValueError as exc:
                raise ValueError(f"unsupported timestamp value {value!r}") from exc
    parsed = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def find_leakage(
    rows: Any,
    *,
    feature_timestamp_col: str | None = None,
    label_timestamp_col: str | None = None,
) -> list[dict[str, Any]]:
    """Return rows where feature availability is later than label decision.

    Common aliases (``event_timestamp``, ``feature_ts``, ``decision_timestamp``
    and ``label_ts``) are accepted so the guard can operate on both Feast and
    the project's label-table shape.
    """

    records = _rows(rows)
    if not records:
        return []
    feature_names = [
        feature_timestamp_col,
        "known_from_ts",
        "feature_timestamp",
        "feature_ts",
        "event_timestamp",
        "created_ts",
    ]
    label_names = [
        label_timestamp_col,
        "decision_ts",
        "label_timestamp",
        "label_ts",
        "decision_timestamp",
        "as_of_timestamp",
    ]
    feature_name = next((name for name in feature_names if name and name in records[0]), None)
    label_name = next((name for name in label_names if name and name in records[0]), None)
    if feature_name is None or label_name is None:
        raise ValueError(
            "rows must include a feature timestamp and label decision timestamp; "
            f"found keys={sorted(records[0])}"
        )

    offending: list[dict[str, Any]] = []
    for index, row in enumerate(records):
        feature_time = _time(row.get(feature_name))
        label_time = _time(row.get(label_name))
        if feature_time is None or label_time is None:
            raise ValueError(
                "feature and label timestamps must be present on every row; "
                f"index={index}, feature_column={feature_name!r}, label_column={label_name!r}"
            )
        if feature_time > label_time:
            offending.append({"index": index, "row": row})
    return offending


def assert_no_leakage(
    rows: Any,
    *,
    feature_timestamp_col: str | None = None,
    label_timestamp_col: str | None = None,
) -> None:
    """Raise :class:`LeakageError` with offending row indexes and values."""

    offending = find_leakage(
        rows,
        feature_timestamp_col=feature_timestamp_col,
        label_timestamp_col=label_timestamp_col,
    )
    if offending:
        indexes = ", ".join(str(item["index"]) for item in offending)
        raise LeakageError(f"point-in-time leakage detected in rows: {indexes}", offending)


def validate_point_in_time(rows: Any, **kwargs: Any) -> bool:
    """Boolean convenience wrapper used by pipeline validation steps."""

    assert_no_leakage(rows, **kwargs)
    return True


class PointInTimeLeakageGuard:
    """Object-oriented adapter matching :mod:`src.ml.contracts` naming."""

    def assert_no_leakage(self, df: Any, split: Any = None) -> None:
        # ``split`` is accepted for contract compatibility; timestamps in the
        # joined frame remain the source of truth for the PIT check.
        del split
        assert_no_leakage(df)

    def find(self, df: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return find_leakage(df, **kwargs)
