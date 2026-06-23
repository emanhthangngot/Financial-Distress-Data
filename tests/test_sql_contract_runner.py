"""W24 Idea 1 - dbt-style SQL contracts in DuckDB (RED seeds).

The W24 plan calls for a DuckDB macro that enforces a naming convention on
the Gold views defined in ``sql/duckdb_create_views.sql``, plus a Python
runner that mirrors the macro and writes evidence JSON. These tests assert
both the file artifacts and the runner behavior. They start RED in W24
commit 1 and turn GREEN once the runner is implemented in commit 2.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MACRO_SQL = REPO_ROOT / "src" / "quality" / "sql_contract_macros.sql"
RUNNER_MODULE = "src.quality.sql_contract_runner"
DUCKDB_VIEWS_SQL = REPO_ROOT / "sql" / "duckdb_create_views.sql"
EVIDENCE_JSON = REPO_ROOT / "docs" / "evidence" / "dbt_macro_check.json"

# Discovered from sql/duckdb_create_views.sql + docs/02_schema_design.md.
# Views are registered as ``gold_<layer>_<name>`` where layer is one of
# dim, fact, obt, feat. distress_labels is a Gold materialisation but is
# only read from the parquet directory directly (no view), so it does not
# show up in duckdb_create_views.sql and is therefore excluded here.
EXPECTED_LAYERS = {"dim", "fact", "obt", "feat"}


def test_macro_sql_file_exists() -> None:
    assert MACRO_SQL.exists(), f"missing macro file at {MACRO_SQL}"


def test_runner_module_loads() -> None:
    mod = importlib.import_module(RUNNER_MODULE)
    assert hasattr(mod, "classify_view"), "runner must expose classify_view()"
    assert hasattr(mod, "check_duckdb_views"), (
        "runner must expose check_duckdb_views()"
    )


@pytest.mark.parametrize(
    "view_name,expected_layer",
    [
        ("gold_dim_company", "dim"),
        ("gold_dim_date", "dim"),
        ("gold_fact_financial_statement", "fact"),
        ("gold_fact_market_price", "fact"),
        ("gold_fact_market_alert", "fact"),
        ("gold_fact_news_sentiment", "fact"),
        ("gold_obt_company_quarter_risk", "obt"),
        ("gold_feat_company_financial_4q", "feat"),
        ("gold_feat_company_market_30d", "feat"),
        ("gold_feat_company_news_30d", "feat"),
        ("gold_feat_company_unified", "feat"),
    ],
)
def test_classify_view_recognises_gold_prefixes(
    view_name: str, expected_layer: str
) -> None:
    mod = importlib.import_module(RUNNER_MODULE)
    assert mod.classify_view(view_name) == expected_layer


def test_classify_view_rejects_unknown_prefix() -> None:
    mod = importlib.import_module(RUNNER_MODULE)
    with pytest.raises(ValueError):
        mod.classify_view("gold_unknown_thing")


def test_check_duckdb_views_writes_evidence_json(tmp_path: Path) -> None:
    mod = importlib.import_module(RUNNER_MODULE)
    out = tmp_path / "dbt_macro_check.json"
    result = mod.check_duckdb_views(DUCKDB_VIEWS_SQL, out)
    assert out.exists(), "evidence JSON must be written"
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["total_views"] == result["total_views"]
    assert set(payload["by_layer"].keys()) == EXPECTED_LAYERS
    assert "violations" in payload
    assert payload["violations"] == []


def test_check_duckdb_views_no_violations(tmp_path: Path) -> None:
    mod = importlib.import_module(RUNNER_MODULE)
    out = tmp_path / "dbt_macro_check.json"
    result = mod.check_duckdb_views(DUCKDB_VIEWS_SQL, out)
    assert result["violations"] == []
    assert result["total_views"] == sum(result["by_layer"].values())
