"""README structural invariant tests.

These tests guard the README's reviewer-facing contract at a text level:
read the file once, assert specific sections exist and internal links
resolve. The README follows the itsmekhoathekid/RecSys-MLops presentation
skeleton (business domain -> system overview -> architecture -> repository
structure -> coursework documentation -> quickstart -> status); operator
content (local setup, Docker, service URLs, validation commands, naming
convention) lives in docs/operator-runbook.md instead of this file.
"""

from __future__ import annotations

import re
from pathlib import Path

README = Path("README.md").read_text(encoding="utf-8")
LINES = README.splitlines()


def _sections() -> list[tuple[str, int]]:
    """Return [(heading, line_no), ...] for every '## ' heading."""
    out: list[tuple[str, int]] = []
    for i, line in enumerate(LINES, start=1):
        if line.startswith("## "):
            out.append((line[3:].strip(), i))
    return out


def test_opening_positioning_sentence_present() -> None:
    # The README opens with a title, then one positioning sentence before
    # any section heading — no separate '## Introduction' banner.
    body_before_first_section = README.split("\n## ", 1)[0]
    lines = [line for line in body_before_first_section.splitlines() if line.strip()]
    assert len(lines) >= 2, "README needs a title and one sentence before the first heading"
    assert lines[0].startswith("# "), "README must open with a top-level title"


def test_business_domain_subsection_present() -> None:
    # Rubric row 1: a business-domain intro paragraph.
    assert re.search(
        r"^##\s+\S*\s*Business Domain", README, flags=re.MULTILINE | re.IGNORECASE
    ), "README must have a Business Domain section"


def test_business_domain_names_platform_users_and_problem() -> None:
    # Pull the Business Domain block and assert it names the platform, the user,
    # and the problem (financial distress on Vietnamese listed companies).
    match = re.search(
        r"^##\s+\S*\s*Business Domain\s*\n+(.*?)(?:\n##\s+|\Z)",
        README,
        flags=re.DOTALL | re.IGNORECASE | re.MULTILINE,
    )
    assert match, "Business Domain section not found"
    block = match.group(1).lower().replace("-", " ")
    assert "financial distress" in block, "Business Domain must mention the problem"
    assert "vietnam" in block, "Business Domain must mention Vietnamese market scope"
    assert any(
        role in block for role in ("analyst", "ml engineer", "data engineer")
    ), "Business Domain must name at least one user role"


def test_table_of_contents_section_present() -> None:
    # Rubric row 3: ToC as a numbered list under its own section heading.
    assert re.search(
        r"^##\s+\S*\s*Table of Contents", README, flags=re.MULTILINE
    ), "README must have a 'Table of Contents' heading"


