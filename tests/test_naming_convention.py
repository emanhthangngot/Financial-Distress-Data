"""W22 naming convention invariants.

The W22 plan locks a single naming rule for the Gold layer:

- DuckDB view names: ``gold_{dim_|fact_|obt_|feat_}*``
- Gold storage paths: ``gold/{dim_*|fact_*|obt_*|feat_*|distress_labels}/``

These tests parse the relevant source files and assert the rules. They
exist as RED test seeds in W22 commit 1 and turn GREEN once the
convention is actually documented and applied.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SQL_VIEWS = REPO_ROOT / "sql" / "duckdb_create_views.sql"
JOB_FILE = REPO_ROOT / "src" / "jobs" / "stage1_spark_lakehouse_job.py"
README_FILE = REPO_ROOT / "README.md"
SCHEMA_DOC = REPO_ROOT / "docs" / "02_schema_design.md"

VIEW_NAME_RE = re.compile(
    r"^CREATE OR REPLACE VIEW\s+(?P<name>\w+)\s+AS\s*$",
    re.IGNORECASE,
)
ALLOWED_VIEW_LAYER_PREFIXES = ("dim_", "fact_", "obt_", "feat_")

# Captures the Gold folder name (everything between gold/ and the next /).
# Examples: s3a://bucket/gold/dim_company/ -> "dim_company"
#           s3a://bucket/gold/distress_labels/ -> "distress_labels"
GOLD_PATH_RE = re.compile(
    r"s3a://[^/\s'\"]+/gold/(?P<folder>[A-Za-z_]+)/",
)
ALLOWED_GOLD_LAYERS = {
    "dim_",
    "fact_",
    "obt_",
    "feat_",
    "distress_labels",
}


def _normalize_gold_folder(folder: str) -> str:
    """Reduce a full Gold folder name (e.g. dim_company) to its layer prefix (dim_)."""
    for prefix in ("dim_", "fact_", "obt_", "feat_"):
        if folder.startswith(prefix):
            return prefix
    return folder


def _read(path: Path) -> str:
    assert path.exists(), f"Required source file missing: {path}"
    return path.read_text(encoding="utf-8")


def _collect_gold_layers(text: str) -> set[str]:
    layers: set[str] = set()
    for match in GOLD_PATH_RE.finditer(text):
        layers.add(_normalize_gold_folder(match.group("folder")))
    return layers


def test_duckdb_view_names_follow_convention() -> None:
    """Every CREATE OR REPLACE VIEW must use the gold_{dim_|fact_|obt_|feat_}* pattern."""
    text = _read(SQL_VIEWS)
    view_names: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.upper().startswith("CREATE OR REPLACE VIEW"):
            continue
        match = VIEW_NAME_RE.match(stripped)
        if not match:
            continue
        view_names.append(match.group("name"))

    assert view_names, "No CREATE OR REPLACE VIEW statements found in duckdb_create_views.sql"

    for name in view_names:
        assert name.startswith("gold_"), f"View {name!r} violates the gold_ layer prefix rule"
        suffix = name[len("gold_") :]
        assert any(suffix.startswith(p) for p in ALLOWED_VIEW_LAYER_PREFIXES), (
            f"View {name!r} violates the convention: must start with one of "
            f"gold_{ALLOWED_VIEW_LAYER_PREFIXES}"
        )


def test_gold_storage_paths_in_spark_job() -> None:
    """Every s3a://.../gold/.../ write in the spark job must use an allowed Gold layer."""
    text = _read(JOB_FILE)
    layers_used = _collect_gold_layers(text)

    assert layers_used, "No s3a://.../gold/.../ paths found in stage1_spark_lakehouse_job.py"
    illegal = layers_used - ALLOWED_GOLD_LAYERS
    assert not illegal, (
        f"Spark job writes to illegal Gold layers {sorted(illegal)}; "
        f"allowed layers are {sorted(ALLOWED_GOLD_LAYERS)}"
    )


def test_gold_layers_actually_used() -> None:
    """Belt-and-braces: convention enforcement must cover the full known set."""
    text = _read(JOB_FILE)
    folders_used = {match.group("folder") for match in GOLD_PATH_RE.finditer(text)}

    for required in (
        "dim_company",
        "fact_financial_statement",
        "feat_company_unified",
        "distress_labels",
    ):
        assert (
            required in folders_used
        ), f"Expected Gold folder {required!r} missing from spark job paths"


def test_readme_documents_naming_convention() -> None:
    """The README must have a Naming Convention section that lists the rules."""
    text = _read(README_FILE)
    assert re.search(
        r"^##\s+Naming Convention\s*$", text, re.MULTILINE
    ), "README is missing the '## Naming Convention' section"
    section = _extract_section(text, "Naming Convention")
    for token in ("dim_", "fact_", "obt_", "feat_", "distress_labels"):
        assert token in section, f"README '## Naming Convention' section does not mention {token!r}"


def test_schema_design_doc_documents_naming_convention() -> None:
    """The schema design doc must reference the Gold layer prefix rules."""
    text = _read(SCHEMA_DOC)
    assert re.search(
        r"(?i)naming convention", text
    ), "docs/02_schema_design.md is missing a 'naming convention' reference"
    for token in ("dim_", "fact_", "obt_", "feat_", "distress_labels"):
        assert (
            token in text
        ), f"docs/02_schema_design.md does not mention required Gold token {token!r}"


def test_schema_design_doc_documents_bronze_silver_naming() -> None:
    """The schema design doc must document the raw_/stg_ equivalence for Bronze and Silver."""
    text = _read(SCHEMA_DOC)
    assert re.search(
        r"(?i)bronze and silver naming", text
    ), "docs/02_schema_design.md is missing a 'Bronze And Silver Naming' section"
    for token in ("bronze.companies", "silver.companies", "raw_", "stg_"):
        assert (
            token in text
        ), f"docs/02_schema_design.md does not mention required Bronze/Silver token {token!r}"


def test_readme_documents_deployment_diagram() -> None:
    """The README must reference the deployment diagram image by relative path."""
    text = _read(README_FILE)
    assert re.search(
        r"^##\s+System Deployment Diagram\s*$", text, re.MULTILINE
    ), "README is missing the '## System Deployment Diagram' section"
    section = _extract_section(text, "System Deployment Diagram")
    assert (
        "images/architecture/system_deployment_diagram.png" in section
    ), "README '## System Deployment Diagram' must embed the diagram PNG by relative path"


def _extract_section(text: str, heading: str) -> str:
    """Return the body of a level-2 markdown section, stopping at the next level-2 heading."""
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return ""
    return match.group("body")
