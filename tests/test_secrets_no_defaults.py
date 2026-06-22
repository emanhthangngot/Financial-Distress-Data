"""Sweep src/, dags/, scripts/, and sql/ for hardcoded demo credentials.

WHO: data-engineer enforcing no-default-credentials (W14, S-A/S-B).
ACTION: walk the source tree and fail on credential-default lookups
that use ``"minioadmin"`` or ``"airflow"`` as a fallback. The literals
are allowed inside ``.env.example``, in this test, in SQL/Docker
service-name lookups, and in pure comments; the test only flags
patterns that would silently mask a missing env var.
RESULT: contributors cannot reintroduce a silent default to a
credential lookup; CI fails on regression.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ("src", "dags", "scripts", "sql")
SKIP_PATH_PARTS = (".venv", "__pycache__", "docs/_plans")

ALLOWLIST_FILES = {
    Path("tests/test_secrets_no_defaults.py"),
}

# Credential names that the sweep must protect. These cover all
# MinIO/S3/Postgres/DuckDB/Spark variables the project uses today; new
# credential env vars should be added here.
PROTECTED_CREDENTIAL_NAMES = frozenset(
    {
        "MINIO_ROOT_USER",
        "MINIO_ROOT_PASSWORD",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
    }
)
PROTECTED_CREDENTIAL_LITERALS = frozenset({"minioadmin", "airflow"})

# Lines that legitimately mention a credential-like word but are NOT a
# credential-default lookup. We skip a line when it matches one of these
# narrow patterns so the sweep stays precise.
NON_CREDENTIAL_LINE_FRAGMENTS = (
    "compose exec",
    "pg_isready",
    "airflow-scheduler",
    "airflow-webserver",
    "airflow-worker",
    "airflow-triggerer",
    "minioadmin@example",  # contact address in docs/comments
    "MINIO_ROOT_USER: minioadmin",  # echoes env block in our own loader
)

# Function names whose second positional arg is treated as a credential
# default. ``os.getenv``/``os.environ.get`` arrive as ``Attribute``-named
# "getenv"/"get"; helpers like ``_config_value`` arrive as ``Name``-named.
CREDENTIAL_GET_FUNCS = frozenset(
    {
        "getenv",
        "get",
        "_config_value",
        "config_value",
        "read_env",
        "env",
        "secrets_get",
    }
)


def _iter_python_and_sql_files() -> list[Path]:
    files: list[Path] = []
    for sub in SCAN_DIRS:
        root = REPO_ROOT / sub
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in path.parts for part in SKIP_PATH_PARTS):
                continue
            if path.suffix not in {".py", ".sql"}:
                continue
            files.append(path)
    return files


def _is_allowed(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT)
    return rel in ALLOWLIST_FILES


def _literal_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _called_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _called_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _indirect_protected_name(node: ast.AST) -> str | None:
    """Recognise ``dict.get("any", "PROTECTED_NAME")``-style indirect
    credential lookups: the first arg is a free-form key, but the
    *second* arg is a protected env-var name (e.g.
    ``minio.get("access_key_env", "MINIO_ROOT_USER")``). When that
    surrounding call is itself passed as the env-var name of a
    ``getenv``/``get`` call, we know the outer call is a credential
    lookup.
    """
    if not isinstance(node, ast.Call):
        return None
    if _called_name(node.func) != "get":
        return None
    if len(node.args) < 2:
        return None
    second = _literal_str(node.args[1])
    if second in PROTECTED_CREDENTIAL_NAMES:
        return second
    return None


def _find_python_offenders(source: str) -> list[tuple[int, str]]:
    """Return ``(line, snippet)`` for any Python call/default that
    hardcodes a credential literal in a protected credential lookup.

    Detection walks the AST so we catch the default no matter how the
    source is wrapped (multi-line ``os.getenv`` calls, ``dict.get(...)
    or literal`` chains, ``_config_value("X", env, "airflow")`` helpers,
    function-signature defaults, etc.).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines()
    offenders: list[tuple[int, str]] = []

    def _record(node: ast.AST) -> None:
        value = _literal_str(node)
        if value is not None and value.strip() in PROTECTED_CREDENTIAL_LITERALS:
            offenders.append((node.lineno, lines[node.lineno - 1].strip()))

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
            func_name = _called_name(node.func)
            first_arg_name = _literal_str(node.args[0]) if node.args else None
            # Also recognise ``minio.get("access_key_env", "MINIO_ROOT_USER")``
            # style indirect lookups whose literal arg is a protected name.
            indirect_name = _indirect_protected_name(node.args[0]) if node.args else None
            resolved_first = first_arg_name or indirect_name
            if (
                resolved_first in PROTECTED_CREDENTIAL_NAMES
                and len(node.args) >= 2
                and func_name in CREDENTIAL_GET_FUNCS
            ):
                # Flag every string default the caller supplied (2nd
                # positional onward). This covers both
                # ``os.getenv("X", "minioadmin")`` and helpers like
                # ``_config_value("X", env, "airflow")``.
                for default in node.args[1:]:
                    _record(default)
            for kw in node.keywords:
                if (
                    kw.arg in {"default", "fallback"}
                    and resolved_first in PROTECTED_CREDENTIAL_NAMES
                ):
                    _record(kw.value)
            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
            self._check_signature_defaults(node.args, node.name)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
            self._check_signature_defaults(node.args, node.name)
            self.generic_visit(node)

        def visit_Lambda(self, node: ast.Lambda) -> None:  # noqa: N802
            self._check_signature_defaults(node.args, "<lambda>")
            self.generic_visit(node)

        @staticmethod
        def _check_signature_defaults(args: ast.arguments, func_name: str) -> None:
            for default in args.defaults:
                if (
                    isinstance(default, ast.Constant)
                    and isinstance(default.value, str)
                    and default.value.strip() in PROTECTED_CREDENTIAL_LITERALS
                ):
                    offenders.append(
                        (default.lineno, lines[default.lineno - 1].strip())
                    )

    Visitor().visit(tree)
    return offenders


