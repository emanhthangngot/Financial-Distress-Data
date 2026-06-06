from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class QualityGate:
    name: str
    command: tuple[str, ...]


DEFAULT_GATES: tuple[QualityGate, ...] = (
    QualityGate("pytest", (sys.executable, "-m", "pytest", "tests")),
    QualityGate("ruff", (sys.executable, "-m", "ruff", "check", "src", "dags", "tests", "scripts")),
    QualityGate(
        "black", (sys.executable, "-m", "black", "--check", "src", "dags", "tests", "scripts")
    ),
    QualityGate("docker-compose-config", ("docker", "compose", "config")),
    QualityGate(
        "stage1-evidence-audit",
        (
            sys.executable,
            "scripts/audit_stage1_evidence.py",
            "docs/evidence",
            "--check",
        ),
    ),
)


def _selected_gates(names: set[str] | None = None) -> tuple[QualityGate, ...]:
    if not names:
        return DEFAULT_GATES
    known = {gate.name: gate for gate in DEFAULT_GATES}
    unknown = sorted(names - set(known))
    if unknown:
        raise ValueError(f"Unknown quality gate(s): {', '.join(unknown)}")
    return tuple(gate for gate in DEFAULT_GATES if gate.name in names)


def run_quality_gates(
    gates: Sequence[QualityGate],
    *,
    runner=subprocess.run,
    cwd: Path = PROJECT_ROOT,
) -> None:
    for gate in gates:
        print(f"\n==> {gate.name}: {' '.join(gate.command)}", flush=True)
        runner(gate.command, cwd=cwd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Stage 1 local quality gates.")
    parser.add_argument(
        "--only",
        action="append",
        choices=[gate.name for gate in DEFAULT_GATES],
        help="Run only the selected gate. Can be passed multiple times.",
    )
    args = parser.parse_args()

    gates = _selected_gates(set(args.only or []))
    try:
        run_quality_gates(gates)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
