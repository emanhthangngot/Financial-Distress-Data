"""Contract tests for the auditor's lightweight artifact-path check."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_SCRIPT = REPO_ROOT / "scripts" / "audit_platform_evidence.py"


@pytest.fixture()
def audit_module():
    spec = importlib.util.spec_from_file_location("audit_platform_artifacts", AUDIT_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _row(
    rubric_id: str, evidence_type: str, artifact_repo: str, artifact_path: str
) -> dict[str, str]:
    return {
        "rubric_id": rubric_id,
        "evidence_type": evidence_type,
        "artifact_repo": artifact_repo,
        "artifact_path": artifact_path,
    }


def test_executed_missing_source_artifact_fails(audit_module, tmp_path: Path) -> None:
    audit_module.REPO_ROOT = tmp_path

    errors, warnings = audit_module._audit_artifacts(
        [_row("ML-executed-missing", "executed", "source", "src/ml/missing.py")],
        gitops_root=None,
    )

    assert warnings == []
    assert errors == ["ML-executed-missing: implementation artifact not found: src/ml/missing.py"]


def test_design_only_missing_artifact_is_a_warning(audit_module, tmp_path: Path) -> None:
    audit_module.REPO_ROOT = tmp_path

    errors, warnings = audit_module._audit_artifacts(
        [_row("ML-design-missing", "design_only", "source", "src/ml/planned.py")],
        gitops_root=None,
    )

    assert errors == []
    assert warnings == ["ML-design-missing: implementation artifact not found: src/ml/planned.py"]


def test_gitops_artifact_requires_explicit_root_and_resolves_when_given(
    audit_module, tmp_path: Path
) -> None:
    row = _row("LLM-gitops", "executed", "gitops", "platform/app/deployment.yaml")
    gitops_root = tmp_path / "financial-distress-gitops"
    artifact = gitops_root / row["artifact_path"]
    artifact.parent.mkdir(parents=True)
    artifact.write_text("kind: Deployment\n", encoding="utf-8")

    errors_without_root, _ = audit_module._audit_artifacts([row], gitops_root=None)
    assert errors_without_root == [
        "LLM-gitops: --gitops-root is required for GitOps artifact validation"
    ]

    errors, warnings = audit_module._audit_artifacts([row], gitops_root=gitops_root)
    assert errors == []
    assert warnings == []
