"""Validate correlated proof artifacts and score the mini-coursework rubric."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path

import yaml

from src.evidence.run_manifest import RunManifest


@dataclass(frozen=True)
class CriterionRequirement:
    """One scored rubric contract."""

    id: str
    title: str
    category: str
    points: int
    required_proof_types: tuple[str, ...]


@dataclass(frozen=True)
class RubricRequirements:
    """Validated rubric registry."""

    schema_version: int
    allowed_proof_types: tuple[str, ...]
    criteria: tuple[CriterionRequirement, ...]

    @property
    def total_points(self) -> int:
        """Return the maximum score represented by this registry."""
        return sum(item.points for item in self.criteria)


@dataclass(frozen=True)
class CriterionAuditResult:
    """Scoring result for one rubric criterion."""

    id: str
    title: str
    points: int
    status: str
    artifacts: list[str]
    missing_proof_types: list[str]
    errors: list[str]


@dataclass(frozen=True)
class RubricAuditReport:
    """Complete machine-readable rubric audit result."""

    status: str
    run_id: str | None
    earned_points: int
    total_points: int
    criteria: list[CriterionAuditResult]
    failed_criteria: list[str]
    errors: list[str]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable report."""
        return asdict(self)


def load_requirements(path: Path) -> RubricRequirements:
    """Load and validate the scored rubric registry."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("rubric requirements must use schema_version 1")
    allowed = tuple(data.get("allowed_proof_types", ()))
    if not allowed or len(set(allowed)) != len(allowed):
        raise ValueError("allowed_proof_types must be non-empty and unique")
    criteria: list[CriterionRequirement] = []
    seen: set[str] = set()
    for raw in data.get("criteria", ()):
        criterion_id = raw["id"]
        required = tuple(raw.get("required_proof_types", ()))
        if criterion_id in seen:
            raise ValueError(f"duplicate criterion id: {criterion_id}")
        if raw["points"] <= 0:
            raise ValueError(f"criterion points must be positive: {criterion_id}")
        unknown = set(required) - set(allowed)
        if unknown:
            raise ValueError(f"unknown proof types for {criterion_id}: {sorted(unknown)}")
        seen.add(criterion_id)
        criteria.append(
            CriterionRequirement(
                id=criterion_id,
                title=raw["title"],
                category=raw["category"],
                points=raw["points"],
                required_proof_types=required,
            )
        )
    return RubricRequirements(1, allowed, tuple(criteria))


def _failed_report(requirements: RubricRequirements, errors: list[str]) -> RubricAuditReport:
    criteria = [
        CriterionAuditResult(
            item.id, item.title, item.points, "invalid", [], list(item.required_proof_types), []
        )
        for item in requirements.criteria
    ]
    return RubricAuditReport(
        "fail",
        None,
        0,
        requirements.total_points,
        criteria,
        [item.id for item in requirements.criteria],
        errors,
    )


def audit_rubric(requirements: Path | RubricRequirements, evidence_dir: Path) -> RubricAuditReport:
    """Score only criteria backed by accepted, correlated, untampered proof."""
    registry = load_requirements(requirements) if isinstance(requirements, Path) else requirements
    manifest_path = evidence_dir / "run-manifest.json"
    evidence_path = evidence_dir / "rubric-evidence.yaml"
    missing = [str(path) for path in (manifest_path, evidence_path) if not path.is_file()]
    if missing:
        errors = [f"required evidence file missing: {path}" for path in missing]
        return _failed_report(registry, errors)

    try:
        manifest = RunManifest.read(manifest_path)
        evidence = yaml.safe_load(evidence_path.read_text(encoding="utf-8"))
    except (KeyError, TypeError, ValueError, yaml.YAMLError) as exc:
        return _failed_report(registry, [f"invalid evidence package: {exc}"])
    evidence_run_id = evidence.get("run_id") if isinstance(evidence, dict) else None
    if manifest.run_id != evidence_run_id:
        report = _failed_report(
            registry,
            [f"run_id mismatch: manifest={manifest.run_id} evidence={evidence_run_id}"],
        )
        return replace(report, run_id=manifest.run_id)
    integrity_errors = manifest.verify(evidence_dir)
    if integrity_errors:
        report = _failed_report(registry, integrity_errors)
        return replace(report, run_id=manifest.run_id)

    artifact_records = {item.path: item for item in manifest.artifacts}
    evidence_criteria = evidence.get("criteria", {})
    results: list[CriterionAuditResult] = []
    earned = 0
    failed: list[str] = []
    for requirement in registry.criteria:
        entry = evidence_criteria.get(requirement.id, {})
        artifacts = entry.get("artifacts", []) if isinstance(entry, dict) else []
        proof_types = {
            artifact_records[path].proof_type for path in artifacts if path in artifact_records
        }
        missing_proofs = sorted(set(requirement.required_proof_types) - proof_types)
        errors = [
            f"artifact is not in manifest: {path}"
            for path in artifacts
            if path not in artifact_records
        ]
        accepted = entry.get("status") == "accepted" and not missing_proofs and not errors
        status = "accepted" if accepted else (entry.get("status") or "missing")
        if accepted:
            earned += requirement.points
        else:
            failed.append(requirement.id)
        results.append(
            CriterionAuditResult(
                requirement.id,
                requirement.title,
                requirement.points,
                status,
                list(artifacts),
                missing_proofs,
                errors,
            )
        )
    return RubricAuditReport(
        "pass" if not failed else "fail",
        manifest.run_id,
        earned,
        registry.total_points,
        results,
        failed,
        [],
    )


def render_evidence_index(report: RubricAuditReport, evidence_dir_name: str = "evidence") -> str:
    """Render a reviewer-facing Markdown index from an audit report."""
    lines = [
        "# Mini-Coursework Evidence Index",
        "",
        f"Status: **{report.status.upper()}**  ",
        f"Score: **{report.earned_points}/{report.total_points}**  ",
        f"Run ID: `{report.run_id or 'unavailable'}`",
        "",
        "This index is generated by `scripts/audit_mini_coursework_rubric.py`. "
        "A criterion earns points only when its status is accepted and every required "
        "proof type is present in the verified run manifest.",
        "",
        "| ID | Criterion | Points | Status | Evidence |",
        "|---|---|---:|---|---|",
    ]
    for item in report.criteria:
        artifacts = (
            "<br>".join(f"[{path}]({evidence_dir_name}/{path})" for path in item.artifacts)
            or "Missing"
        )
        score = item.points if item.status == "accepted" else 0
        lines.append(
            f"| {item.id} | {item.title} | {score}/{item.points} | {item.status} | {artifacts} |"
        )
    if report.errors:
        lines.extend(["", "## Package Errors", "", *[f"- {error}" for error in report.errors]])
    return "\n".join(lines) + "\n"
