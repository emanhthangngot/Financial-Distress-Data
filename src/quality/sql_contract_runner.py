"""W24 Idea 1 - SQL contract runner.

Loads ``sql/duckdb_create_views.sql``, extracts every ``CREATE VIEW``
name, classifies it by Gold layer prefix, and writes the result to
``docs/evidence/dbt_macro_check.json``.

The naming convention enforced here mirrors the DuckDB macro in
``sql_contract_macros.sql``: views must start with ``gold_<layer>_``
where ``<layer>`` is one of ``dim``, ``fact``, ``obt``, ``feat``.
The Python mirror lets the contract be checked offline (CI, pre-commit,
test) without needing a live DuckDB session; the SQL file is the source
of truth for the same rule when running inside DuckDB.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

# Allowed Gold layer prefixes. Kept in sync with the macro in
# ``sql_contract_macros.sql`` and with ``docs/02_schema_design.md``.
ALLOWED_LAYERS: tuple[str, ...] = ("dim", "fact", "obt", "feat")

# Regex captures the view name from a ``CREATE [OR REPLACE] VIEW <name>``
# statement. It is intentionally lenient about whitespace and the
# ``OR REPLACE`` keyword.
_VIEW_NAME_RE = re.compile(
    r"CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)


def classify_view(name: str) -> str:
    """Return the Gold layer for a fully-qualified view name.

    Examples
    --------
    >>> classify_view("gold_dim_company")
    'dim'
    >>> classify_view("gold_feat_company_unified")
    'feat'

    Raises
    ------
    ValueError
        If ``name`` does not start with ``gold_<allowed_layer>_``.
    """
    if not name.startswith("gold_"):
        raise ValueError(
            f"view {name!r} does not start with 'gold_'"
        )
    tail = name[len("gold_"):]
    for layer in ALLOWED_LAYERS:
        prefix = f"{layer}_"
        if tail.startswith(prefix):
            return layer
    raise ValueError(
        f"view {name!r} has no recognised Gold layer prefix "
        f"(expected one of: {', '.join(ALLOWED_LAYERS)})"
    )


def _parse_view_names(sql_path: Path) -> list[str]:
    """Read the SQL file and return the list of view names in order."""
    text = sql_path.read_text(encoding="utf-8")
    return _VIEW_NAME_RE.findall(text)


def check_duckdb_views(
    sql_path: Path, evidence_path: Path
) -> dict[str, object]:
    """Validate every view in ``sql_path`` and write the evidence JSON.

    Parameters
    ----------
    sql_path
        Path to the DuckDB view registration SQL (typically
        ``sql/duckdb_create_views.sql``).
    evidence_path
        Path the JSON evidence will be written to.

    Returns
    -------
    dict
        The same payload that is written to ``evidence_path``:
        ``{total_views, by_layer, violations}``.
    """
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    view_names = _parse_view_names(sql_path)
    by_layer: Counter[str] = Counter()
    violations: list[dict[str, str]] = []
    for name in view_names:
        try:
            layer = classify_view(name)
        except ValueError as exc:
            violations.append({"view": name, "reason": str(exc)})
            continue
        by_layer[layer] += 1

    payload: dict[str, object] = {
        "total_views": len(view_names),
        "by_layer": dict(sorted(by_layer.items())),
        "violations": violations,
        "source_sql": str(sql_path),
        "allowed_layers": list(ALLOWED_LAYERS),
    }

    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def _default_paths() -> tuple[Path, Path]:
    repo_root = Path(__file__).resolve().parents[2]
    return (
        repo_root / "sql" / "duckdb_create_views.sql",
        repo_root / "docs" / "evidence" / "dbt_macro_check.json",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate Gold view naming convention in "
            "sql/duckdb_create_views.sql and write evidence JSON."
        )
    )
    parser.add_argument(
        "--sql",
        type=Path,
        default=None,
        help="Path to the DuckDB view registration SQL (default: sql/duckdb_create_views.sql)",
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=None,
        help="Path to write the evidence JSON to "
        "(default: docs/evidence/dbt_macro_check.json)",
    )
    args = parser.parse_args(argv)

    sql_path, evidence_path = _default_paths()
    sql_path = args.sql or sql_path
    evidence_path = args.evidence or evidence_path

    payload = check_duckdb_views(sql_path, evidence_path)
    print(
        f"Checked {payload['total_views']} views; "
        f"layers: {payload['by_layer']}; "
        f"violations: {len(payload['violations'])}"
    )
    return 0 if not payload["violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
