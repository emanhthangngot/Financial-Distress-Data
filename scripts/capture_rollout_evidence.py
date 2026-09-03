#!/usr/bin/env python3
"""Capture rollout/analysis status from a connected Kubernetes cluster.

The command is deliberately fail-closed: it never synthesizes a successful
promotion or rollback.  It records the exact CLI output and exits non-zero when
the required client or workload is unavailable.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(command: tuple[str, ...], *, timeout: int) -> dict[str, object]:
    started = dt.datetime.now(dt.UTC)
    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "command": list(command),
            "status": "error",
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "started_at": started.isoformat(),
            "finished_at": dt.datetime.now(dt.UTC).isoformat(),
        }
    return {
        "command": list(command),
        "status": "pass" if result.returncode == 0 else "fail",
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "started_at": started.isoformat(),
        "finished_at": dt.datetime.now(dt.UTC).isoformat(),
    }


def capture(
    *, rollout: str, namespace: str = "dataflow", timeout: int = 60
) -> dict[str, object]:
    """Capture status and analysis records for one rollout."""

    required = ("kubectl", "kubectl-argo-rollouts")
    missing = [tool for tool in required if shutil.which(tool) is None]
    if missing:
        raise RuntimeError("required cluster tools are missing: " + ", ".join(missing))
    commands = (
        ("kubectl-argo-rollouts", "get", "rollout", rollout, "-n", namespace),
        ("kubectl", "get", "analysisrun", "-n", namespace, "-o", "json"),
        ("kubectl", "get", "rollout", rollout, "-n", namespace, "-o", "json"),
    )
    records = [_run(command, timeout=timeout) for command in commands]
    return {
        "captured_at": dt.datetime.now(dt.UTC).isoformat(),
        "rollout": rollout,
        "namespace": namespace,
        "status": "pass" if all(item["status"] == "pass" for item in records) else "fail",
        "records": records,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rollout", required=True)
    parser.add_argument("--namespace", default="dataflow")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args(argv)
    try:
        payload = capture(rollout=args.rollout, namespace=args.namespace, timeout=args.timeout)
    except RuntimeError as exc:
        parser.exit(2, f"rollout evidence capture unavailable: {exc}\n")
    rendered = json.dumps(payload, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
