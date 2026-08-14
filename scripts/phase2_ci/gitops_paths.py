"""Safe GitOps path resolution and digest-bump patch construction."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

IMAGE_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class GitOpsPathError(ValueError):
    """Raised for unsafe or missing GitOps paths."""


def resolve_gitops_path(root: Path | str, relative_path: str, *, must_exist: bool = True) -> Path:
    """Resolve a relative path while preventing traversal outside ``root``."""

    if not relative_path or Path(relative_path).is_absolute():
        raise GitOpsPathError(f"GitOps path must be relative: {relative_path!r}")
    root_path = Path(root).resolve()
    candidate = (root_path / relative_path).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError as exc:
        raise GitOpsPathError(f"GitOps path escapes checkout: {relative_path}") from exc
    if must_exist and not candidate.is_file():
        raise GitOpsPathError(f"GitOps path does not exist: {relative_path}")
    return candidate


def validate_gitops_paths(entries: Iterable[object], root: Path | str) -> None:
    """Ensure every catalog chart and values path exists under a checkout."""

    for entry in entries:
        name = getattr(entry, "name", "<unknown>")
        for field in ("gitops_chart", "gitops_values_path"):
            relative = getattr(entry, field, None)
            if not isinstance(relative, str) or not relative.strip():
                raise GitOpsPathError(f"{name}.{field} must be a non-empty relative path")
            try:
                resolve_gitops_path(root, relative)
            except GitOpsPathError as exc:
                raise GitOpsPathError(f"{name}.{field}: {exc}") from exc


def validate_digest(digest: str) -> str:
    """Validate and normalize a sha256 digest string."""

    value = digest.strip()
    if not IMAGE_DIGEST_RE.fullmatch(value):
        raise GitOpsPathError("image digest must match sha256:<64 lowercase hex characters>")
    return value


@dataclass(frozen=True)
class DigestBump:
    path: Path
    before: str
    after: str


def build_digest_bump_patch(
    text: str,
    *,
    repository: str,
    digest: str,
    target_type: str = "values",
    target_kind: str = "",
    target_selector: str = "",
) -> str:
    """Return text with one image reference replaced by an immutable digest."""

    if not repository or any(char.isspace() for char in repository) or "@" in repository:
        raise GitOpsPathError(
            "image repository must be a non-empty reference without whitespace or @"
        )
    digest = validate_digest(digest)
    image = f"{repository}@{digest}"
    if target_type == "values":
        repository_pattern = r"(?m)^(\s*repository:\s*).*$"
        digest_pattern = r"(?m)^(\s*digest:\s*).*$"
        repo_matches = len(re.findall(repository_pattern, text))
        digest_matches = len(re.findall(digest_pattern, text))
        if repo_matches != 1 or digest_matches != 1:
            raise GitOpsPathError(
                "values target must contain exactly one image.repository and one "
                f"image.digest (found {repo_matches} repository line(s), "
                f"{digest_matches} digest line(s))"
            )
        updated = re.sub(repository_pattern, rf"\g<1>{repository}", text, count=1)
        updated = re.sub(digest_pattern, rf"\g<1>{digest}", updated, count=1)
        return updated
    if target_type != "manifest":
        raise GitOpsPathError(f"unsupported GitOps target type: {target_type!r}")
    if not target_kind or not target_selector:
        raise GitOpsPathError("manifest target requires target_kind and target_selector")
    documents = text.split("\n---\n")
    matches = [
        index
        for index, document in enumerate(documents)
        if re.search(rf"(?m)^kind:\s*{re.escape(target_kind)}\s*$", document)
        and re.search(
            rf"(?m)^metadata:\s*\n(?:\s+.*\n)*?\s+name:\s*{re.escape(target_selector)}\s*$",
            document,
        )
    ]
    if len(matches) != 1:
        raise GitOpsPathError(
            f"expected one {target_kind} manifest named {target_selector!r}, found {len(matches)}"
        )
    index = matches[0]
    documents[index], count = re.subn(
        r"(?m)^(\s*image:\s*).*$", rf"\g<1>{image}", documents[index], count=1
    )
    if count != 1:
        raise GitOpsPathError(f"{target_kind}/{target_selector} has no image field")
    return "\n---\n".join(documents)


def apply_digest_bump(
    path: Path | str,
    *,
    repository: str,
    digest: str,
    target_type: str = "values",
    target_kind: str = "",
    target_selector: str = "",
) -> DigestBump:
    """Apply a checked digest bump and return the before/after text."""

    target = Path(path)
    before = target.read_text(encoding="utf-8")
    after = build_digest_bump_patch(
        before,
        repository=repository,
        digest=digest,
        target_type=target_type,
        target_kind=target_kind,
        target_selector=target_selector,
    )
    target.write_text(after, encoding="utf-8")
    return DigestBump(target, before, after)