def _find_sql_offenders(source: str) -> list[tuple[int, str]]:
    """Return ``(line, snippet)`` for any SQL ``SET s3_access_key_id='minioadmin';``."""
    lines = source.splitlines()
    offenders: list[tuple[int, str]] = []
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        if "minioadmin" not in line.lower():
            continue
        lower = line.lower()
        if "set " in lower and any(
            var in lower
            for var in (
                "s3_access_key_id",
                "s3_secret_access_key",
                "s3_region",
            )
        ):
            offenders.append((lineno, stripped))
    return offenders


def _is_skippable_line(line: str) -> bool:
    stripped = line.lstrip()
    if stripped.startswith("#") or stripped.startswith("--"):
        return True
    return any(fragment in line for fragment in NON_CREDENTIAL_LINE_FRAGMENTS)


def test_no_credential_defaults_in_source_tree():
    """No Python/SQL file under src/, dags/, scripts/, or sql/ may set a
    default credential literal in a credential-lookup call site."""
    offenders: list[tuple[str, str]] = []
    for path in _iter_python_and_sql_files():
        if _is_allowed(path):
            continue
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".py":
            for lineno, snippet in _find_python_offenders(text):
                if _is_skippable_line(snippet):
                    continue
                offenders.append((f"{path.relative_to(REPO_ROOT)}:{lineno}", snippet))
        elif path.suffix == ".sql":
            for lineno, snippet in _find_sql_offenders(text):
                offenders.append((f"{path.relative_to(REPO_ROOT)}:{lineno}", snippet))

    assert not offenders, (
        "Hardcoded credential defaults found. Set these via env vars in "
        ".env (already gitignored) and let src.security.secrets.require() "
        "raise when they are missing:\n"
        + "\n".join(f"  {p} :: {line}" for p, line in offenders)
    )
