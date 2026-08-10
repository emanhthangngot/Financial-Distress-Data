"""Shared parsing helpers and matrix lookup for the requirement tests.

Mirrors `_parse_evidence_fields`/`EVIDENCE_REQUIRED_KEYS` in
scripts/audit_phase2_evidence.py (duplicated, not imported, to keep these
tests import-light — the auditor script itself is not a service dependency,
but importing it pulls in argparse/subprocess wiring these 60 subprocess
invocations don't need).
"""

from __future__ import annotations

import ast
import csv
import json
import os
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
# Mirrors the auditor's --gitops-root: no baked assumption about a sibling
# checkout. PHASE2_GITOPS_ROOT overrides; unset, GITOPS_ROOT is None and every
# gitops-artifact case skips with an explicit "not checked out" reason instead
# of misreporting a missing checkout as a missing implementation artifact.
_gitops_env = os.environ.get("PHASE2_GITOPS_ROOT")
GITOPS_ROOT = Path(_gitops_env) if _gitops_env else None
MATRIX_PATH = REPO_ROOT / "docs" / "phase2" / "rubric-matrix.csv"

EVIDENCE_REQUIRED_KEYS = [
    "rubric_id",
    "execution_timestamp",
    "source_sha",
    "gitops_sha",
    "versions",
    "command",
    "expected_result",
    "actual_result",
    "redaction_status",
]


def _load_matrix() -> dict[str, dict[str, str]]:
    """rubric_id -> row, read fresh from the CSV so tests never bake stale data."""
    rows = csv.DictReader(MATRIX_PATH.read_text(encoding="utf-8").splitlines())
    return {row["rubric_id"]: row for row in rows}


MATRIX = _load_matrix()


def parse_evidence_fields(text: str) -> dict[str, str]:
    """Extract ``key: value`` metadata pairs from an evidence markdown file."""
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        match = re.match(r"^[-*]?\s*\**([a-z_]+)\**\s*:\s*(.*)$", stripped, re.IGNORECASE)
        if not match:
            continue
        key = match.group(1).strip().lower()
        if key in EVIDENCE_REQUIRED_KEYS:
            fields[key] = match.group(2).strip()
    return fields


def _substantive_text(path: Path, text: str) -> str:
    """Strip blank/comment-only lines so reserved placeholders cannot pass."""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//")) or stripped == "---":
            continue
        lines.append(stripped)
    return "\n".join(lines)


PLACEHOLDER_RE = re.compile(
    r"(?i)(?:\bTODO\b|\bplaceholder\b|not[ _-]?implemented|reserved for future)"
)


def _is_placeholder_python(node: ast.AST) -> bool:
    """Recognize bodies that reserve a symbol without implementing behavior."""
    if isinstance(node, ast.Pass):
        return True
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
        return node.value.value is Ellipsis or isinstance(node.value.value, str)
    if isinstance(node, ast.Raise):
        exc = node.exc
        return (
            isinstance(exc, ast.Name)
            and exc.id == "NotImplementedError"
            or isinstance(exc, ast.Call)
            and isinstance(exc.func, ast.Name)
            and exc.func.id == "NotImplementedError"
        )
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        value = node.value
        return isinstance(value, ast.Constant) and (
            value.value is None
            or value.value is Ellipsis
            or isinstance(value.value, str)
            and bool(PLACEHOLDER_RE.search(value.value))
        )
    return False


def _meaningful_python_body(body: list[ast.stmt]) -> list[ast.stmt]:
    return [node for node in body if not _is_placeholder_python(node)]


def _assert_nested_definitions_implemented(path: Path, definition: ast.AST) -> None:
    """A class cannot hide placeholder methods behind a substantive class body."""
    if not isinstance(definition, ast.ClassDef):
        return
    for node in ast.walk(definition):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        assert _meaningful_python_body(
            node.body
        ), f"{path}: method {definition.name}.{node.name} is a placeholder"


def _placeholder_only_yaml(value: object) -> bool:
    """Reject empty/reservation mappings while allowing real Kubernetes/config data."""
    if value in (None, "", [], {}):
        return True
    if isinstance(value, str):
        return bool(PLACEHOLDER_RE.search(value))
    if isinstance(value, list):
        return not value or all(_placeholder_only_yaml(item) for item in value)
    if isinstance(value, dict):
        if not value:
            return True
        placeholder_keys = {"placeholder", "todo", "reserved", "notimplemented"}
        normalized_keys = {re.sub(r"[^a-z]", "", str(key).casefold()) for key in value}
        return normalized_keys <= placeholder_keys or all(
            _placeholder_only_yaml(item) for item in value.values()
        )
    return False