def test_toc_anchors_all_resolve() -> None:
    # Extract ToC lines, resolve each anchor slug against the headings.
    toc_match = re.search(
        r"^##\s+\S*\s*Table of Contents\s*\n+(.*?)(?:\n##\s+|\Z)",
        README,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert toc_match, "Table of Contents body not found"
    toc_body = toc_match.group(1)
    anchors = re.findall(r"\]\(#([^)]+)\)", toc_body)
    assert anchors, "ToC must contain at least one internal link"
    headings = {title.lower().replace(" ", "-"): title for title, _ in _sections()}

    # GitHub also lowercases and strips most punctuation; we mirror that loosely.
    # Emoji/variation-selector prefixes on our headings are also stripped so a
    # ToC anchor like "#-business-domain" matches a "## 🏦 Business Domain" heading.
    def slugify(title: str) -> str:
        s = title.lower()
        s = re.sub(r"[^\w\s-]", "", s)
        s = re.sub(r"\s+", "-", s.strip())
        s = re.sub(r"^-+", "", s)
        return s

    for a in anchors:
        # Strip leading punctuation/variation-selector noise an emoji prefix
        # can leave in a raw anchor (e.g. "️-architecture" from "🏗️").
        stripped = re.sub(r"^[^a-z0-9]+", "", a.lower())
        assert (
            a in headings
            or a in {slugify(t) for t in headings}
            or stripped in {slugify(t) for t in headings}
        ), f"ToC anchor #{a} does not match any heading slug"


def test_repository_structure_section_annotated() -> None:
    # Rubric row 3: an annotated repository tree.
    assert re.search(
        r"^##\s+\S*\s*Repository Structure", README, flags=re.MULTILINE
    ), "README must have a Repository Structure section"
    structure_match = re.search(
        r"^##\s+\S*\s*Repository Structure\s*\n+(.*?)(?:\n##\s+|\Z)",
        README,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert structure_match
    block = structure_match.group(1)
    assert "```" in block, "Repository Structure must be a fenced code block (tree)"
    assert "src/" in block, "Repository Structure must mention src/"


def test_coursework_documentation_section_links_to_narrative_docs() -> None:
    # The reviewer index: three coursework tables (LLM track, mini-coursework,
    # ML deferred), each naming its owning narrative-doc directory.
    assert re.search(
        r"^##\s+\S*\s*Coursework Documentation", README, flags=re.MULTILINE
    ), "README must have a 'Coursework Documentation' section"
    match = re.search(
        r"^##\s+\S*\s*Coursework Documentation\s*\n+(.*?)(?:\n##\s+|\Z)",
        README,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert match, "Coursework Documentation body not found"
    body = match.group(1)
    for required in (
        "rubric-final-coursework-(final-llm)",
        "rubric-(mini-coursework)",
        "ml-track-deferred.md",
    ):
        assert required in body, f"Coursework Documentation section must reference {required}"


def test_architecture_section_calls_out_deployable_units() -> None:
    # Rubric row 5: each diagram node is a deployable unit. The README prose
    # around the diagram must make that convention explicit.
    match = re.search(
        r"^##\s+\S*\s*Architecture\s*\n+(.*?)(?:\n##\s+|\Z)",
        README,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert match, "Architecture section not found"
    block = match.group(1).lower()
    assert (
        "deployable unit" in block
    ), "Architecture section must state each component is a deployable unit"
    for component in ("airflow", "kafka", "spark", "minio", "postgresql", "flink"):
        assert (
            component in block
        ), f"Architecture section must mention {component} as a deployable unit"


def test_no_broken_internal_markdown_image_link() -> None:
    # The architecture image must be referenced by a path that exists on disk.
    img_match = re.search(r"!\[[^\]]*\]\((images/[^)]+)\)", README)
    assert img_match, "README must embed at least one images/... image"
    rel = img_match.group(1)
    assert Path(rel).is_file(), f"Referenced image {rel} not present on disk"


def test_operator_content_lives_outside_readme() -> None:
    # Local setup / Docker / service URLs / validation commands / naming
    # convention moved to docs/operator-runbook.md so the README stays
    # reviewer-facing; the README links to it instead of inlining it.
    assert "docs/operator-runbook.md" in README, "README must link to docs/operator-runbook.md"
    runbook = Path("docs/operator-runbook.md")
    assert runbook.is_file(), "docs/operator-runbook.md must exist"
    runbook_text = runbook.read_text(encoding="utf-8")
    for required_section in ("Local Setup", "Naming Convention", "Service URLs"):
        assert required_section in runbook_text, f"runbook must cover {required_section}"


def test_section_order_repository_structure_before_coursework_documentation() -> None:
    # Structural invariant: the reviewer walks Repository Structure before
    # Coursework Documentation, and Quickstart/Project Status close the file.
    order = [title for title, _ in _sections()]

    def find(substr: str) -> int:
        for i, title in enumerate(order):
            if substr.lower() in title.lower():
                return i
        raise AssertionError(f"section containing {substr!r} not found in {order}")

    repo_i = find("Repository Structure")
    coursework_i = find("Coursework Documentation")
    quickstart_i = find("Quickstart")
    status_i = find("Project Status")
    assert repo_i < coursework_i < quickstart_i < status_i, order
