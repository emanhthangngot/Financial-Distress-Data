"""Phase 2 rubric items mapping — stable semantic source of truth for both tracks.

Parses the two final-coursework rubric CSVs:
  - docs/Coursework Tracking (Public) - rubic final-coursework (final - ml).csv
  - docs/Coursework Tracking (Public) - rubic final-coursework (final - llm).csv

5-column structure (A=requirement, B=sub-claim, C=deliverable-text,
D=Proof/screenshot instructions, E=Points).

Physical line numbers are unreliable (multiline cells, merged sections).
Every scored row receives a stable semantic slug ID of the form
`{ML|LLM}-{parent-context}-{unique-description}`.

Evidence_type taxonomy:
  - executed     — proof from a running system (phase-08)
  - design_only  — design exists, proof is planned
  - stretch      — optional stretch goal, not required for 100/100

Owner taxonomy (role-based):
  - ml_engineer, llm_engineer, data_engineer, platform_operator
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DOCS = REPO_ROOT / "docs"
STATUS_ORDER = ["executed", "design_only", "stretch"]

VALID_OWNERS = ("ml_engineer", "llm_engineer", "data_engineer", "platform_operator")


# -- Helpers ------------------------------------------------------------


def _slug(text: str, max_len: int = 50) -> str:
    """Turn text into a short, readable slug for semantic IDs."""
    slug = text.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    # Remove leading filler words
    slug = re.sub(r"^(co-su-dung|setup|deploy|implement)-", "", slug)
    return slug[:max_len]


def _smart_slug(text: str, max_len: int = 30) -> str:
    """Pick the first meaningful fragment: stop at newline, parenthesis, colon."""
    fragment = text.strip().split("\n")[0].strip()
    fragment = re.sub(r"\s*\(.*", "", fragment)
    fragment = re.sub(r"\s*[:,].*", "", fragment)
    fragment = fragment.strip()
    slug = fragment.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    slug = re.sub(r"^(co-su-dung|su-dung|deploy|setup|implement|build|configure)-", "", slug)
    return slug[:max_len]


def _first_line(text: str, width: int = 120) -> str:
    """First non-empty line, truncating."""
    line = text.strip().split("\n")[0].strip()
    return line[:width]


# Keyword phrase lists used by _assign_owner. Order matters: intent rules
# (ML/agent/custom-model/A-B) are evaluated before generic data-content rules
# so a row that *demonstrates* ML or agent work wins over supporting keywords
# such as "feast"/"offline store" that merely describe its data plumbing.
# Content rules still precede section-head rules so a specific deliverable
# beats a generic section header (e.g. a "Deploy to k8s with helm" sub-row
# stays with the platform operator even though its section is "Web API kéo dữ
# liệu").
_DATA_CONTENT = [
    "push stream feature",
    "materialize",
    "offline store",
    "online store",
    "feature store",
    "data generator",
    "simulate data drift",
    "generator configuration",
    "bảng label",
    "rag data pipeline",
    "data governance",
    "data drift pipeline",
    "feast",
    "chunk",
    "load test the web api",
]
_ML_CONTENT = [
    "model versioning",
    "model registry",
    "mlflow",
    "distributed training",
    "training pipeline",
    "basic understanding of ml",
    "trigger retrain",
    "jupyter notebook to demonstrate basic",
]
_AGENT_CONTENT = [
    "coordinator agent",
    "agent sử dụng mcp",
    "agent chạy trong sandbox",
    "publish agent",
    "demonstrate basic understanding of agents",
    "agent kéo dữ liệu",
    "agent drift detection",
    "agent để làm coordinator",
    "basic understanding of agents",
    "jupyter notebook để demonstrate agent",
]
_CUSTOM_MODEL_CONTENT = ["custom model", "benchmark"]
_PLATFORM_HEAD = [
    "ci/cd",
    "routing & gateway",
    "iac",
    "autoscale",
    "observability",
    "security",
    "repository design",
    "warm up",
]
_PLATFORM_CONTENT = [
    "deploy to k8s",
    "helm",
    "terraform",
    "ansible",
    "nginx",
    "vault",
    "service mesh",
    "jenkins",
    "prometheus",
    "grafana",
    "kibana",
    "jaeger",
    "kubeflow",
    "knative eventing",
    "kserve",
    "envoy",
    "llm inference platform",
    "global model config",
    "registry for agent",
    "setup authentication",
    "rate limit",
]
_DATA_HEAD = [
    "web api kéo dữ liệu",
    "web api cho real-time drift",
    "improve the data generator",
    "rag",
]


# ── Artifact mapping (P1-1) ────────────────────────────────────────────────
# Every scored row must name the *exact implementation artifact* so a reviewer
# can find it in docs/phase2/rubric-matrix.{md,csv} without inference
# (docs/phase2/requirements.md, section 4 "Rubric Contract"). Artifacts live
# under the Phase 2 implementation roots declared in requirements.md section 2:
#   src/ml/, src/drift/, src/llm/, src/agents/, apps/
ARTIFACT_ROOTS = ("src/ml/", "src/drift/", "src/llm/", "src/agents/", "apps/")

# Drift phrases are deliberately specific ("data drift", "real-time drift",
# "drift detection", "simulate data drift") so a row that merely *mentions*
# drift — e.g. an A/B monitoring dashboard — is not mis-routed.
_ARTIFACT_AGENT = _AGENT_CONTENT
_ARTIFACT_DRIFT = ["real-time drift", "data drift", "simulate data drift", "drift detection"]


def _artifact_root(
    track: str, owner: str, section: str, requirement: str, deliverables: str
) -> str:
    """Map a rubric row to its Phase 2 implementation root directory.

    Rules (first match wins), mirroring the domain taxonomy used by
    ``_assign_owner``:

      1. Agent work (MCP tools, coordinator/publisher agents, sandboxed agents,
         agent demo notebooks) -> ``src/agents/``
      2. Drift-detection work (real-time drift APIs, data-drift pipelines,
         simulated drift) -> ``src/drift/``
      3. Platform operator deployables (gateways, CI/CD, IaC, observability,
         security, k8s/helm manifests) -> ``apps/``
      4. Data engineer work feeds the track's data pipelines ->
         ``src/ml/`` (ML) or ``src/llm/`` (LLM/RAG)
      5. Track default -> ``src/ml/`` (ML) or ``src/llm/`` (LLM)
    """
    blob = " ".join([section, requirement, deliverables]).lower()
    if any(k in blob for k in _ARTIFACT_AGENT):
        return "src/agents/"
    if any(k in blob for k in _ARTIFACT_DRIFT):
        return "src/drift/"
    if owner == "platform_operator":
        return "apps/"
    if owner == "data_engineer":
        return "src/ml/" if track == "ML" else "src/llm/"
    return "src/ml/" if track == "ML" else "src/llm/"


def _assign_owner(track: str, section: str, requirement: str, deliverables: str) -> str:
    """Assign a role-based owner from the locked taxonomy.

    Rule order (first match wins):
      1. ML-engineer intent (model versioning, training, MLflow, "basic
         understanding of ML" notebooks, trigger-retrain) — must precede data
         content so an ML demonstration row that happens to read from Feast's
         offline store is owned by the ML engineer, not the data engineer
      2. LLM-agent intent (MCP tools, coordinator, registry publication,
         agent demonstration notebooks)
      3. LLM custom-model/benchmark work
      4. A/B testing → track owner (ML or LLM)
      5. data-engineer content (Feast, materialization, generator, labels)
      6. platform-operator section heads (CI/CD, gateway, IaC, autoscale,
         observability, security, repository design, warm-up)
      7. platform-operator content (helm, terraform, mesh, gateway config)
      8. data-engineer section heads (data web APIs, generator, RAG)
      9. track default (ml_engineer / llm_engineer)
    """
    head = section.split("\n")[0].lower()
    blob = " ".join([requirement.lower(), deliverables.lower()])

    if any(k in blob for k in _ML_CONTENT):
        return "ml_engineer"
    if any(k in blob for k in _AGENT_CONTENT):
        return "llm_engineer"
    if any(k in blob for k in _CUSTOM_MODEL_CONTENT):
        return "llm_engineer"
    if "a/b" in head or "a/b test" in blob or "a-b test" in blob:
        return "ml_engineer" if track == "ML" else "llm_engineer"
    if any(k in blob for k in _DATA_CONTENT):
        return "data_engineer"
    if any(k in head for k in _PLATFORM_HEAD):
        return "platform_operator"
    if any(k in blob for k in _PLATFORM_CONTENT):
        return "platform_operator"
    if any(k in head for k in _DATA_HEAD):
        return "data_engineer"
    return "ml_engineer" if track == "ML" else "llm_engineer"


def _parse_csv(csv_path: Path, track: str) -> list[dict[str, object]]:
    """Parse a rubric CSV into a flat list of scored-row dicts.

    Logic
    -----
    - The header row (idx 0) has 5 columns: A,B,C,D(Proof),E(Point).
    - A row where column E is a positive integer is a *scored row*.
    - When column A of a scored row is non-empty, it's the top-level
      item and becomes the current parent context.
    - When column A is empty, the row inherits from the current parent.
    - The deliverable text is the most specific non-empty column among
      B, C, and D.
    - The Proof column (D) carries the required evidence screenshot/text.
    - The E row with Points='Sum' (total row) is skipped.
    """
    contents = csv_path.read_text(encoding="utf-8", errors="replace")
    reader = csv.reader(io.StringIO(contents))
    all_rows = list(reader)

    current_parent: str = ""
    current_section: str = track + "-section"
    current_proof: str = ""
    out: list[dict[str, object]] = []

    for _physical_idx, raw_row in enumerate(all_rows[1:], start=1):  # skip header
        if not raw_row or all(v.strip() == "" for v in raw_row):
            continue

        cells = list(raw_row)
        while len(cells) < 5:
            cells.append("")

        a = cells[0].strip()
        b = cells[1].strip()
        c = cells[2].strip()
        d = cells[3].strip()
        e = cells[4].strip()

        # Determine points
        try:
            points = int(e)
        except (ValueError, TypeError):
            points = 0

        if not points and not a and not b and not c and not d:
            continue
        # Skip Sum row
        if d.lower() == "sum" and a == "" and b == "" and c == "":
            continue

        # Non-scored header / category row — carry forward as section
        if not points and a:
            # Skip the README instruction block (it's not a rubric section)
            if a.startswith("Viết file README.md"):
                current_parent = "README"
                continue
            current_section = a
            current_parent = a
            continue

        # Non-scored desc row (parent with no points) — update parent only
        if not points:
            if a:
                current_parent = a
            continue

        # --- Scored row ---
        # Determine the semantic parent context and primary requirement text
        if a:
            # A is non-empty: this is a new parent row
            parent = a
            current_parent = a
            current_section = a  # A acts as the section/group label
            current_proof = d if d else current_proof
            # Requirement: combine A + B
            req = a
            if b:
                req = a + " — " + b
            proof = d if d else current_proof
            deliverables = c if c else d if d else b
            # Use A as the slug context — first meaningful fragment only
            slug_parent = _smart_slug(a, 25)
        else:
            parent = current_parent
            # For sub-rows, the deliverable is in C or B or D
            req = c or b or d or parent
            proof = d if d else current_proof
            deliverables = c if c else req
            slug_parent = _smart_slug(current_parent, 25)

        # Generate semantic ID: ML/LLM + parent slug + unique delimiter
        child_src = c or b or d if not a else b or a
        slug_child = _smart_slug(child_src, 30) if child_src else "item"
        rid = f"{track}-{slug_parent}-{slug_child}" if slug_child else f"{track}-{slug_parent}"

        # Taxonomy — role-based owner from the locked ruleset
        owner = _assign_owner(track, current_section, req, deliverables)

        # Validation command (reviewer reproduces proof). `pytest` targets the
        # phase-2 test module; the matching test file is seeded per rubric row.
        test = "pytest tests/phase2 -k '" + rid + "'"

        etype: str = "design_only"

        # Exact implementation artifact: a concrete path under one of the Phase 2
        # roots so a reviewer can find the implementation without inference.
        root = _artifact_root(track, owner, current_section, req, deliverables)
        artifact_path = f"{root}{rid}"

        out.append(
            {
                "rubric_id": rid,
                "track": track,
                "section": current_section,
                "points": points,
                "requirement": req,
                "proof": proof,
                "deliverables": deliverables,
                "owner": owner,
                "test": test,
                "evidence_path": f"docs/phase2/evidence/{track.lower()}/{rid}.md",
                "evidence_type": etype,
                "acceptance_criterion": "",
                "artifact_path": artifact_path,
            }
        )

        if not a:
            # Keep parent context for the next row
            pass

    return out


# -- Build ITEMS ------------------------------------------------------------------


_ML_PATH = DOCS / "Coursework Tracking (Public) - rubic final-coursework (final - ml).csv"
_LLM_PATH = DOCS / "Coursework Tracking (Public) - rubic final-coursework (final - llm).csv"


_RAW_ML = _parse_csv(_ML_PATH, "ML")
_RAW_LLM = _parse_csv(_LLM_PATH, "LLM")


# De-duplicate semantic IDs (slugs may collide for very similar rows). Any
# field derived from the id — the validation command and the evidence path —
# must be regenerated against the final deduplicated id so `pytest -k '<rid>'`
# matches exactly one contract test.
_seen: set[str] = set()
_deduped: list[dict[str, object]] = []
for row in _RAW_ML + _RAW_LLM:
    rid = str(row["rubric_id"])
    track = str(row["track"])
    n = 1
    while rid in _seen:
        original = rid
        rid = f"{original}-{n}"
        n += 1
    _seen.add(rid)
    row["rubric_id"] = rid
    row["test"] = "pytest tests/phase2 -k '" + rid + "'"
    row["evidence_path"] = f"docs/phase2/evidence/{track.lower()}/{rid}.md"
    # Regenerate the artifact path against the final (deduplicated) id so the
    # matrix stays the exact, non-inferred implementation reference.
    row["artifact_path"] = (
        _artifact_root(
            track,
            str(row["owner"]),
            str(row["section"]),
            str(row["requirement"]),
            str(row["deliverables"]),
        )
        + rid
    )
    _deduped.append(row)


@dataclass(frozen=True)
class Phase2RubricItem:
    rubric_id: str
    track: str
    section: str
    points: int
    requirement: str
    proof: str
    deliverables: str
    owner: str
    test: str = ""
    evidence_path: str = ""
    evidence_type: str = "executed"
    acceptance_criterion: str = ""
    artifact_path: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> Phase2RubricItem:
        return cls(
            rubric_id=str(d.get("rubric_id", "")),
            track=str(d.get("track", "")),
            section=str(d.get("section", "")),
            points=int(d.get("points", 0)),  # type: ignore[arg-type]
            requirement=str(d.get("requirement", "")),
            proof=str(d.get("proof", "")),
            deliverables=str(d.get("deliverables", "")),
            owner=str(d.get("owner", "")),
            test=str(d.get("test", "")),
            evidence_path=str(d.get("evidence_path", "")),
            evidence_type=str(d.get("evidence_type", "executed")),
            acceptance_criterion=str(d.get("acceptance_criterion", "")),
            artifact_path=str(d.get("artifact_path", "")),
        )


ITEMS: tuple[Phase2RubricItem, ...] = tuple(Phase2RubricItem.from_dict(d) for d in _deduped)


# -- Public API --------------------------------------------------------------


def total_points(track: str) -> int:
    return sum(item.points for item in ITEMS if item.track == track)


def by_track() -> dict[str, list[Phase2RubricItem]]:
    out: dict[str, list[Phase2RubricItem]] = {"ML": [], "LLM": []}
    for item in ITEMS:
        out[item.track].append(item)
    return out


def by_section(track: str) -> dict[str, list[Phase2RubricItem]]:
    out: dict[str, list[Phase2RubricItem]] = {}
    for item in ITEMS:
        if item.track != track:
            continue
        out.setdefault(item.section, []).append(item)
    return out


def validate_matrix() -> tuple[list[str], bool]:
    """Return (errors, is_valid).  Checks completeness, sums, ids, etc."""
    errors: list[str] = []

    ml_total = total_points("ML")
    llm_total = total_points("LLM")
    if ml_total != 100:
        errors.append(f"ML total points = {ml_total}, expected 100")
    if llm_total != 100:
        errors.append(f"LLM total points = {llm_total}, expected 100")

    owners_seen: set[str] = set()
    for item in ITEMS:
        if not item.rubric_id:
            errors.append(f"row without rubric_id: requirement='{item.requirement[:40]}'")
            continue
        if item.points <= 0:
            errors.append(f"{item.rubric_id}: missing or zero points ({item.points})")
        if not item.requirement:
            errors.append(f"{item.rubric_id}: missing requirement text")
        if not item.proof:
            errors.append(f"{item.rubric_id}: missing Proof")
        if not item.deliverables:
            errors.append(f"{item.rubric_id}: missing Deliverables")
        if not item.owner:
            errors.append(f"{item.rubric_id}: missing owner")
        if item.owner not in VALID_OWNERS:
            errors.append(f"{item.rubric_id}: owner '{item.owner}' not a recognized role")
        owners_seen.add(item.owner)
        if not item.test:
            errors.append(f"{item.rubric_id}: missing validation command (test)")
        if not item.evidence_path:
            errors.append(f"{item.rubric_id}: missing evidence_path")
        if not item.artifact_path:
            errors.append(f"{item.rubric_id}: missing artifact_path (exact implementation)")
        elif not item.artifact_path.startswith(ARTIFACT_ROOTS):
            errors.append(
                f"{item.rubric_id}: artifact_path '{item.artifact_path}' not under "
                f"an allowed Phase 2 root {ARTIFACT_ROOTS}"
            )
        if item.evidence_type not in ("executed", "design_only", "stretch"):
            errors.append(f"{item.rubric_id}: bad evidence_type '{item.evidence_type}'")
        # Acceptance criterion is optional at this stage
        # Phase-01 per-deliverable ACs are in docs, not per-row

    # Every role must own at least one scored row (locked taxonomy)
    for role in VALID_OWNERS:
        if role not in owners_seen:
            errors.append(f"owner '{role}' owns no scored row in the rubric matrix")

    return errors, len(errors) == 0


def export_matrix_csv() -> str:
    """Export all items as a single-line-per-row CSV string."""
    header = (
        "rubric_id,track,section,points,requirement,proof,deliverables,"
        "owner,test,evidence_path,evidence_type,acceptance_criterion,artifact_path\n"
    )
    lines = []

    def _clean(value: str) -> str:
        return value.replace("\n", "; ").replace('"', '""')

    for item in sorted(ITEMS, key=lambda i: (i.track, i.rubric_id)):
        section = _clean(item.section)
        req = _clean(item.requirement)
        proof = _clean(item.proof)
        deliverables = _clean(item.deliverables)
        ac = _clean(item.acceptance_criterion)
        test = _clean(item.test)
        lines.append(
            f'{item.rubric_id},{item.track},"{section}",{item.points},'
            f'"{req}","{proof}","{deliverables}",'
            f'{item.owner},"{test}",{item.evidence_path},'
            f'{item.evidence_type},"{ac}",{item.artifact_path}'
        )
    return header + "\n".join(lines)
