"""Tests that the silver_to_gold wrapper for build_distress_labels is removed (P-D).

The wrapper is a needless re-export; callers must import compute_distress_labels.compute_labels
directly and produce identical output.
"""
import importlib


def test_silver_to_gold_does_not_expose_build_distress_labels():
    mod = importlib.import_module("src.transforms.silver_to_gold")
    assert not hasattr(mod, "build_distress_labels")
    assert "build_distress_labels" not in getattr(mod, "__all__", [])


def test_no_remaining_build_distress_labels_imports_in_src_or_dags():
    import subprocess

    result = subprocess.run(
        [
            "rg",
            "-n",
            "--no-ignore",
            "build_distress_labels",
            "src/",
            "dags/",
            "tests/",
        ],
        capture_output=True,
        text=True,
    )
    # rg exit 0 = found, 1 = not found, 2 = error
    assert result.returncode == 1, (
        f"build_distress_labels still referenced:\n{result.stdout}"
    )


def test_dag_06_imports_compute_labels_directly():
    from pathlib import Path

    src = Path("dags/06_pyspark_silver_to_gold.py").read_text()
    assert "compute_distress_labels.compute_labels" in src
    assert "build_distress_labels" not in src


def test_stage1_evidence_job_imports_compute_labels_directly():
    from pathlib import Path

    src = Path("src/jobs/stage1_evidence_job.py").read_text()
    assert "compute_distress_labels.compute_labels" in src
    assert "build_distress_labels" not in src


def test_wrapper_removal_preserves_distress_label_output():
    """Behavioral equivalence: compute_labels direct call must equal what the old wrapper returned."""
    from src.transforms.compute_distress_labels import compute_labels

    rows = [
        {
            "ticker": "AAA",
            "report_period": "2025Q4",
            "total_assets": 1000,
            "total_liabilities": 500,
            "equity": 500,
            "current_assets": 300,
            "current_liabilities": 200,
            "net_income": 80,
            "ebit": 120,
            "interest_expense": 20,
        }
    ]
    labels = compute_labels(rows)
    assert len(labels) == 1
    assert labels[0]["ticker"] == "AAA"
    assert labels[0]["report_period"] == "2025Q4"
    assert "distress_label" in labels[0]
