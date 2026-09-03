"""Contracts for the platform .eployable catalog and GitOps path guard."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ci.catalog import CatalogError, load_catalog, validate_catalog
from scripts.ci.gitops_paths import GitOpsPathError, resolve_gitops_path

REPO_ROOT = Path(__file__).resolve().parents[2]
GITOPS_ROOT = REPO_ROOT.parent / "financial-distress-gitops"


def test_catalog_contains_all_unique_deployables() -> None:
    entries = load_catalog()
    # feature-api/drift-api (ML-track) removed 2026-08-14 — LLM submission
    # does not need them; see configs/platform-deployables.yaml header.
    assert len(entries) == 8
    assert len({entry.name for entry in entries}) == len(entries)
    assert all(entry.test_args for entry in entries)


def test_catalog_source_paths_validate() -> None:
    validate_catalog(load_catalog(), source_root=REPO_ROOT)


def test_catalog_gitops_paths_validate_when_checkout_is_available() -> None:
    if not GITOPS_ROOT.is_dir():
        pytest.skip("GitOps checkout is not available")
    validate_catalog(load_catalog(), source_root=REPO_ROOT, gitops_root=GITOPS_ROOT)


def test_wrong_gitops_path_fails(tmp_path: Path) -> None:
    with pytest.raises(GitOpsPathError, match="escapes checkout"):
        resolve_gitops_path(tmp_path, "../outside.yaml")


def test_catalog_reports_wrong_gitops_path(tmp_path: Path) -> None:
    entry = load_catalog()[0]
    with pytest.raises(CatalogError, match="does not exist"):
        validate_catalog((entry,), source_root=REPO_ROOT, gitops_root=tmp_path)
