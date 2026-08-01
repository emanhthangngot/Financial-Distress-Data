"""README rubric invariant tests (W18).

These tests guard the rubric row 1-8 + 70-71 promises for README.md. They are
purely text-level: read the file once, assert specific strings or anchor
resolutions. The tests intentionally fail before the W18 README edit (the
"business domain" and "documentation" sections do not exist yet) and pass
after the editorial pass.
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


def test_introduction_section_present() -> None:
    assert "## Introduction" in README, "README must keep the '## Introduction' section"


def test_business_domain_subsection_present() -> None:
    # Rubric row 1: a business-domain intro paragraph.
    body = README.lower()
    assert (
        "## business domain" in body or "### business domain" in body
    ), "README must have a Business Domain section under Introduction"


def test_business_domain_names_platform_users_and_problem() -> None:
    # Pull the Business Domain block and assert it names the platform, the user,
    # and the problem (financial distress on Vietnamese listed companies).
    match = re.search(
        r"#{2,3}\s+Business Domain\s*\n+(.*?)(?:\n#{2,3}\s+|\Z)",
        README,
        flags=re.DOTALL | re.IGNORECASE,
    )
    assert match, "Business Domain section not found"
    block = match.group(1).lower().replace("-", " ")
    assert "financial distress" in block, "Business Domain must mention the problem"
    assert "vietnam" in block, "Business Domain must mention Vietnamese market scope"
    assert any(
        role in block for role in ("analyst", "ml engineer", "data engineer")
    ), "Business Domain must name at least one user role"


def test_table_of_contents_section_present() -> None:
    # Rubric row 3: ToC.
    assert re.search(
        r"^#\s+Table of Contents", README, flags=re.MULTILINE
    ), "README must have a top-level 'Table of Contents' heading"


def test_toc_anchors_all_resolve() -> None:
    # Extract ToC lines, resolve each anchor slug against the headings.
    toc_match = re.search(
        r"^#\s+Table of Contents\s*\n+(.*?)(?:\n##\s+|\Z)",
        README,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert toc_match, "Table of Contents body not found"
    toc_body = toc_match.group(1)
    anchors = re.findall(r"\]\(#([^)]+)\)", toc_body)
    assert anchors, "ToC must contain at least one internal link"
    headings = {title.lower().replace(" ", "-"): title for title, _ in _sections()}

    # GitHub also lowercases and strips most punctuation; we mirror that loosely.
    def slugify(title: str) -> str:
        s = title.lower()
        s = re.sub(r"[^\w\s-]", "", s)
        s = re.sub(r"\s+", "-", s.strip())
        return s

    for a in anchors:
        assert a in headings or a in {
            slugify(t) for t in headings
        }, f"ToC anchor #{a} does not match any heading slug"


def test_project_structure_section_annotated() -> None:
    # Rubric row 3: Project Structure with annotated tree.
    assert "## Project Structure" in README
    structure_match = re.search(
        r"##\s+Project Structure\s*\n+(.*?)(?:\n##\s+|\Z)",
        README,
        flags=re.DOTALL,
    )
    assert structure_match
    block = structure_match.group(1)
    assert "```" in block, "Project Structure must be a fenced code block (tree)"
    assert "src/" in block, "Project Structure must mention src/"


def test_documentation_section_links_to_required_docs() -> None:
    # Rubric row 70-71: README must link to the canonical docs.
    assert "## Documentation" in README, "README must have a '## Documentation' section"
    match = re.search(
        r"##\s+Documentation\s*\n+(.*?)(?:\n##\s+|\Z)",
        README,
        flags=re.DOTALL,
    )
    assert match, "Documentation body not found"
    body = match.group(1)
    for required in (
        "docs/01_data_generator.md",
        "docs/02_schema_design.md",
        "docs/idea.md",
        "docs/evidence/",
    ):
        assert required in body, f"Documentation section must link to {required}"


def test_architecture_section_calls_out_deployable_units() -> None:
    # Rubric row 5: each diagram node is a deployable unit. The README prose
    # around the diagram must make that convention explicit.
    match = re.search(
        r"##\s+Overall System Architecture\s*\n+(.*?)(?:\n##\s+|\Z)",
        README,
        flags=re.DOTALL,
    )
    assert match, "Overall System Architecture section not found"
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


def test_documentation_section_position_invariant() -> None:
    # Rubric row 70 expects Documentation to sit in the project overview
    # band (a peer of Project Structure), not inside the LOCAL setup band.
    # Lock the heading order: Project Structure -> Documentation -> # LOCAL.
    section_lines = [
        (title, line_no)
        for title, line_no in _sections()
        if title in {"Project Structure", "Documentation"}
    ]
    assert (
        len(section_lines) == 2
    ), f"Expected exactly Project Structure and Documentation sections, got {section_lines}"
    ps_line, doc_line = section_lines[0][1], section_lines[1][1]
    assert ps_line < doc_line, "Documentation must come after Project Structure"
    local_line = next(
        (i + 1 for i, line in enumerate(LINES) if line.strip() == "# LOCAL"),
        None,
    )
    assert local_line is not None, "README must have a # LOCAL separator"
    assert doc_line < local_line, "Documentation must come before # LOCAL"
