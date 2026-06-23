"""W21 data governance lite invariants.

The W21 plan locks a self-contained governance story for Phase 1:

- ``docs/07_data_contracts.md`` lists every Bronze/Silver/Gold table with
  schema, owner, source, refresh cadence, primary keys, expected row count
  range, partition columns, upstream tables, downstream consumers.
- ``src/quality/contract_checker.py`` loads the contract doc, validates an
  actual schema against it, and writes 6 evidence JSONs to
  ``docs/evidence/governance/`` (3 lineage + 3 validation, one per DP).
- ``dags/09_data_governance.py`` wires the checker as the terminal task of
  each DP so the evidence is regenerated on every run.

These tests parse the source files and assert the rules. They start RED in
W21 commit 1 and turn GREEN once the artifacts are added.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DOC = REPO_ROOT / "docs" / "07_data_contracts.md"
SCHEMA_DOC = REPO_ROOT / "docs" / "02_schema_design.md"
CONTRACT_CHECKER_MODULE = "src.quality.contract_checker"
DAG_FILE = REPO_ROOT / "dags" / "09_data_governance.py"
EVIDENCE_DIR = REPO_ROOT / "docs" / "evidence" / "governance"

# Every Gold table name from docs/02_schema_design.md that must be covered.
EXPECTED_GOLD_TABLES = {
    "dim_company",
    "dim_date",
    "fact_financial_statement",
    "fact_market_price",
    "fact_market_alert",
    "fact_news_sentiment",
    "distress_labels",
    "obt_company_quarter_risk",
    "feat_company_financial_4q",
    "feat_company_market_30d",
    "feat_company_news_30d",
    "feat_company_unified",
}

EXPECTED_BRONZE_SILVER = {
    "raw_company",
    "stg_company",
    "stg_company_quarter",
    "fact_company_quarter_financials",
}


def _read(path: Path) -> str:
    assert path.exists(), f"Required source file missing: {path}"
    return path.read_text(encoding="utf-8")


def _list_gold_tables_from_schema_doc() -> set[str]:
    """Extract every Gold table name referenced in ``docs/02_schema_design.md``."""
    text = _read(SCHEMA_DOC)
    found: set[str] = set()
    for folder_match in re.finditer(r"gold/(?P<name>[a-z_]+)/", text):
        found.add(folder_match.group("name"))
    return found


# --- Contract doc tests --------------------------------------------------------


def test_contract_doc_exists_and_lists_all_gold_tables() -> None:
    text = _read(CONTRACTS_DOC)
    expected = _list_gold_tables_from_schema_doc()
    missing = expected - set(re.findall(r"`([a-z_]+)`", text))
    assert not missing, (
        f"docs/07_data_contracts.md must reference every Gold table from "
        f"docs/02_schema_design.md; missing: {sorted(missing)}"
    )


def test_contract_doc_has_lineage_section_per_dp() -> None:
    text = _read(CONTRACTS_DOC)
    for dp in ("DP1", "DP2", "DP3"):
        pattern = rf"##\s+Lineage\s+{dp}\b"
        assert re.search(pattern, text), (
            f"docs/07_data_contracts.md must have a '## Lineage {dp}' section"
        )


# --- Module import + API tests -------------------------------------------------


def test_contract_checker_module_loads() -> None:
    import importlib

    module = importlib.import_module(CONTRACT_CHECKER_MODULE)
    for attr in ("load_contracts", "validate_against_schema", "write_dp_evidence"):
        assert hasattr(module, attr), (
            f"src.quality.contract_checker must expose {attr}()"
        )


def test_load_contracts_parses_doc() -> None:
    from src.quality.contract_checker import load_contracts

    contracts = load_contracts(CONTRACTS_DOC)
    assert isinstance(contracts, dict)
    expected_count = len(EXPECTED_GOLD_TABLES | EXPECTED_BRONZE_SILVER)
    assert len(contracts) >= expected_count, (
        f"load_contracts must return at least {expected_count} entries"
    )
    for required in EXPECTED_GOLD_TABLES | EXPECTED_BRONZE_SILVER:
        assert required in contracts, f"load_contracts must include {required!r}"


def test_validate_against_schema_passes_on_match() -> None:
    from src.quality.contract_checker import (
        load_contracts,
        validate_against_schema,
    )

    contracts = load_contracts(CONTRACTS_DOC)
    contract = contracts["dim_company"]
    # Build a minimal actual schema that satisfies the contract.
    actual = {col.name: col.dtype for col in contract.columns}
    result = validate_against_schema(contract, actual)
    assert result.passed, f"validation should pass on matching schema: {result}"


def test_validate_against_schema_fails_on_missing_column() -> None:
    from src.quality.contract_checker import (
        load_contracts,
        validate_against_schema,
    )

    contracts = load_contracts(CONTRACTS_DOC)
    contract = contracts["dim_company"]
    # Drop the first column to simulate a missing column.
    actual = {col.name: col.dtype for col in contract.columns[1:]}
    result = validate_against_schema(contract, actual)
    assert not result.passed, "validation should fail when a required column is missing"


# --- Evidence JSON tests -------------------------------------------------------


def _evidence_paths() -> dict[str, Path]:
    return {
        "dp1_lineage": EVIDENCE_DIR / "dp1_lineage.json",
        "dp1_validation": EVIDENCE_DIR / "dp1_validation.json",
        "dp2_lineage": EVIDENCE_DIR / "dp2_lineage.json",
        "dp2_validation": EVIDENCE_DIR / "dp2_validation.json",
        "dp3_lineage": EVIDENCE_DIR / "dp3_lineage.json",
        "dp3_validation": EVIDENCE_DIR / "dp3_validation.json",
    }


def test_write_dp_evidence_creates_6_files(tmp_path: Path) -> None:
    from src.quality.contract_checker import (
        load_contracts,
        write_dp_evidence,
    )

    contracts = load_contracts(CONTRACTS_DOC)
    for dp in ("dp1", "dp2", "dp3"):
        write_dp_evidence(contracts, dp, tmp_path)
    written = sorted(p.name for p in tmp_path.glob("*.json"))
    assert written == [
        "dp1_lineage.json",
        "dp1_validation.json",
        "dp2_lineage.json",
        "dp2_validation.json",
        "dp3_lineage.json",
        "dp3_validation.json",
    ], f"unexpected evidence files: {written}"


def test_dp_lineage_json_has_required_keys() -> None:
    paths = _evidence_paths()
    for name, path in paths.items():
        assert path.exists(), f"missing evidence file: {path}"
        data = json.loads(path.read_text(encoding="utf-8"))
        if name.endswith("_lineage"):
            for key in ("dp", "dataset", "upstream", "downstream"):
                assert key in data, f"{path.name} must contain {key!r} key"
        else:
            required = ("dp", "dataset", "dq_passed", "row_count", "schema_match", "contract_check")
            for key in required:
                assert key in data, f"{path.name} must contain {key!r} key"


def test_dp_validation_json_has_dq_results() -> None:
    paths = _evidence_paths()
    for name, path in paths.items():
        if not name.endswith("_validation"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data["dq_passed"], bool)
        assert isinstance(data["row_count"], int)
        assert isinstance(data["schema_match"], bool)
        assert isinstance(data["contract_check"], bool)


# --- DAG wire test -------------------------------------------------------------


def test_dag_09_data_governance_imports() -> None:
    text = _read(DAG_FILE)
    # The DAG must declare 3 contract check tasks.
    for task_id in ("check_dp1_contracts", "check_dp2_contracts", "check_dp3_contracts"):
        assert task_id in text, f"dags/09_data_governance.py must define {task_id!r}"
    # The module must be importable in a subprocess so Airflow does not break CI.
    import_cmd = (
        "import importlib; "
        "m = importlib.import_module('dags.09_data_governance'); "
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", import_cmd],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, f"dags.09_data_governance failed to import: {result.stderr}"
    assert "ok" in result.stdout
