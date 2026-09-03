"""Parse and validate the platform .eployable catalog.

The module intentionally contains no CI or network code so local preflight and
unit tests exercise the same decisions as a future workflow adapter.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .gitops_paths import GitOpsPathError, validate_gitops_paths

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = REPO_ROOT / "configs" / "platform-deployables.yaml"


class CatalogError(ValueError):
    """Raised when the catalog violates its schema or path contracts."""


@dataclass(frozen=True)
class Deployable:
    name: str
    image_context: str
    dockerfile: str
    test_selector: str
    lint_paths: tuple[str, ...]
    gitops_chart: str
    gitops_values_path: str
    gitops_target_type: str = "manifest"
    gitops_target_kind: str = ""
    gitops_target_selector: str = ""

    @property
    def test_args(self) -> tuple[str, ...]:
        """Return a shell-free argv representation for the test selector."""

        return tuple(shlex.split(self.test_selector))

    @classmethod
    def from_mapping(cls, value: Any, index: int) -> Deployable:
        if not isinstance(value, dict):
            raise CatalogError(f"deployables[{index}] must be a mapping")
        required = (
            "name",
            "image_context",
            "dockerfile",
            "test_selector",
            "lint_paths",
            "gitops_chart",
            "gitops_values_path",
        )
        missing = [key for key in required if key not in value]
        if missing:
            raise CatalogError(f"deployables[{index}] missing keys: {', '.join(missing)}")
        scalar_required = (
            "name",
            "image_context",
            "dockerfile",
            "test_selector",
            "gitops_chart",
            "gitops_values_path",
        )
        if not all(isinstance(value[key], str) and value[key].strip() for key in scalar_required):
            raise CatalogError(f"deployables[{index}] has an empty or non-string required value")
        lint_paths = value["lint_paths"]
        if isinstance(lint_paths, str):
            lint_paths = shlex.split(lint_paths)
        if (
            not isinstance(lint_paths, list)
            or not lint_paths
            or not all(isinstance(path, str) and path.strip() for path in lint_paths)
        ):
            raise CatalogError(f"deployables[{index}].lint_paths must be a non-empty list")
        source_paths = (*lint_paths, value["dockerfile"], value["image_context"])
        if any(Path(path).is_absolute() for path in source_paths):
            raise CatalogError(f"deployables[{index}] contains an absolute source path")
        return cls(
            name=value["name"].strip(),
            image_context=value["image_context"].strip(),
            dockerfile=value["dockerfile"].strip(),
            test_selector=value["test_selector"].strip(),
            lint_paths=tuple(path.strip() for path in lint_paths),
            gitops_chart=value["gitops_chart"].strip(),
            gitops_values_path=value["gitops_values_path"].strip(),
            gitops_target_type=str(value.get("gitops_target_type", "manifest")),
            gitops_target_kind=str(value.get("gitops_target_kind", "")),
            gitops_target_selector=str(value.get("gitops_target_selector", "")),
        )


def load_catalog(path: Path | str = DEFAULT_CATALOG) -> tuple[Deployable, ...]:
    """Load a catalog and enforce schema-level invariants."""

    catalog_path = Path(path)
    try:
        payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CatalogError(f"cannot read catalog {catalog_path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise CatalogError(f"invalid YAML in {catalog_path}: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("deployables"), list):
        raise CatalogError(f"{catalog_path}: expected a deployables list")
    if payload.get("version", 1) != 1:
        raise CatalogError(
            f"{catalog_path}: unsupported catalog version {payload.get('version')!r}"
        )
    entries = tuple(
        Deployable.from_mapping(item, i) for i, item in enumerate(payload["deployables"])
    )
    names = [entry.name for entry in entries]
    if len(names) != len(set(names)):
        raise CatalogError("deployable names must be unique")
    return entries


def validate_catalog(
    catalog: tuple[Deployable, ...] | Path | str,
    *,
    source_root: Path | str = REPO_ROOT,
    gitops_root: Path | str | None = None,
) -> tuple[Deployable, ...]:
    """Validate source files and, when supplied, GitOps paths."""

    entries = load_catalog(catalog) if not isinstance(catalog, tuple) else catalog
    source = Path(source_root).resolve()
    problems: list[str] = []
    for entry in entries:
        for field in ("dockerfile", "image_context"):
            relative = getattr(entry, field)
            candidate = (source / relative).resolve()
            try:
                candidate.relative_to(source)
            except ValueError:
                problems.append(f"{entry.name}.{field} escapes source root: {relative}")
                continue
            if not candidate.exists():
                problems.append(f"{entry.name}.{field} does not exist: {relative}")
        for path in entry.lint_paths:
            candidate = (source / path).resolve()
            if not candidate.exists():
                problems.append(f"{entry.name}.lint_paths does not exist: {path}")
    if gitops_root is not None:
        try:
            validate_gitops_paths(entries, Path(gitops_root))
        except GitOpsPathError as exc:
            problems.append(str(exc))
    if problems:
        raise CatalogError("catalog validation failed:\n- " + "\n- ".join(problems))
    return entries
