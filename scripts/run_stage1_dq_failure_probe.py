# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.jobs.stage1_dq_job import build_intentional_dq_failure_checks
from src.metadata.metadata_writer import PostgresMetadataWriter, psycopg_connection_factory
from src.quality.dq_runner import CriticalDQFailure, DQRunner


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prove that Stage 1 critical DQ failures are persisted before halting."
    )
    parser.add_argument("--run-id", default="stage1-dq-failure-probe")
    parser.add_argument("--export-evidence", default="/tmp/stage1-dq-failure-probe")
    parser.add_argument(
        "--dsn",
        default=os.getenv(
            "PROJECT_METADATA_DSN",
            "postgresql://airflow:airflow@localhost:55432/financial_distress",
        ),
    )
    args = parser.parse_args()

    writer = PostgresMetadataWriter(psycopg_connection_factory(args.dsn))
    runner = DQRunner(writer)
    evidence = {
        "run_id": args.run_id,
        "expected_outcome": "critical_failure_persisted_before_halt",
        "halted": False,
        "error_message": None,
    }
    try:
        runner.run(args.run_id, build_intentional_dq_failure_checks())
    except CriticalDQFailure as exc:
        evidence["halted"] = True
        evidence["error_message"] = str(exc)
    else:
        raise RuntimeError("Intentional DQ failure probe did not halt.")

    evidence_dir = Path(args.export_evidence)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "stage1_dq_failure_probe.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Exported Stage 1 DQ failure probe evidence to {evidence_dir}")


if __name__ == "__main__":
    main()
