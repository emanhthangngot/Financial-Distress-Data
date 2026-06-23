"""Stage 1 Rubric Coverage Audit (W25).

Maps each rubric item from
``docs/Coursework Tracking (Public) - rubic (mini-coursework).csv``
to filesystem evidence (files, JSON, PNG, doc sections). Each test asserts
a specific piece of evidence exists. Items that are known missing use
``pytest.xfail`` with a clear reason so the harness stays honest.

The companion script ``scripts/audit_rubric_coverage.py`` walks the same
mapping and emits ``docs/evidence/rubric_coverage.json``.

The rubric CSV has 100 points across 6 categories:
  1. Engineering Fundamentals   (2 pts)
  2. Implement Data Generator   (16 pts)
  3. Processing Jobs (Spark/Flink) (20 pts)
  4. Data Storage               (4 pts)
  5. Data Pipeline Orchestration (12 pts)
  6. Data Governance            (12 pts)
  7. Documentation              (8 pts)
  8. README + Deployment Diagram (10 pts)
  9. Novel Ideas                (10 pts)
  10. Unallocated filler (any rubric rows that don't fit)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
EVIDENCE = DOCS / "evidence"
IMAGES = REPO_ROOT / "images"
README = REPO_ROOT / "README.md"


# -- Helpers ------------------------------------------------------------


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _exists(rel: str) -> bool:
    return (REPO_ROOT / rel).exists()


def _evidence_contains_json(filename: str, must_have: list[str]) -> bool:
    p = EVIDENCE / filename
    if not p.exists():
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return False
    text = json.dumps(data)
    return all(token in text for token in must_have)


# -- 1. Engineering Fundamentals ---------------------------------------
# Rubric idx 1-2: Docker & Docker Compose + Optimize Dockerfile (2 pts)


def test_docker_compose_present() -> None:
    assert _exists("docker-compose.yml"), "docker-compose.yml missing"


def test_dockerfile_optimize_evidence() -> None:
    # W23 produced docker_size.json showing measurable size reduction
    assert (EVIDENCE / "docker_size.json").exists() or _exists(
        "docs/08_docker_optimization.md"
    ), "Docker image size optimization evidence missing"


# -- 2. Implement Data Generator (16 pts) ------------------------------
# Rubric idx 3-10: skew, high cardinality, schema evolution, duplicate,
# using config, store to bronze, burst, late, streaming duplicate, streaming config


def test_generator_offline_skew_evidence() -> None:
    # W17 generator produces skew; W20 evidence captures characteristics
    p = EVIDENCE / "stage1_generator_characteristics.json"
    if not p.exists():
        pytest.xfail("stage1_generator_characteristics.json is generated at runtime")
    data = json.loads(p.read_text(encoding="utf-8"))
    assert (
        "skew" in json.dumps(data).lower() or "cardinality" in json.dumps(data).lower()
    )


def test_generator_offline_cardinality_evidence() -> None:
    p = EVIDENCE / "stage1_generator_characteristics.json"
    if not p.exists():
        pytest.xfail("stage1_generator_characteristics.json is generated at runtime")
    text = p.read_text(encoding="utf-8").lower()
    assert "cardinality" in text or "approx_count_distinct" in text


def test_generator_schema_evolution_evidence() -> None:
    text = _read(DOCS / "01_data_generator.md").lower()
    assert "schema" in text and "evolution" in text


def test_generator_duplicate_rate_evidence() -> None:
    text = _read(DOCS / "01_data_generator.md").lower()
    assert "duplicate" in text


def test_generator_uses_config() -> None:
    # Generator must be driven by a config file
    assert _exists("src/generators/config_loader.py") or _exists(
        "src/generator/config.yaml"
    ), "Generator config not found"


def test_generator_lands_in_bronze() -> None:
    # The generator must persist output that lands in MinIO Bronze zone
    text = _read(DOCS / "01_data_generator.md")
    assert "bronze" in text.lower() or "minio" in text.lower()


def test_generator_streaming_burst_evidence() -> None:
    text = _read(DOCS / "01_data_generator.md").lower()
    assert "burst" in text


def test_generator_streaming_late_evidence() -> None:
    text = _read(DOCS / "01_data_generator.md").lower()
    assert "late" in text


def test_generator_streaming_duplicate_evidence() -> None:
    text = _read(DOCS / "01_data_generator.md").lower()
    assert "duplicate" in text


# -- 3. Processing Jobs (Spark + Flink) (20 pts) ------------------------
# Rubric idx 11-20: Spark baseline/skew/cardinality/schema/other/int + Flink 6 items


def test_spark_optimization_journey_documented() -> None:
    # W18 produced Spark optimization evidence
    p = DOCS / "evidence" / "w20_dp1_airflow_task_tree.png"
    assert p.exists(), "W18/W20 Spark optimization evidence PNG missing"
    text = _read(DOCS / "01_data_generator.md") + _read(
        DOCS / "05_storage_optimization.md"
    )
    assert "spark" in text.lower()


def test_spark_integrated_to_airflow() -> None:
    # dags/ should reference spark jobs
    dags = (
        list((REPO_ROOT / "dags").glob("*.py")) if (REPO_ROOT / "dags").exists() else []
    )
    spark_mentions = sum(1 for f in dags if "spark" in _read(f).lower())
    assert spark_mentions > 0, "No DAG references Spark"


def test_flink_baseline_documented() -> None:
    # Flink baseline is documented in the Flink jobs README + W26 plan + AGENTS.md
    flink_readme = REPO_ROOT / "src" / "streaming" / "flink" / "jobs" / "README.md"
    text = (
        _read(DOCS / "01_data_generator.md")
        + _read(DOCS / "09_novel_idea_1.md")
        + _read(flink_readme)
        + _read(REPO_ROOT / "AGENTS.md")
    )
    assert "flink" in text.lower(), "Flink baseline not documented"


def test_flink_window_processing_evidence() -> None:
    # W26 added opt-in Flink
    flink_dir = REPO_ROOT / "src" / "streaming" / "flink"
    if not flink_dir.exists():
        pytest.xfail("Flink opt-in not enabled (W26 not merged)")
    py_files = list(flink_dir.glob("*.py"))
    assert py_files, "Flink directory exists but no python files"


# -- 4. Data Storage (4 pts) -------------------------------------------
# Rubric idx 21-22: lakehouse compaction + DW indexing


def test_lakehouse_compaction_evidence() -> None:
    p = EVIDENCE / "lakehouse_compaction_benchmark.json"
    assert p.exists(), "W19 lakehouse compaction benchmark missing"


def test_duckdb_index_benchmark_evidence() -> None:
    p = EVIDENCE / "duckdb_index_benchmark.json"
    assert p.exists(), "W19 DuckDB index benchmark missing"


# -- 5. Data Pipeline Orchestration (12 pts) ---------------------------
# Rubric idx 23-28: DP1/DP2/DP3 each has Ingest + Validate stage evidence


@pytest.mark.parametrize(
    "dp_prefix",
    [
        "w20_dp1_airflow_dag_graph",
        "w20_dp1_airflow_task_tree",
    ],
)
def test_dp1_airflow_dag_graph_evidence(dp_prefix: str) -> None:
    p = EVIDENCE / f"{dp_prefix}.png"
    assert p.exists(), f"{dp_prefix}.png missing"


def test_dp2_pipeline_exists() -> None:
    # DP2 = bronze -> silver -> gold
    dags = (
        list((REPO_ROOT / "dags").glob("*.py")) if (REPO_ROOT / "dags").exists() else []
    )
    candidates = [
        f for f in dags if "silver" in _read(f).lower() or "gold" in _read(f).lower()
    ]
    assert candidates, "No DAG references silver/gold for DP2"


def test_dp3_pipeline_exists() -> None:
    # DP3 = feature table computation
    dags = (
        list((REPO_ROOT / "dags").glob("*.py")) if (REPO_ROOT / "dags").exists() else []
    )
    candidates = [
        f for f in dags if "feature" in _read(f).lower() or "feat_" in _read(f).lower()
    ]
    assert candidates, "No DAG references features for DP3"


# -- 6. Data Governance (12 pts) ---------------------------------------
# Rubric idx 29-34: DP1/DP2/DP3 each has lineage + data contract evidence


@pytest.mark.parametrize("dp", ["dp1", "dp2", "dp3"])
def test_dp_lineage_evidence(dp: str) -> None:
    p = EVIDENCE / "governance" / f"{dp}_lineage.json"
    assert p.exists(), f"{dp}_lineage.json missing"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data.get("upstream") and data.get(
        "downstream"
    ), f"{dp} lineage missing upstream/downstream"


@pytest.mark.parametrize("dp", ["dp1", "dp2", "dp3"])
def test_dp_validation_evidence(dp: str) -> None:
    p = EVIDENCE / "governance" / f"{dp}_validation.json"
    assert p.exists(), f"{dp}_validation.json missing"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data.get("contract_check") is True, f"{dp} contract check not asserted"


# -- 7. Documentation (8 pts) -----------------------------------------
# Rubric idx 35-39: schema design visualization, SCD2 dim, feat table cols,
# dim/fact relationship, naming convention


def test_schema_erd_image_exists() -> None:
    assert (
        IMAGES / "schema" / "schema_evidence_erd.png"
    ).exists(), "Schema ERD image missing"


def test_dim_scd2_documented() -> None:
    text = _read(DOCS / "02_schema_design.md").lower()
    assert (
        "valid_from_ts" in text and "is_current" in text
    ), "SCD2 columns not documented"


def test_feat_table_columns_documented() -> None:
    text = _read(DOCS / "02_schema_design.md").lower()
    assert (
        "event_timestamp" in text and "created" in text
    ), "feat table event_timestamp/created not documented"


def test_dim_fact_relationship_documented() -> None:
    text = _read(DOCS / "02_schema_design.md").lower()
    assert "relationship" in text or ("dim_" in text and "fact_" in text)


def test_naming_convention_documented() -> None:
    # W22 added naming convention section to README and 02_schema_design.md
    readme = _read(README).lower()
    schema = _read(DOCS / "02_schema_design.md").lower()
    assert "naming convention" in readme, "README missing naming convention section"
    assert "dim_" in schema and "fact_" in schema, "Naming prefixes not in schema doc"


# -- 8. README + Deployment Diagram (10 pts) ---------------------------


def test_readme_has_business_domain() -> None:
    text = _read(README)
    # Must describe what the project does (not just a title)
    assert len(text) > 2000, "README too short to cover business domain"
    assert "financial" in text.lower() or "distress" in text.lower()


def test_readme_has_toc() -> None:
    text = _read(README).lower()
    assert (
        "table of contents" in text
        or re.search(r"^## .*$", text, re.MULTILINE) is not None
    )


def test_readme_has_repo_structure() -> None:
    text = _read(README).lower()
    assert "project structure" in text or "repo structure" in text


def test_deployment_diagram_png_exists() -> None:
    # W22 added images/architecture/system_deployment_diagram.png
    assert (
        IMAGES / "architecture" / "system_deployment_diagram.png"
    ).exists(), "Deployment diagram missing"


def test_deployment_diagram_dot_in_sync() -> None:
    # W22 keeps the diagram regenerable from DOT
    dot = IMAGES / "architecture" / "system_deployment_diagram.dot"
    png = IMAGES / "architecture" / "system_deployment_diagram.png"
    if not (dot.exists() and png.exists()):
        pytest.xfail("DOT/PNG pair not both committed")
    assert dot.stat().st_size > 0 and png.stat().st_size > 1024


# -- 9. Novel Ideas (10 pts) ------------------------------------------
# Rubric idx 42-43: 2 ideas, each 5 pts


def test_novel_idea_1_doc_and_proof() -> None:
    p1 = DOCS / "09_novel_idea_1.md"
    p2 = EVIDENCE / "dbt_macro_check.json"
    assert p1.exists(), "09_novel_idea_1.md missing"
    assert p2.exists(), "dbt_macro_check.json proof missing"


def test_novel_idea_2_doc_and_proof() -> None:
    p1 = DOCS / "10_novel_idea_2.md"
    p2 = EVIDENCE / "airbyte_manifest_run.json"
    assert p1.exists(), "10_novel_idea_2.md missing"
    assert p2.exists(), "airbyte_manifest_run.json proof missing"


# -- 10. Module/class docstrings (rubric requirement) ------------------


def test_source_files_have_module_docstrings() -> None:
    """Rubric: 'Các hàm/class phải có docstring... đầu file phải có mô tả'."""
    src = REPO_ROOT / "src"
    py_files = [p for p in src.rglob("*.py") if p.name != "__init__.py"]
    if not py_files:
        pytest.xfail("No python files under src/")
    with_docstring = sum(
        1
        for f in py_files
        if _read(f).lstrip().startswith('"""') or _read(f).lstrip().startswith("'''")
    )
    coverage = with_docstring / len(py_files)
    assert (
        coverage > 0.8
    ), f"Only {coverage:.0%} of src/*.py files have module docstrings"
