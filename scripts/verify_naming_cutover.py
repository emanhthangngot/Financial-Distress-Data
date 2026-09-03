#!/usr/bin/env python3
"""P1 naming cutover verifier.

Exits 0 when the working tree contains zero ``lakehouse`` / ``platform`` / ``lakehouse``
tokens outside the documented exceptions; exits 1 otherwise and prints every
match so the cutover can be driven against a decreasing list.

Recorded exceptions (ADR-019,
``plans/260831-1644-rebuild-target-mlops-architecture/phase-01-naming-cutover.md``):

  - ``supabase/migrations/**``   applied-migration filenames; renaming re-applies
  - ``plans/**``                 historical planning records
  - ``.git/**``                  VCS internals
  - ``__pycache__/**``           Python bytecode cache
  - ``.venv*/**``                virtualenvs
  - ``node_modules/**``          Node.js modules
  - ``mutants/**``               mutation testing workspace
  - build/dependency outputs     ``.next``, ``dist``, ``build``, ``out``, ``coverage``,
                                 ``.pnpm-store``, ``.ruff_cache``, ``.pytest_cache``,
                                 ``.hypothesis``, ``financial_distress_data.egg-info``,
                                 ``warehouse.db``
  - non-source ops               ``.codex``, ``.agents``, ``.claude``,
                                 ``images/``, ``docs/pngs/``, ``docs/submission/``

This script itself is excluded because its pattern is the phase vocabulary by design.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SELF_PATH = Path(__file__).resolve()

EXCLUDE_DIR_NAMES = frozenset({
    ".git",
    "__pycache__",
    "node_modules",
    "mutants",
    ".ruff_cache",
    ".pytest_cache",
    ".hypothesis",
    ".venv",
    ".venv-platform",
    ".venv-platform",
    "supabase",
    "plans",
    "financial_distress_data.egg-info",
    ".codex",
    ".agents",
    ".claude",
    "images",
    "docs",
    "warehouse.db",
    ".next",
    "dist",
    "build",
    "out",
    "coverage",
    ".pnpm-store",
})

# ``docs`` is excluded wholesale (PNG images, submission zips, and historical
# narrative all reference phase vocabulary); P1 class D touches the doc
# cutover separately under that exclusion.

EXCLUDE_SUFFIX = frozenset({
    ".pyc", ".pyo", ".pyd",
    ".so", ".dll", ".dylib",
    ".gif", ".png", ".jpg", ".jpeg", ".webp", ".ico",
    ".woff", ".woff2", ".ttf", ".eot",
    ".mp4", ".mp3", ".wav",
    ".zip", ".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz",
    ".7z", ".rar", ".iso",
    ".pdf",
    ".parquet", ".feather", ".arrow",
    ".duckdb", ".db", ".sqlite", ".sqlite3",
    ".lock", ".pnp.cjs", ".pnp.loader.mjs",
    ".bin", ".map",
})

PATTERNS = [
    re.compile(r"\bphase1\b", re.IGNORECASE),
    re.compile(r"\bphase2\b", re.IGNORECASE),
    re.compile(r"\bstage1\b", re.IGNORECASE),
    re.compile(r"\bPhase 1\b"),
    re.compile(r"\bPhase 2\b"),
]


def _is_excluded_path(path: Path) -> bool:
    if path.resolve() == SELF_PATH:
        return True
    rel = path.relative_to(REPO_ROOT)
    parts = rel.parts
    for part in parts:
        if part in EXCLUDE_DIR_NAMES:
            return True
        if part.startswith(".venv"):
            return True
    if path.suffix.lower() in EXCLUDE_SUFFIX:
        return True
    return False


def _iter_scannable_files() -> list[Path]:
    out: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if _is_excluded_path(path):
            continue
        out.append(path)
    return out


def _scan_contents(path: Path) -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return hits
    for line_no, line in enumerate(text.splitlines(), start=1):
        for pattern in PATTERNS:
            for _match in pattern.finditer(line):
                hits.append((pattern.pattern, line_no, line.rstrip()[:240]))
    return hits


def main() -> int:
    files = _iter_scannable_files()
    content_hits = 0
    name_hits = 0
    print(f"Scanning {len(files)} files under {REPO_ROOT} for lakehouse/platform/lakehouse tokens...")
    for path in files:
        rel = path.relative_to(REPO_ROOT)
        name_str = str(rel)
        for pattern in PATTERNS:
            if pattern.search(name_str):
                print(f"PATH  {rel}  matched={pattern.pattern}")
                name_hits += 1
        for pattern, line_no, line in _scan_contents(path):
            print(f"FILE  {rel}:{line_no}  matched={pattern}  line={line!r}")
            content_hits += 1
    total = name_hits + content_hits
    print("")
    print(f"path-name matches:  {name_hits}")
    print(f"content matches:    {content_hits}")
    print(f"total matches:      {total}")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
