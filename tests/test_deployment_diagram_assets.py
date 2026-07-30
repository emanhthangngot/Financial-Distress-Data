"""W22 deployment diagram asset invariants.

These tests are RED until the deployment diagram PNG and DOT source are
copied into images/architecture/. They are part of the W22 deliverable
rubric row 60.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
IMG_DIR = REPO_ROOT / "images" / "architecture"

PNG_PATH = IMG_DIR / "system_deployment_diagram.png"
DOT_PATH = IMG_DIR / "system_deployment_diagram.dot"

MIN_PNG_BYTES = 50_000


def test_deployment_diagram_png_exists() -> None:
    """The deployment diagram PNG must be checked in at the expected path."""
    assert PNG_PATH.exists(), f"Missing diagram PNG at {PNG_PATH}"
    assert PNG_PATH.is_file(), f"{PNG_PATH} is not a regular file"


def test_deployment_diagram_png_is_nontrivial_size() -> None:
    """A blank/empty PNG (e.g. CI placeholder) must not satisfy the invariant."""
    assert PNG_PATH.exists(), f"Missing diagram PNG at {PNG_PATH}"
    size = PNG_PATH.stat().st_size
    assert size > MIN_PNG_BYTES, (
        f"Diagram PNG is suspiciously small ({size} bytes). "
        f"Expected a real rendered diagram larger than {MIN_PNG_BYTES} bytes."
    )


def test_deployment_diagram_png_is_actual_png() -> None:
    """Magic bytes 89 50 4E 47 0D 0A 1A 0A confirm a real PNG file."""
    assert PNG_PATH.exists(), f"Missing diagram PNG at {PNG_PATH}"
    with PNG_PATH.open("rb") as f:
        head = f.read(8)
    assert head == b"\x89PNG\r\n\x1a\n", f"{PNG_PATH} is not a valid PNG (got magic bytes {head!r})"


def test_deployment_diagram_dot_source_exists() -> None:
    """The DOT source must live next to the PNG so the diagram stays editable."""
    assert DOT_PATH.exists(), f"Missing DOT source at {DOT_PATH}"
    text = DOT_PATH.read_text(encoding="utf-8")
    assert text.strip(), f"{DOT_PATH} is empty"
    # Heuristic: a valid W22 deployment DOT must declare the graph and reference
    # the lakehouse components by name.
    assert "digraph" in text, f"{DOT_PATH} is missing the digraph declaration"
    for required in ("Airflow", "Kafka", "MinIO", "DuckDB", "PostgreSQL"):
        assert required in text, f"{DOT_PATH} does not mention required component {required!r}"


def test_deployment_diagram_dot_has_required_components() -> None:
    """The DOT source must declare each deployable unit as a cluster subgraph."""
    text = DOT_PATH.read_text(encoding="utf-8")
    # Each deployable unit the W22 plan calls out as a cluster.
    for cluster in (
        "cluster_collectors",
        "cluster_airflow",
        "cluster_kafka",
        "cluster_flink",
        "cluster_minio",
        "cluster_spark",
        "cluster_postgres",
        "cluster_duckdb",
        "cluster_dbeaver",
    ):
        assert cluster in text, f"{DOT_PATH} is missing required cluster subgraph {cluster!r}"


def test_architecture_directory_contains_only_known_files() -> None:
    """Lock the asset directory contents so stray files fail fast."""
    assert IMG_DIR.exists(), f"Missing architecture directory {IMG_DIR}"
    actual = {p.name for p in IMG_DIR.iterdir() if p.is_file()}
    expected = {
        "architecture-stage-1.png",
        "system_deployment_diagram.png",
        "system_deployment_diagram.dot",
    }
    assert actual == expected, (
        f"images/architecture/ contents drifted: actual={sorted(actual)} "
        f"expected={sorted(expected)}"
    )


def test_dot_source_uses_tb_layout() -> None:
    """The W22 plan locks TB layout so all edge labels render (LR + ortho drops them)."""
    text = DOT_PATH.read_text(encoding="utf-8")
    assert re.search(
        r"rankdir\s*=\s*TB", text
    ), f"{DOT_PATH} does not declare rankdir=TB; LR layout drops edge labels"
    assert re.search(
        r"splines\s*=\s*true", text
    ), f"{DOT_PATH} does not declare splines=true; required for curved edges with labels"
