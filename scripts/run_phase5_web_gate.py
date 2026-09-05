#!/usr/bin/env python3
"""Run the Phase 05 Web API fixture/mock coverage gate.

The application files use hyphenated directory names, so a normal
``pytest --cov=...`` module selector cannot target them reliably. This runner
uses coverage's file include patterns explicitly, emits a terminal report, and
exits non-zero below the declared 90% line/branch gate.
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.etree import ElementTree

import pytest

from coverage import Coverage  # isort: skip

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO_ROOT
    / "plans/260809-2039-complete-platform-llm-submission/reports/phase05-web-coverage.xml"
)
TESTS = [
    "tests/platform/apps",
    "tests/platform/verification/test_equivalence_boundary.py",
    "tests/platform/verification/test_web_api_adapters.py",
]
MINIMUM_COVERAGE_RATE = 90.0


def coverage_rates(report_path: Path) -> tuple[float, float]:
    """Return separately rounded line and branch percentages from Coverage XML."""
    root = ElementTree.parse(report_path).getroot()
    try:
        line_rate = round(float(root.attrib["line-rate"]) * 100, 2)
        branch_rate = round(float(root.attrib["branch-rate"]) * 100, 2)
    except KeyError as exc:
        raise ValueError(f"coverage XML is missing {exc.args[0]!r}") from exc
    return line_rate, branch_rate


def meets_coverage_gate(line_rate: float, branch_rate: float) -> bool:
    """Keep the rubric's line and branch thresholds independently enforceable."""
    return line_rate >= MINIMUM_COVERAGE_RATE and branch_rate >= MINIMUM_COVERAGE_RATE


def main() -> int:
    collector = Coverage(
        branch=True,
        include=[
            str(REPO_ROOT / "apps/feature-mcp/app/main.py"),
            str(REPO_ROOT / "apps/drift-mcp/app/main.py"),
        ],
        data_file=str(REPORT_PATH.with_suffix(".data")),
    )
    collector.start()
    try:
        result = pytest.main([*TESTS, "-q"])
    finally:
        collector.stop()
        collector.save()
    collector.report(show_missing=True)
    collector.xml_report(outfile=str(REPORT_PATH))
    if result != pytest.ExitCode.OK:
        return int(result)
    line_rate, branch_rate = coverage_rates(REPORT_PATH)
    print(f"Phase 05 coverage: lines={line_rate:.2f}% branches={branch_rate:.2f}%")
    return 0 if meets_coverage_gate(line_rate, branch_rate) else 1


if __name__ == "__main__":
    sys.exit(main())
