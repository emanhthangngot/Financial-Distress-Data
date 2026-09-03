#!/usr/bin/env python3
"""Run the source-repo Phase 2 preflight gates.

The GitOps checkout is optional: without ``--gitops-root`` this command remains
safe and fully offline, while supplying it delegates to that checkout's own
validator exactly once.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from ci.catalog import CatalogError, validate_catalog

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def shell_scripts(root: Path = PROJECT_ROOT) -> tuple[Path, ...]:
    """Return tracked-style shell scripts in deterministic order."""

    return tuple(sorted(path for path in root.glob("scripts/**/*.sh") if path.is_file()))


def run_platform_quality_gates(
    *,
    gitops_root: Path | None = None,
    runner=subprocess.run,
    project_root: Path = PROJECT_ROOT,
    require_real_digests: bool = False,
) -> None:
    """Run bash syntax, catalog, Phase 2 tests, and optional GitOps checks."""

    catalog = project_root / "configs" / "phase2-deployables.yaml"
    try:
        validate_catalog(catalog, source_root=project_root, gitops_root=gitops_root)
    except CatalogError as exc:
        raise RuntimeError(str(exc)) from exc

    for script in shell_scripts(project_root):
        command = ("bash", "-n", str(script.relative_to(project_root)))
        print(f"\n==> bash syntax: {' '.join(command)}", flush=True)
        runner(command, cwd=project_root, check=True)

    # The Phase 2 conftest intentionally ignores the tree when its optional
    # runtime (notably pydantic) is absent. Keep this gate useful in the shared
    # Phase 1 environment by selecting the dependency-free contract tests; a
    # fully provisioned Phase 2 environment can run the wider tree separately.
    test_command = (
        sys.executable,
        "-m",
        "pytest",
        "tests/platform/test_rubric_matrix.py",
        "tests/platform/test_artifact_path_contract.py",
        "tests/platform/test_deployable_catalog.py",
        "-m",
        "not slow",
    )
    print(f"\n==> phase2 pytest: {' '.join(test_command)}", flush=True)
    runner(test_command, cwd=project_root, check=True)

    if gitops_root is None:
        return
    validator = gitops_root / "scripts" / "validate-gitops.sh"
    if not validator.is_file():
        raise RuntimeError(f"GitOps validator not found: {validator}")
    command = ("bash", str(validator))
    print(f"\n==> GitOps validation: {' '.join(command)}", flush=True)
    environment = None
    if require_real_digests:
        environment = os.environ.copy()
        environment["GITOPS_REQUIRE_REAL_DIGESTS"] = "1"
    runner(command, cwd=gitops_root, check=True, **({"env": environment} if environment else {}))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase 2 source and optional GitOps gates.")
    parser.add_argument(
        "--gitops-root",
        type=Path,
        help="Path to the financial-distress-gitops checkout; omit for source-only gates.",
    )
    parser.add_argument(
        "--require-real-digests",
        action="store_true",
        help="Require registry-backed non-placeholder image digests in GitOps values/manifests.",
    )
    args = parser.parse_args(argv)
    try:
        run_platform_quality_gates(
            gitops_root=args.gitops_root, require_real_digests=args.require_real_digests
        )
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        if isinstance(exc, subprocess.CalledProcessError):
            return exc.returncode
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
