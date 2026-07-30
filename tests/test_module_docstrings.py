"""Invariant tests for module-level docstring coverage.

These tests are the W19a regression lock. They fail loudly when a new .py file
is added without a module docstring, or when a docstring is reduced to a
trivial placeholder. The tests run offline (no network, no I/O beyond file
reads) and use only stdlib `ast` + `pathlib`.
"""

from __future__ import annotations

import ast
import pathlib
from collections.abc import Iterable

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _iter_python_files(directory: pathlib.Path) -> Iterable[pathlib.Path]:
    """Yield every .py file under `directory`, skipping __pycache__ and .venv."""
    for path in sorted(directory.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        if any(part.startswith(".") and part not in (".",) for part in path.parts):
            continue
        yield path


def _has_module_docstring(path: pathlib.Path) -> bool:
    """Return True if the file's AST module has a non-trivial docstring."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return False
    doc = ast.get_docstring(tree)
    if not doc:
        return False
    # Reject trivial single-line placeholders (less than 40 meaningful chars).
    return len(doc.strip()) >= 40


def _coverage_ratio(directory: pathlib.Path, exclude_init: bool = False) -> tuple[float, int, int]:
    """Return (ratio, covered, total) of files with module docstrings."""
    covered = 0
    total = 0
    for path in _iter_python_files(directory):
        if exclude_init and path.name == "__init__.py":
            continue
        total += 1
        if _has_module_docstring(path):
            covered += 1
    return (covered / total if total else 1.0), covered, total


def test_src_module_docstring_coverage_ge_95() -> None:
    """Production code under src/ must have module docstring coverage >= 95%."""
    ratio, covered, total = _coverage_ratio(REPO_ROOT / "src", exclude_init=True)
    assert ratio >= 0.95, (
        f"src/ module docstring coverage {ratio:.1%} ({covered}/{total}) below 95%. "
        "Add a module docstring (>= 40 chars) to each missing file."
    )


def test_dags_module_docstring_coverage_ge_90() -> None:
    """DAGs under dags/ must have module docstring coverage >= 90%."""
    ratio, covered, total = _coverage_ratio(REPO_ROOT / "dags")
    assert ratio >= 0.90, (
        f"dags/ module docstring coverage {ratio:.1%} ({covered}/{total}) below 90%."
    )


def test_scripts_module_docstring_coverage_ge_90() -> None:
    """Helper scripts under scripts/ must have module docstring coverage >= 90%."""
    ratio, covered, total = _coverage_ratio(REPO_ROOT / "scripts")
    assert ratio >= 0.90, (
        f"scripts/ module docstring coverage {ratio:.1%} ({covered}/{total}) below 90%."
    )


def test_init_files_have_docstring() -> None:
    """Every __init__.py under src/ must have a meaningful docstring."""
    init_files = sorted((REPO_ROOT / "src").rglob("__init__.py"))
    assert init_files, "expected src/ to contain at least one __init__.py"
    missing: list[pathlib.Path] = []
    for init in init_files:
        try:
            tree = ast.parse(init.read_text(encoding="utf-8"))
        except SyntaxError:
            missing.append(init)
            continue
        doc = ast.get_docstring(tree)
        if not doc or len(doc.strip()) < 20:
            missing.append(init)
    assert not missing, (
        f"these __init__.py files lack a meaningful module docstring: "
        f"{[str(p.relative_to(REPO_ROOT)) for p in missing]}"
    )


def test_module_docstrings_are_meaningful() -> None:
    """Module docstrings must be >= 40 chars after stripping (no empty placeholders)."""
    offenders: list[tuple[str, int]] = []
    for directory in (REPO_ROOT / "src", REPO_ROOT / "dags", REPO_ROOT / "scripts"):
        for path in _iter_python_files(directory):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            doc = ast.get_docstring(tree)
            if doc is not None and len(doc.strip()) < 40:
                offenders.append((str(path.relative_to(REPO_ROOT)), len(doc.strip())))
    assert not offenders, f"these module docstrings are too short to be meaningful: {offenders}"
