#!/usr/bin/env python3
"""Run the repeatable, checklist-driven evidence capture workflow.

This driver deliberately writes into a run-scoped directory and never edits a
canonical rubric evidence file.  A failed command is recorded in the manifest
and makes the process fail, so a partial capture cannot be mistaken for a
submission freeze.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKLIST = REPO_ROOT / "configs/evidence-checklist.yaml"


def _git_value(root: Path, *args: str) -> str | None:
    """Resolve provenance from the checkout without making capture fail on exports."""
    try:
        result = subprocess.run(
            ("git", *args), cwd=root, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = result.stdout.strip()
    return value or None


def _load_checklist(path: Path) -> dict[str, dict[str, Any]]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - depends on interpreter env
        raise RuntimeError(
            "PyYAML is required; run this command with the project environment "
            "(for example: `uv run python scripts/capture_phase2_evidence.py ...`)"
        ) from exc
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sections = payload.get("sections")
    if not isinstance(sections, dict) or not sections:
        raise ValueError(f"{path} must define a non-empty sections mapping")
    result: dict[str, dict[str, Any]] = {}
    for name, spec in sections.items():
        if not isinstance(name, str) or not isinstance(spec, dict):
            raise ValueError("section names and definitions must be mappings")
        command = spec.get("command")
        claim = spec.get("claim")
        if not isinstance(command, str) or not command.strip():
            raise ValueError(f"section {name!r} is missing command")
        if not isinstance(claim, str) or not claim.strip():
            raise ValueError(f"section {name!r} is missing claim")
        result[name] = {
            "command": command,
            "claim": claim,
            "screenshot": bool(spec.get("screenshot")),
            "screenshot_command": spec.get("screenshot_command"),
        }
    return result


def _run_section(
    name: str, spec: dict[str, Any], output_dir: Path, *, dry_run: bool
) -> dict[str, Any]:
    command = spec["command"]
    argv = shlex.split(command)
    started = dt.datetime.now(dt.UTC)
    result: subprocess.CompletedProcess[str] | None = None
    if not dry_run:
        try:
            result = subprocess.run(
                argv, cwd=REPO_ROOT, capture_output=True, text=True, check=False
            )
        except OSError as exc:
            result = subprocess.CompletedProcess(argv, 127, "", f"{type(exc).__name__}: {exc}")
    ended = dt.datetime.now(dt.UTC)
    stdout = result.stdout if result else "(dry run)\n"
    stderr = result.stderr if result else ""
    returncode = result.returncode if result else 0
    output_path = output_dir / f"{name}.log"
    output_path.write_text(stdout + ("\n[stderr]\n" + stderr if stderr else ""), encoding="utf-8")
    record = {
        "section": name,
        "claim": spec["claim"],
        "command": command,
        "argv": argv,
        "started_at": started.isoformat(),
        "finished_at": ended.isoformat(),
        "returncode": returncode,
        "status": "pass" if returncode == 0 else "fail",
        "artifact": (
            output_path.relative_to(REPO_ROOT).as_posix()
            if output_path.is_relative_to(REPO_ROOT)
            else str(output_path)
        ),
        "screenshot_declared": bool(spec.get("screenshot")),
    }
    if spec.get("screenshot"):
        screenshot_command = spec.get("screenshot_command")
        if not isinstance(screenshot_command, str) or not screenshot_command.strip():
            record["screenshot_status"] = "fail"
            record["screenshot_error"] = "screenshot declared without screenshot_command"
            record["status"] = "fail"
        elif dry_run:
            record["screenshot_status"] = "planned"
            record["screenshot_command"] = screenshot_command
        else:
            screenshot_argv = shlex.split(
                screenshot_command.format(output_dir=str(output_dir / "screenshots"))
            )
            try:
                screenshot_result = subprocess.run(
                    screenshot_argv,
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except OSError as exc:
                screenshot_result = subprocess.CompletedProcess(
                    screenshot_argv, 127, "", f"{type(exc).__name__}: {exc}"
                )
            screenshot_log = output_dir / f"{name}.screenshot.log"
            screenshot_log.write_text(
                screenshot_result.stdout
                + ("\n[stderr]\n" + screenshot_result.stderr if screenshot_result.stderr else ""),
                encoding="utf-8",
            )
            record["screenshot_status"] = "pass" if screenshot_result.returncode == 0 else "fail"
            record["screenshot_command"] = screenshot_command
            record["screenshot_log"] = str(screenshot_log)
            screenshot_root = output_dir / "screenshots"
            screenshot_files = (
                sorted(
                    path.relative_to(output_dir).as_posix()
                    for path in screenshot_root.rglob("*")
                    if path.is_file()
                )
                if screenshot_root.is_dir()
                else []
            )
            record["screenshot_artifacts"] = screenshot_files
            if screenshot_result.returncode != 0 or not screenshot_files:
                record["status"] = "fail"
                if not screenshot_files:
                    record["screenshot_error"] = "screenshot command produced no files"
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("section", nargs="?", help="Checklist section to run")
    parser.add_argument("--all", action="store_true", help="Run every checklist section")
    parser.add_argument("--checklist", type=Path, default=DEFAULT_CHECKLIST)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--gitops-root", type=Path, default=None, help="Recorded for provenance")
    parser.add_argument("--source-sha", default=None)
    parser.add_argument("--gitops-sha", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not args.all and not args.section:
        parser.error("provide a section name or --all")

    try:
        sections = _load_checklist(args.checklist.resolve())
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(2, f"capture unavailable: {exc}\n")
    selected = list(sections) if args.all else [args.section]
    unknown = [name for name in selected if name not in sections]
    if unknown:
        parser.error(f"unknown checklist section(s): {', '.join(unknown)}")

    run_id = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = (
        args.output_dir or (REPO_ROOT / "docs/phase2/evidence/captures" / run_id)
    ).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    records = [
        _run_section(name, sections[name], output_dir, dry_run=args.dry_run) for name in selected
    ]
    gitops_root = args.gitops_root.resolve() if args.gitops_root else None
    source_sha = args.source_sha or _git_value(REPO_ROOT, "rev-parse", "HEAD") or "unresolved"
    gitops_sha = (
        args.gitops_sha
        or (_git_value(gitops_root, "rev-parse", "HEAD") if gitops_root else None)
        or ("unresolved" if gitops_root else "none")
    )
    manifest = {
        "run_id": run_id,
        "source_sha": source_sha,
        "gitops_sha": gitops_sha,
        "gitops_root": str(gitops_root) if gitops_root else None,
        "checklist": str(args.checklist.resolve().relative_to(REPO_ROOT)),
        "sections": records,
        "status": "pass" if all(r["status"] == "pass" for r in records) else "fail",
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"status": manifest["status"], "manifest": str(manifest_path), "sections": len(records)}
        )
    )
    return 0 if manifest["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
