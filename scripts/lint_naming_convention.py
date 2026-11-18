"""
Naming convention linter (plan phase-02-data-model.md, Step 7 / F9, F10, F18).

Parses the SQL DDL files that are the source of truth for table and column
names (``sql/schema_evidence.sql`` for bronze/silver/gold, ``sql/init_ops.sql``
for ``ops``, ``sql/init_ml.sql`` for ``ml``) and enforces the
``docs/architecture/data-model.md`` §Naming Convention block:

- gold tables: singular, one of ``dim_`` / ``fact_`` / ``obt_`` / ``feat_``
- bronze tables: ``raw_`` prefix, plural feed name
- silver tables: ``stg_`` prefix, plural feed name
- no version token (``_v1``, ``_v2``, ...) in any table name
- no ``_at``-suffixed column in ``ops``
- the two reserved Feast column names (``event_timestamp``,
  ``created_timestamp``) are never renamed

Exits 0 with zero findings; exits 1 and prints every finding otherwise. Wired
into ``scripts/run_lakehouse_quality_gates.py``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?P<name>[A-Za-z0-9_.]+)\s*\((?P<body>.*?)\n\);",
    re.IGNORECASE | re.DOTALL,
)
COLUMN_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+[A-Za-z]", re.MULTILINE)
VERSION_TOKEN_RE = re.compile(r"_v\d+$", re.IGNORECASE)

GOLD_PREFIXES = ("dim_", "fact_", "obt_", "feat_")
RESERVED_FEAST_NAMES = {"event_timestamp", "created_timestamp"}

# Words that legitimately end in "s" but are singular gold entities/concepts —
# none exist today; kept as an explicit empty allowlist so a future table name
# collision is a deliberate decision, not a silent lint bypass.
GOLD_SINGULAR_ALLOWLIST: frozenset[str] = frozenset()

# Table-level SQL keywords that are not column definitions, so COLUMN_RE
# should skip lines starting with these.
NON_COLUMN_LINE_RE = re.compile(
    r"^\s*(PRIMARY\s+KEY|UNIQUE|FOREIGN\s+KEY|CHECK|CONSTRAINT)\b", re.IGNORECASE
)


def _find_tables(sql_text: str) -> list[tuple[str, list[str]]]:
    """Return ``[(schema.table, [column_name, ...]), ...]`` from CREATE TABLE statements."""

    tables: list[tuple[str, list[str]]] = []
    for match in CREATE_TABLE_RE.finditer(sql_text):
        name = match.group("name")
        body = match.group("body")
        columns = []
        for line in body.splitlines():
            if NON_COLUMN_LINE_RE.match(line):
                continue
            col_match = COLUMN_RE.match(line)
            if col_match:
                columns.append(col_match.group(1))
        tables.append((name, columns))
    return tables


# Mass/uncountable nouns that end in "s" but are grammatically singular —
# a naive endswith("s") check would misclassify them as plural.
SINGULAR_S_WORDS = frozenset({"news", "status", "series"})


def _looks_plural(noun: str) -> bool:
    """Heuristic: at least one underscore-separated word segment is plural.

    Feed names are often compound (``market_prices_daily``): the plural
    marker lives on the feed noun, not necessarily on the trailing
    qualifier, so every segment is checked rather than only the last one.
    """

    return any(
        word.endswith("s") and not word.endswith("ss") and word not in SINGULAR_S_WORDS
        for word in noun.split("_")
    )


def lint_gold_table(table: str) -> list[str]:
    errors = []
    schema, _, bare = table.partition(".")
    if VERSION_TOKEN_RE.search(bare):
        errors.append(
            f"{table}: table name carries a version token — versions live in Iceberg tags"
        )
    prefix = next((p for p in GOLD_PREFIXES if bare.startswith(p)), None)
    if prefix is None:
        errors.append(
            f"{table}: gold table has no declared prefix (expected one of {GOLD_PREFIXES})"
        )
        return errors
    noun = bare[len(prefix) :]
    if _looks_plural(noun) and bare not in GOLD_SINGULAR_ALLOWLIST:
        errors.append(f"{table}: gold table name is plural ({noun!r}) — gold nouns are singular")
    if "table" in noun:
        errors.append(f"{table}: table name contains the literal word 'table'")
    return errors


def lint_bronze_table(table: str) -> list[str]:
    errors = []
    _, _, bare = table.partition(".")
    if not bare.startswith("raw_"):
        errors.append(f"{table}: bronze table missing required 'raw_' prefix")
    else:
        noun = bare[len("raw_") :]
        if not _looks_plural(noun):
            errors.append(f"{table}: bronze feed name {noun!r} should be plural")
    return errors


def lint_silver_table(table: str) -> list[str]:
    errors = []
    _, _, bare = table.partition(".")
    if not bare.startswith("stg_"):
        errors.append(f"{table}: silver table missing required 'stg_' prefix")
    else:
        noun = bare[len("stg_") :]
        if not _looks_plural(noun):
            errors.append(f"{table}: silver feed name {noun!r} should be plural")
    return errors


def lint_ops_columns(table: str, columns: list[str]) -> list[str]:
    errors = []
    for column in columns:
        if column in RESERVED_FEAST_NAMES:
            continue
        if column.endswith("_at"):
            errors.append(f"{table}.{column}: '_at' suffix is banned in ops — use '_ts'")
    return errors


def lint_feast_reserved_names(table: str, columns: list[str]) -> list[str]:
    """Gold feat_* tables must declare both reserved Feast column names verbatim."""

    errors = []
    _, _, bare = table.partition(".")
    if not bare.startswith("feat_"):
        return errors
    for reserved in RESERVED_FEAST_NAMES:
        if reserved not in columns:
            errors.append(f"{table}: missing reserved Feast column {reserved!r}")
    return errors


def lint_file(path: Path) -> list[str]:
    if not path.is_file():
        return [f"{path}: file not found"]
    text = path.read_text(encoding="utf-8")
    findings: list[str] = []
    for table, columns in _find_tables(text):
        schema = table.partition(".")[0]
        if schema == "gold":
            findings.extend(lint_gold_table(table))
            findings.extend(lint_feast_reserved_names(table, columns))
        elif schema == "bronze":
            findings.extend(lint_bronze_table(table))
        elif schema == "silver":
            findings.extend(lint_silver_table(table))
        elif schema == "ops":
            findings.extend(lint_ops_columns(table, columns))
        if VERSION_TOKEN_RE.search(table.partition(".")[2]):
            findings.append(f"{table}: table name carries a version token")
    return findings


def main() -> int:
    targets = [
        REPO_ROOT / "sql" / "schema_evidence.sql",
        REPO_ROOT / "sql" / "init_ops.sql",
        REPO_ROOT / "sql" / "init_ml.sql",
    ]
    all_findings: list[str] = []
    for target in targets:
        all_findings.extend(lint_file(target))

    if all_findings:
        for finding in all_findings:
            print(finding)
        print(f"\n{len(all_findings)} naming-convention finding(s) — FAIL")
        return 1
    print("Naming convention: 0 findings across", len(targets), "SQL files — PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