def assert_behavioral_contract(path: Path, assertion: str) -> None:
    """Interpret the generator-owned, non-executable assertion DSL."""
    kind, separator, token = assertion.partition(":")
    assert separator and token, f"invalid behavioral_assertion: {assertion!r}"
    text = path.read_text(encoding="utf-8", errors="replace")
    substantive = _substantive_text(path, text)
    assert substantive, f"implementation artifact is only comments/whitespace: {path}"
    non_placeholder_lines = [
        line for line in substantive.splitlines() if not PLACEHOLDER_RE.search(line)
    ]
    assert (
        non_placeholder_lines
    ), f"implementation artifact contains only TODO/placeholder text: {path}"
    if kind == "python_ast_symbol":
        tree = ast.parse(text, filename=str(path))
        definitions = {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        assert token in definitions, f"{path}: behavioral symbol {token!r} not defined"
        body = definitions[token].body
        meaningful_body = _meaningful_python_body(body)
        assert meaningful_body, f"{path}: behavioral symbol {token!r} is a placeholder"
        _assert_nested_definitions_implemented(path, definitions[token])
        return
    if kind == "yaml_path":
        value = yaml.safe_load(text)
        for key in token.split("."):
            assert isinstance(value, dict) and key in value, f"{path}: YAML path {token!r} missing"
            value = value[key]
        assert not _placeholder_only_yaml(value), f"{path}: YAML path {token!r} is placeholder-only"
        if token.startswith("jobs."):
            assert isinstance(value, dict), f"{path}: workflow job {token!r} is not a mapping"
            assert value.get("runs-on"), f"{path}: workflow job {token!r} has no runs-on"
            steps = value.get("steps")
            assert isinstance(steps, list) and steps, f"{path}: workflow job {token!r} has no steps"
            assert all(
                isinstance(step, dict) and (step.get("uses") or step.get("run")) for step in steps
            ), f"{path}: workflow job {token!r} contains a non-runnable step"
        return

    normalized_text = re.sub(r"[^a-z0-9]+", "", substantive.casefold())
    normalized_token = re.sub(r"[^a-z0-9]+", "", token.casefold())
    assert normalized_token in normalized_text, f"{path}: behavioral token {token!r} not found"

    if kind == "python_ast_contains":
        tree = ast.parse(text, filename=str(path))
        behavior = [
            node
            for node in tree.body
            if not isinstance(node, (ast.Import, ast.ImportFrom))
            and not _is_placeholder_python(node)
            and not (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and not _meaningful_python_body(node.body)
            )
        ]
        assert behavior, f"Python artifact has no executable declarations/statements: {path}"
    elif kind == "notebook_code_contains":
        notebook = json.loads(text)
        meaningful_cells = []
        for cell in notebook.get("cells", []):
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", [])).strip()
            if not source or PLACEHOLDER_RE.search(source):
                continue
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            if _meaningful_python_body(tree.body):
                meaningful_cells.append(source)
        assert meaningful_cells, f"notebook has no executable non-placeholder code cell: {path}"
    elif kind == "yaml_mapping_contains":
        document = yaml.safe_load(text)
        assert isinstance(document, dict) and document, f"YAML artifact is not a mapping: {path}"
        assert not _placeholder_only_yaml(document), f"YAML artifact is placeholder-only: {path}"
        if {"apiVersion", "kind", "metadata"} <= set(document):
            substantive_keys = {"spec", "data", "stringData", "binaryData", "rules"}
            assert substantive_keys & set(
                document
            ), f"Kubernetes YAML artifact has metadata only and no substantive payload: {path}"
    elif kind != "text_contains":
        raise AssertionError(f"unsupported behavioral_assertion kind: {kind!r}")
    else:
        words = re.findall(r"[A-Za-z0-9]+", substantive)
        assert (
            len(words) >= 3 and len(substantive) >= 24
        ), f"text artifact is only a path/token skeleton: {path}"
