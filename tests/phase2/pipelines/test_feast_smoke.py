"""Real `feast plan`/`apply` against a disposable local registry + sqlite
online store — proves feature_repo/structured/definitions.py and
feature_repo/rag/definitions.py actually parse and register with a real
Feast install. Skipped unless `feast` is importable — it cannot run in
`.venv` (Feast lives only in `.venv-phase2`, D4)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("feast")

pytestmark = pytest.mark.slow

REPO_ROOT = Path(__file__).resolve().parents[3]
FEATURE_REPO = REPO_ROOT / "feature_repo"


def _feast_plan(
    repo_dir: Path, definitions_source: Path, tmp_path: Path
) -> subprocess.CompletedProcess:
    work_dir = tmp_path / repo_dir.name
    work_dir.mkdir()
    (work_dir / "definitions.py").write_text(
        definitions_source.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (work_dir / "feature_store.yaml").write_text(
        f"""
project: {repo_dir.name}_smoke
provider: local
registry: {work_dir / "registry.db"}
online_store:
  type: sqlite
offline_store:
  type: file
entity_key_serialization_version: 3
""",
        encoding="utf-8",
    )
    import os

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    feast_cli = str(Path(sys.executable).parent / "feast")
    return subprocess.run(
        [feast_cli, "plan"],
        cwd=work_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_structured_definitions_parse_and_register(tmp_path: Path) -> None:
    result = _feast_plan(
        FEATURE_REPO / "structured", FEATURE_REPO / "structured" / "definitions.py", tmp_path
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Created entity ticker" in result.stdout
    for view_name in (
        "company_financial_features",
        "company_risk_features",
        "market_price_features",
        "stream_market_features",
    ):
        assert f"Created feature view {view_name}" in result.stdout


def test_rag_definitions_parse_and_register(tmp_path: Path) -> None:
    result = _feast_plan(FEATURE_REPO / "rag", FEATURE_REPO / "rag" / "definitions.py", tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Created entity chunk_id" in result.stdout
    assert "Created feature view document_chunk_vectors" in result.stdout
