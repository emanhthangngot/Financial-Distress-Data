from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_RUNNING_SERVICES = frozenset(
    {
        "postgres",
        "minio",
        "kafka",
        "airflow-webserver",
        "airflow-scheduler",
    }
)
REQUIRED_KAFKA_TOPICS = frozenset(
    {
        "financial.price_events",
        "financial.news_events",
        "financial.alert_events",
    }
)


Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class ServiceCheckResult:
    name: str
    status: str
    detail: str


def _run(
    command: Sequence[str],
    *,
    runner: Runner = subprocess.run,
    cwd: Path = PROJECT_ROOT,
) -> subprocess.CompletedProcess[str]:
    return runner(command, cwd=cwd, capture_output=True, text=True, check=False)


def _output(process: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(part.strip() for part in (process.stdout, process.stderr) if part.strip())


def _check_running_services(*, runner: Runner, cwd: Path) -> ServiceCheckResult:
    process = _run(
        ("docker", "compose", "ps", "--status", "running", "--services"),
        runner=runner,
        cwd=cwd,
    )
    if process.returncode != 0:
        return ServiceCheckResult("docker-compose-running-services", "fail", _output(process))

    running = {line.strip() for line in process.stdout.splitlines() if line.strip()}
    missing = sorted(REQUIRED_RUNNING_SERVICES - running)
    if missing:
        return ServiceCheckResult(
            "docker-compose-running-services",
            "fail",
            f"Missing running service(s): {', '.join(missing)}",
        )
    return ServiceCheckResult(
        "docker-compose-running-services",
        "pass",
        f"Running service(s): {', '.join(sorted(running))}",
    )


def _check_postgres(*, runner: Runner, cwd: Path) -> ServiceCheckResult:
    process = _run(
        (
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "pg_isready",
            "-U",
            "airflow",
            "-d",
            "financial_distress",
        ),
        runner=runner,
        cwd=cwd,
    )
    status = "pass" if process.returncode == 0 else "fail"
    return ServiceCheckResult("postgres-readiness", status, _output(process))


def _check_kafka(*, runner: Runner, cwd: Path) -> ServiceCheckResult:
    process = _run(
        (
            "docker",
            "compose",
            "exec",
            "-T",
            "kafka",
            "/opt/kafka/bin/kafka-topics.sh",
            "--bootstrap-server",
            "kafka:9092",
            "--list",
        ),
        runner=runner,
        cwd=cwd,
    )
    if process.returncode != 0:
        return ServiceCheckResult("kafka-topics", "fail", _output(process))

    topics = {line.strip() for line in process.stdout.splitlines() if line.strip()}
    missing = sorted(REQUIRED_KAFKA_TOPICS - topics)
    if missing:
        return ServiceCheckResult("kafka-topics", "fail", f"Missing topic(s): {', '.join(missing)}")
    return ServiceCheckResult("kafka-topics", "pass", f"Topic(s): {', '.join(sorted(topics))}")


def _check_minio(*, runner: Runner, cwd: Path) -> ServiceCheckResult:
    process = _run(
        (
            "docker",
            "compose",
            "exec",
            "-T",
            "minio",
            "sh",
            "-c",
            "test -d /data/financial-distress-lake",
        ),
        runner=runner,
        cwd=cwd,
    )
    if process.returncode != 0:
        return ServiceCheckResult("minio-bucket", "fail", _output(process))
    return ServiceCheckResult("minio-bucket", "pass", "Bucket path exists: financial-distress-lake")


def _check_airflow(*, runner: Runner, cwd: Path) -> ServiceCheckResult:
    process = _run(
        (
            "docker",
            "compose",
            "exec",
            "-T",
            "airflow-scheduler",
            "airflow",
            "dags",
            "list-import-errors",
        ),
        runner=runner,
        cwd=cwd,
    )
    output = _output(process)
    if process.returncode != 0:
        return ServiceCheckResult("airflow-dag-imports", "fail", output)
    if "No data found" not in output:
        return ServiceCheckResult("airflow-dag-imports", "fail", output)
    return ServiceCheckResult("airflow-dag-imports", "pass", output)


def check_services(
    *,
    runner: Runner = subprocess.run,
    cwd: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    checks = [
        _check_running_services(runner=runner, cwd=cwd),
        _check_postgres(runner=runner, cwd=cwd),
        _check_kafka(runner=runner, cwd=cwd),
        _check_minio(runner=runner, cwd=cwd),
        _check_airflow(runner=runner, cwd=cwd),
    ]
    failed = [check.name for check in checks if check.status != "pass"]
    return {
        "status": "pass" if not failed else "fail",
        "failed_checks": failed,
        "checks": [check.__dict__ for check in checks],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Stage 1 local Docker service readiness.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    args = parser.parse_args()

    summary = check_services()
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        for check in summary["checks"]:
            print(f"{check['status'].upper():4} {check['name']}: {check['detail']}")
    if summary["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
