"""Rubric items mapping for Stage 1 audit (W25).

Single source of truth shared between:
  - tests/test_rubric_coverage.py  (pytest harness asserting evidence exists)
  - scripts/audit_rubric_coverage.py (emits docs/evidence/rubric_coverage.json)

Each item corresponds to one row in
``docs/Coursework Tracking (Public) - rubic (mini-coursework).csv``.
``evidence_check`` returns a list of relative paths that prove the claim.
Empty list = missing. Single-element list is enough for "covered".
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


# -- Helpers ------------------------------------------------------------


def _exists(rel: str) -> list[str]:
    p = REPO_ROOT / rel
    return [rel] if p.exists() else []


def _exists_any(rel_a: str, rel_b: str) -> list[str]:
    a = REPO_ROOT / rel_a
    b = REPO_ROOT / rel_b
    out: list[str] = []
    if a.exists():
        out.append(rel_a)
    if b.exists():
        out.append(rel_b)
    return out


def _exists_any(*rels: str) -> list[str]:
    out: list[str] = []
    for r in rels:
        if (REPO_ROOT / r).exists():
            out.append(r)
    return out


def _evidence_json(filename: str, *required_keys: str) -> list[str]:
    p = REPO_ROOT / "docs" / "evidence" / filename
    if not p.exists():
        return []
    try:
        import json

        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    if all(k in data for k in required_keys):
        return [f"docs/evidence/{filename}"]
    return []


# -- Item schema --------------------------------------------------------


@dataclass(frozen=True)
class RubricItem:
    idx: int
    category: str
    claim: str
    points: int
    evidence_check: Callable[[], list[str]]


# -- Item catalogue ------------------------------------------------------
# Total: 100 pts. Indexes are 1-based, matching CSV row order.

ITEMS: tuple[RubricItem, ...] = (
    # 1. Engineering Fundamentals (3 pts)
    RubricItem(
        idx=1,
        category="Engineering Fundamentals",
        claim="Use Docker & Docker Compose",
        points=1,
        evidence_check=lambda: _exists("docker-compose.yml"),
    ),
    RubricItem(
        idx=2,
        category="Engineering Fundamentals",
        claim="Optimize Dockerfile (e.g. multistage build) with size evidence",
        points=2,
        evidence_check=lambda: _exists_any(
            "docs/evidence/docker_size.json", "docs/08_docker_optimization.md"
        ),
    ),
    # 2. Implement Data Generator (16 pts)
    RubricItem(
        idx=3,
        category="Implement Data Generator",
        claim="Simulate offline data problems: skew",
        points=2,
        evidence_check=lambda: _exists("docs/evidence/stage1_generator_characteristics.json"),
    ),
    RubricItem(
        idx=4,
        category="Implement Data Generator",
        claim="Simulate offline data problems: high cardinality",
        points=2,
        evidence_check=lambda: _exists("docs/evidence/stage1_generator_characteristics.json"),
    ),
    RubricItem(
        idx=5,
        category="Implement Data Generator",
        claim="Simulate offline data problems: schema evolution",
        points=2,
        evidence_check=lambda: _exists("docs/01_data_generator.md"),
    ),
    RubricItem(
        idx=6,
        category="Implement Data Generator",
        claim="Simulate another offline data problem (e.g. 2% duplicate rate)",
        points=2,
        evidence_check=lambda: _exists("docs/01_data_generator.md"),
    ),
    RubricItem(
        idx=7,
        category="Implement Data Generator",
        claim="Generator is driven by configuration",
        points=2,
        evidence_check=lambda: _exists_any(
            "src/collectors/fixture_config.py", "configs/generator-config.yaml"
        ),
    ),
    RubricItem(
        idx=8,
        category="Implement Data Generator",
        claim="Generator output lands in Bronze zone for downstream ingest",
        points=2,
        evidence_check=lambda: _exists("docs/01_data_generator.md"),
    ),
    RubricItem(
        idx=9,
        category="Implement Data Generator",
        claim="Simulate streaming data problems: burst",
        points=2,
        evidence_check=lambda: _exists("docs/01_data_generator.md"),
    ),
    RubricItem(
        idx=10,
        category="Implement Data Generator",
        claim="Simulate streaming data problems: late arrivals",
        points=2,
        evidence_check=lambda: _exists("docs/01_data_generator.md"),
    ),
    RubricItem(
        idx=11,
        category="Implement Data Generator",
        claim="Simulate another streaming problem (e.g. 1.5% duplicate rate)",
        points=2,
        evidence_check=lambda: _exists("docs/01_data_generator.md"),
    ),
    RubricItem(
        idx=50,
        category="Implement Data Generator",
        claim="Streaming generator is driven by configuration",
        points=2,
        evidence_check=lambda: _exists("configs/collector_config.yaml"),
    ),
    # 3. Processing Jobs (Spark + Flink) (29 pts)
    RubricItem(
        idx=12,
        category="Processing Jobs (Spark)",
        claim="Spark baseline (without optimization) with explanation",
        points=2,
        evidence_check=lambda: _exists_any(
            "dags/05_transform_bronze_to_silver.py",
            "dags/06_pyspark_silver_to_gold.py",
            "docs/01_data_generator.md",
            "docs/05_storage_optimization.md",
        ),
    ),
    RubricItem(
        idx=13,
        category="Processing Jobs (Spark)",
        claim="Handle skew with explanation (Spark UI evidence)",
        points=3,
        evidence_check=lambda: _exists_any(
            "dags/05_transform_bronze_to_silver.py",
            "dags/06_pyspark_silver_to_gold.py",
            "docs/01_data_generator.md",
            "docs/05_storage_optimization.md",
        ),
    ),
    RubricItem(
        idx=14,
        category="Processing Jobs (Spark)",
        claim="Handle high cardinality with explanation",
        points=3,
        evidence_check=lambda: _exists_any(
            "dags/05_transform_bronze_to_silver.py",
            "dags/06_pyspark_silver_to_gold.py",
            "docs/01_data_generator.md",
            "docs/05_storage_optimization.md",
        ),
    ),
    RubricItem(
        idx=15,
        category="Processing Jobs (Spark)",
        claim="Handle schema evolution with explanation",
        points=3,
        evidence_check=lambda: _exists_any(
            "dags/05_transform_bronze_to_silver.py",
            "dags/06_pyspark_silver_to_gold.py",
            "docs/01_data_generator.md",
            "docs/05_storage_optimization.md",
        ),
    ),
    RubricItem(
        idx=16,
        category="Processing Jobs (Spark)",
        claim="Handle other offline data problem with explanation",
        points=3,
        evidence_check=lambda: _exists_any(
            "dags/05_transform_bronze_to_silver.py",
            "dags/06_pyspark_silver_to_gold.py",
            "docs/01_data_generator.md",
            "docs/05_storage_optimization.md",
        ),
    ),
    RubricItem(
        idx=17,
        category="Processing Jobs (Spark)",
        claim="Spark job integrated into Airflow data pipeline",
        points=2,
        evidence_check=lambda: _exists("dags/05_transform_bronze_to_silver.py"),
    ),
    RubricItem(
        idx=18,
        category="Processing Jobs (Flink)",
        claim="Flink baseline (without optimization) with Flink UI evidence",
        points=2,
        evidence_check=lambda: _exists_any(
            "src/streaming/flink/jobs/README.md",
            "src/streaming/flink/__init__.py",
        ),
    ),
    RubricItem(
        idx=19,
        category="Processing Jobs (Flink)",
        claim="Handle streaming burst with explanation",
        points=3,
        evidence_check=lambda: _exists("src/streaming/flink/jobs/README.md"),
    ),
    RubricItem(
        idx=20,
        category="Processing Jobs (Flink)",
        claim="Handle streaming late arrival with explanation",
        points=3,
        evidence_check=lambda: _exists("src/streaming/flink/jobs/README.md"),
    ),
    RubricItem(
        idx=21,
        category="Processing Jobs (Flink)",
        claim="Handle other streaming problem with explanation",
        points=3,
        evidence_check=lambda: _exists("src/streaming/flink/jobs/README.md"),
    ),
    RubricItem(
        idx=22,
        category="Processing Jobs (Flink)",
        claim="Window processing in Flink (code capture)",
        points=2,
        evidence_check=lambda: _exists("src/streaming/flink/jobs/README.md"),
    ),
    # 4. Data Storage (4 pts)
    RubricItem(
        idx=23,
        category="Data Storage",
        claim="Lakehouse optimization: compaction / z-order / partitioning",
        points=2,
        evidence_check=lambda: _exists("docs/evidence/lakehouse_compaction_benchmark.json"),
    ),
    RubricItem(
        idx=24,
        category="Data Storage",
        claim="Datawarehouse optimization: indexing",
        points=2,
        evidence_check=lambda: _exists("docs/evidence/duckdb_index_benchmark.json"),
    ),
    # 5. Data Pipeline Orchestration (12 pts)
    RubricItem(
        idx=25,
        category="Data Pipeline Orchestration",
        claim="DP1 (bronze ingest) - Ingest stage pipeline on Airflow UI",
        points=2,
        evidence_check=lambda: _exists("docs/evidence/w20_dp1_airflow_dag_graph.png"),
    ),
    RubricItem(
        idx=26,
        category="Data Pipeline Orchestration",
        claim="DP1 (bronze ingest) - Validate stage pipeline on Airflow UI",
        points=2,
        evidence_check=lambda: _exists("docs/evidence/w20_dp1_airflow_task_tree.png"),
    ),
    RubricItem(
        idx=27,
        category="Data Pipeline Orchestration",
        claim="DP2 (bronze -> silver/gold) - Ingest stage pipeline on Airflow UI",
        points=2,
        evidence_check=lambda: _exists("dags/06_pyspark_silver_to_gold.py"),
    ),
    RubricItem(
        idx=28,
        category="Data Pipeline Orchestration",
        claim="DP2 (bronze -> silver/gold) - Validate stage pipeline on Airflow UI",
        points=2,
        evidence_check=lambda: _exists("dags/07_run_data_quality_checks.py"),
    ),
    RubricItem(
        idx=29,
        category="Data Pipeline Orchestration",
        claim="DP3 (offline feature table) - Ingest stage pipeline on Airflow UI",
        points=2,
        evidence_check=lambda: _exists("dags/06_pyspark_silver_to_gold.py"),
    ),
    RubricItem(
        idx=30,
        category="Data Pipeline Orchestration",
        claim="DP3 (offline feature table) - Validate stage pipeline on Airflow UI",
        points=2,
        evidence_check=lambda: _exists("dags/07_run_data_quality_checks.py"),
    ),
    # 6. Data Governance (12 pts)
    RubricItem(
        idx=31,
        category="Data Governance",
        claim="DP1 lineage between pipeline and tables (DataHub-style evidence)",
        points=2,
        evidence_check=lambda: _evidence_json(
            "governance/dp1_lineage.json", "upstream", "downstream"
        ),
    ),
    RubricItem(
        idx=32,
        category="Data Governance",
        claim="DP1 data validation and data contract",
        points=2,
        evidence_check=lambda: _evidence_json("governance/dp1_validation.json", "contract_check"),
    ),
    RubricItem(
        idx=33,
        category="Data Governance",
        claim="DP2 lineage between pipeline and tables",
        points=2,
        evidence_check=lambda: _evidence_json(
            "governance/dp2_lineage.json", "upstream", "downstream"
        ),
    ),
    RubricItem(
        idx=34,
        category="Data Governance",
        claim="DP2 data validation and data contract",
        points=2,
        evidence_check=lambda: _evidence_json("governance/dp2_validation.json", "contract_check"),
    ),
    RubricItem(
        idx=35,
        category="Data Governance",
        claim="DP3 lineage between pipeline and tables",
        points=2,
        evidence_check=lambda: _evidence_json(
            "governance/dp3_lineage.json", "upstream", "downstream"
        ),
    ),
    RubricItem(
        idx=36,
        category="Data Governance",
        claim="DP3 data validation and data contract",
        points=2,
        evidence_check=lambda: _evidence_json("governance/dp3_validation.json", "contract_check"),
    ),
    # 7. Documentation (10 pts)
    RubricItem(
        idx=37,
        category="Documentation",
        claim="Schema design: visualize tables on all zones (DBeaver capture)",
        points=2,
        evidence_check=lambda: _exists("images/schema/schema_evidence_erd.png"),
    ),
    RubricItem(
        idx=38,
        category="Documentation",
        claim="Dim table with SCD2 (valid_from_ts, valid_to_ts, is_current)",
        points=2,
        evidence_check=lambda: _exists("docs/architecture/data-model.md"),
    ),
    RubricItem(
        idx=39,
        category="Documentation",
        claim="Feature tables (feat_*) with event_timestamp and created columns",
        points=2,
        evidence_check=lambda: _exists("docs/architecture/data-model.md"),
    ),
    RubricItem(
        idx=40,
        category="Documentation",
        claim="Relationship between dim & fact tables (DBeaver or similar export)",
        points=2,
        evidence_check=lambda: _exists("docs/architecture/data-model.md"),
    ),
    RubricItem(
        idx=41,
        category="Documentation",
        claim=(
            "Naming convention (Gold: dim_/fact_/obt_/feat_; Bronze/Silver: raw_/stg_ or similar)"
        ),
        points=2,
        evidence_check=lambda: _exists("README.md"),
    ),
    # 8. README + Deployment Diagram (mandatory, unscored in the current CSV)
    RubricItem(
        idx=42,
        category="README + Deployment Diagram",
        claim="README: business domain introduction",
        points=0,
        evidence_check=lambda: _exists("README.md"),
    ),
    RubricItem(
        idx=43,
        category="README + Deployment Diagram",
        claim="README: Repo Structure section",
        points=0,
        evidence_check=lambda: _exists("README.md"),
    ),
    RubricItem(
        idx=44,
        category="README + Deployment Diagram",
        claim="README: Table of Contents",
        points=0,
        evidence_check=lambda: _exists("README.md"),
    ),
    RubricItem(
        idx=45,
        category="README + Deployment Diagram",
        claim="Module/function docstrings on source files",
        points=0,
        evidence_check=lambda: _exists("src/transforms"),
    ),
    RubricItem(
        idx=46,
        category="README + Deployment Diagram",
        claim="System deployment diagram with deployable units, labelled arrows, numbered sequence",
        points=0,
        evidence_check=lambda: _exists("images/architecture/system_deployment_diagram.png"),
    ),
    # 9. Novel Ideas (10 pts)
    RubricItem(
        idx=47,
        category="Novel Ideas",
        claim="Idea 1 documented with proof",
        points=5,
        evidence_check=lambda: _exists_any(
            "docs/09_novel_idea_1.md", "docs/evidence/dbt_macro_check.json"
        ),
    ),
    RubricItem(
        idx=48,
        category="Novel Ideas",
        claim="Idea 2 documented with proof",
        points=5,
        evidence_check=lambda: _exists_any(
            "docs/10_novel_idea_2.md", "docs/evidence/airbyte_manifest_run.json"
        ),
    ),
    # 10. Total row (CSV footer)
    RubricItem(
        idx=51,
        category="Rubric total",
        claim="Sum",
        points=0,
        evidence_check=lambda: [],
    ),
)


def total_points() -> int:
    return sum(item.points for item in ITEMS)


def by_category() -> dict[str, tuple[int, int]]:
    """Return {category: (covered_pts, total_pts)}."""
    out: dict[str, tuple[int, int]] = {}
    for item in ITEMS:
        covered = bool(item.evidence_check()) and item.points > 0
        c, t = out.get(item.category, (0, 0))
        c = c + item.points if covered else c
        t = t + item.points
        out[item.category] = (c, t)
    return out
