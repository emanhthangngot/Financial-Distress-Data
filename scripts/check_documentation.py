#!/usr/bin/env python3
"""Validate reviewer documentation size, local links, and critical docstrings."""

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path

# A link destination wrapped in angle brackets (CommonMark's escape for
# spaces/parentheses in a path, e.g. `[x](<docs/a (b).md>)`) is matched by
# the `angle` group; a bare destination falls back to `bare`, which stops at
# the first `)` and therefore cannot itself contain unescaped parentheses.
LINK_PATTERN = re.compile(r"\[[^\]]*\]\((?:<(?P<angle>[^>]+)>|(?P<bare>[^)]+))\)")


def _iter_link_targets(text: str):
    for match in LINK_PATTERN.finditer(text):
        yield match.group("angle") or match.group("bare")


SOURCE_SPEC_EXCEPTIONS = {"coursework.md", "mini_coursework.md"}
DOCSTRING_ROOTS = (
    Path("src/evidence"),
    Path("src/governance"),
    Path("src/orchestration"),
)


def check_documentation(root: Path, max_lines: int) -> list[str]:
    """Return actionable documentation violations."""
    errors = []
    for path in sorted((root / "docs").rglob("*.md")):
        relative = path.relative_to(root)
        if relative.parts[:3] == ("docs", "evidence", "final"):
            continue
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > max_lines and path.name not in SOURCE_SPEC_EXCEPTIONS:
            errors.append(f"{relative}: exceeds {max_lines} lines ({line_count})")
        for target in _iter_link_targets(path.read_text(encoding="utf-8")):
            target = target.split("#", 1)[0]
            if not target or "://" in target or target.startswith("#"):
                continue
            if not (path.parent / target).resolve().exists():
                errors.append(f"{relative}: broken link {target}")
    for path in [root / "README.md"]:
        for target in _iter_link_targets(path.read_text(encoding="utf-8")):
            target = target.split("#", 1)[0]
            if target and not target.startswith("#") and "://" not in target:
                if not (path.parent / target).resolve().exists():
                    errors.append(f"README.md: broken link {target}")
    for source_root in DOCSTRING_ROOTS:
        for path in sorted((root / source_root).glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            relative = path.relative_to(root)
            if not ast.get_docstring(tree):
                errors.append(f"{relative}: missing module docstring")
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if not node.name.startswith("_") and not ast.get_docstring(node):
                        errors.append(
                            f"{relative}:{node.lineno}: missing docstring for {node.name}"
                        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-lines", type=int, default=800)
    args = parser.parse_args()
    errors = check_documentation(Path.cwd(), args.max_lines)
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
