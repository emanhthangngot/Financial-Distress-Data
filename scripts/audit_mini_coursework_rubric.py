"""Audit a correlated evidence directory against the 100-point coursework rubric."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evidence.rubric_audit import audit_rubric, render_evidence_index


def main() -> int:
    """Run the audit, optionally persist JSON and Markdown, and return gate status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", default="configs/rubric-requirements.yaml")
    parser.add_argument("--evidence-dir", default="docs/evidence")
    parser.add_argument("--output")
    parser.add_argument("--write-index")
    parser.add_argument("--index-prefix")
    parser.add_argument("--require-score", type=int)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()

    report = audit_rubric(Path(args.requirements), Path(args.evidence_dir))
    rendered = json.dumps(report.to_dict(), indent=2)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    if args.write_index:
        Path(args.write_index).write_text(
            render_evidence_index(
                report,
                evidence_dir_name=args.index_prefix or Path(args.evidence_dir).name,
            ),
            encoding="utf-8",
        )
    score_satisfied = args.require_score is None or report.earned_points >= args.require_score
    return 0 if (report.status == "pass" and score_satisfied) or args.allow_incomplete else 1


if __name__ == "__main__":
    raise SystemExit(main())
