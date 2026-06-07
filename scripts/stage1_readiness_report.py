# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audit_stage1_evidence import audit_evidence
from scripts.check_stage1_services import check_services

PROJECT_LABEL = "production-inspired local-first lakehouse foundation with runtime evidence"
QUALITY_GATE_COMMAND = (sys.executable, "scripts/run_stage1_quality_gates.py")


def _run_git(
    command: tuple[str, ...],
    *,
    cwd: Path = PROJECT_ROOT,
    default: str = "unknown",
) -> str:
    process = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    if process.returncode != 0:
        return default
    return process.stdout.strip() or default


def _git_summary(*, cwd: Path = PROJECT_ROOT) -> dict[str, str]:
    return {
        "branch": _run_git(("git", "branch", "--show-current"), cwd=cwd),
        "commit": _run_git(("git", "rev-parse", "--short", "HEAD"), cwd=cwd),
        "status": _run_git(("git", "status", "--short"), cwd=cwd, default="clean"),
    }


def _run_quality_gates(
    *,
    command: Sequence[str] = QUALITY_GATE_COMMAND,
    cwd: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    process = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    output = "\n".join(part.strip() for part in (process.stdout, process.stderr) if part.strip())
    return {
        "status": "pass" if process.returncode == 0 else "fail",
        "returncode": process.returncode,
        "command": list(command),
        "output_tail": output[-4000:],
    }


def build_readiness_report(
    evidence_dir: str | Path,
    *,
    include_services: bool = False,
    include_quality_gates: bool = False,
    cwd: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    evidence = audit_evidence(evidence_dir)
    services = check_services(cwd=cwd) if include_services else None
    quality_gates = _run_quality_gates(cwd=cwd) if include_quality_gates else None
    failed_sections = []

    if evidence["status"] != "pass":
        failed_sections.append("evidence")
    if services is not None and services["status"] != "pass":
        failed_sections.append("services")
    if quality_gates is not None and quality_gates["status"] != "pass":
        failed_sections.append("quality_gates")

    coursework_ready = not failed_sections
    return {
        "status": "pass" if coursework_ready else "fail",
        "project_label": PROJECT_LABEL,
        "coursework_ready": coursework_ready,
        "production_ready": False,
        "enterprise_ready": False,
        "failed_sections": failed_sections,
        "git": _git_summary(cwd=cwd),
        "evidence": {
            "status": evidence["status"],
            "failed_checks": evidence["failed_checks"],
            "duckdb_metrics": evidence["duckdb_metrics"],
            "kafka_topics": evidence["kafka_topics"],
            "minio_object_count": evidence["minio_object_count"],
        },
        "services": services,
        "quality_gates": quality_gates,
        "truthfulness_note": (
            "Use this report to claim Phase 1 local runtime evidence only; "
            "live ingestion, enterprise lineage, managed security, cloud deployment, "
            "and scale claims remain out of scope."
        ),
    }


def _print_text_report(report: dict[str, Any]) -> None:
    print(f"Status: {report['status']}")
    print(f"Project label: {report['project_label']}")
    print(f"Coursework ready: {report['coursework_ready']}")
    print(f"Production ready: {report['production_ready']}")
    print(f"Enterprise ready: {report['enterprise_ready']}")
    print(f"Git: {report['git']['branch']} {report['git']['commit']} ({report['git']['status']})")
    print(f"Evidence: {report['evidence']['status']}")
    print(f"DuckDB metrics: {json.dumps(report['evidence']['duckdb_metrics'], sort_keys=True)}")
    print(f"Kafka topics: {', '.join(report['evidence']['kafka_topics'])}")
    print(f"MinIO object count: {report['evidence']['minio_object_count']}")
    if report["services"] is None:
        print("Services: not checked")
    else:
        print(f"Services: {report['services']['status']}")
        for check in report["services"]["checks"]:
            print(f"  {check['status'].upper():4} {check['name']}: {check['detail']}")
    if report["quality_gates"] is None:
        print("Quality gates: not checked")
    else:
        print(
            "Quality gates: "
            f"{report['quality_gates']['status']} "
            f"(returncode={report['quality_gates']['returncode']})"
        )
    print(f"Truthfulness: {report['truthfulness_note']}")


def _write_report(report: dict[str, Any], output_path: str | Path) -> None:
    report_text = json.dumps(report, indent=2, sort_keys=True)
    Path(output_path).write_text(f"{report_text}\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Stage 1 coursework readiness report.")
    parser.add_argument("--evidence-dir", default="docs/evidence")
    parser.add_argument(
        "--include-services",
        action="store_true",
        help="Also check running Docker services. Requires docker compose services to be up.",
    )
    parser.add_argument(
        "--include-quality-gates",
        action="store_true",
        help="Also run scripts/run_stage1_quality_gates.py and include the result.",
    )
    parser.add_argument("--output", help="Write the readiness report JSON to this path.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    args = parser.parse_args()

    report = build_readiness_report(
        args.evidence_dir,
        include_services=args.include_services,
        include_quality_gates=args.include_quality_gates,
    )
    if args.output:
        _write_report(report, args.output)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_text_report(report)
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
