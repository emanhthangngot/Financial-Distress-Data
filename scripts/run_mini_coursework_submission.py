"""Build and validate an immutable mini-coursework evidence package."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evidence.rubric_audit import audit_rubric, render_evidence_index
from src.evidence.run_manifest import build_run_manifest


@dataclass(frozen=True)
class Proof:
    target: str
    proof_type: str
    source: str


PROOFS = (
    Proof("documents/readme.md", "document", "README.md"),
    Proof("documents/generator.md", "document", "docs/data-generator.md"),
    Proof("documents/spark.md", "document", "docs/spark-and-storage-optimization.md"),
    Proof("documents/flink.md", "document", "docs/flink-stream-processing.md"),
    Proof("documents/orchestration.md", "document", "docs/data-pipeline-orchestration.md"),
    Proof("documents/governance.md", "document", "docs/data-governance.md"),
    Proof("documents/schema.md", "document", "docs/schema-design.md"),
    Proof("documents/docker.md", "document", "docs/docker-optimization.md"),
    Proof("documents/evidence-manifest.md", "document", "docs/novel-idea-evidence-manifest.md"),
    Proof("documents/pit-leakage.md", "document", "docs/novel-idea-pit-leakage-guard.md"),
    Proof("code/documentation-check.py", "code_reference", "scripts/check_documentation.py"),
    Proof("code/spark-optimized.py", "code_reference", "src/jobs/spark_optimized_job.py"),
    Proof("code/flink-job.py", "code_reference", "flink/jobs/price_event_job.py"),
    Proof("code/airflow-dp2.py", "code_reference", "dags/build_silver_gold.py"),
    Proof("code/schema.sql", "code_reference", "sql/schema_evidence.sql"),
    Proof("code/run-manifest.py", "code_reference", "src/evidence/run_manifest.py"),
    Proof("code/pit.py", "code_reference", "src/transforms/features/pit.py"),
    Proof("config/generator.yaml", "config", "configs/generator-config.yaml"),
    Proof("config/compose.yaml", "config", "docker-compose.yml"),
    Proof("config/governance.yaml", "config", "configs/datahub/governance.yaml"),
    Proof("metrics/generator.json", "metrics", "docs/evidence/generator/runtime-validation.json"),
    Proof("metrics/spark.json", "metrics", "docs/evidence/spark/comparison.json"),
    Proof("metrics/flink.json", "metrics", "docs/evidence/flink/comparison.json"),
    Proof("metrics/docker.json", "metrics", "docs/evidence/docker/phase8-image-sizes.json"),
    Proof("metrics/novel-ideas.json", "metrics", "docs/evidence/novel/phase8-novel-ideas.json"),
    Proof("queries/generator.json", "query_output", "docs/evidence/generator/profile.json"),
    Proof("queries/flink.json", "query_output", "docs/evidence/flink/optimized-runtime.json"),
    Proof(
        "queries/postgres-index.txt",
        "query_output",
        "docs/evidence/spark/postgres-index-benchmark.txt",
    ),
    Proof("queries/airflow.json", "query_output", "docs/evidence/airflow/phase6-runtime.json"),
    Proof("queries/schema.json", "query_output", "docs/evidence/schema/phase8-schema-audit.json"),
    Proof("logs/airflow.json", "log", "docs/evidence/airflow/phase6-runtime.json"),
    Proof("logs/generator.json", "log", "docs/evidence/generator/runtime-validation.json"),
    Proof("ui/datahub.json", "ui_export", "docs/evidence/datahub/phase7-runtime.json"),
    Proof(
        "screenshots/architecture.png",
        "screenshot",
        "images/architecture/deployment-architecture.png",
    ),
    Proof("screenshots/schema.png", "screenshot", "images/schema/schema_evidence_erd.png"),
    Proof(
        "screenshots/generator.png", "screenshot", "docs/evidence/screenshots/generator-profile.png"
    ),
    Proof(
        "screenshots/spark-baseline.png",
        "screenshot",
        "docs/evidence/screenshots/spark-ui-baseline.png",
    ),
    Proof(
        "screenshots/spark-optimized.png",
        "screenshot",
        "docs/evidence/screenshots/spark-ui-optimized.png",
    ),
    Proof(
        "screenshots/flink-baseline.png",
        "screenshot",
        "docs/evidence/screenshots/flink-baseline.png",
    ),
    Proof(
        "screenshots/flink-optimized.png",
        "screenshot",
        "docs/evidence/screenshots/flink-optimized.png",
    ),
    Proof(
        "screenshots/flink-restart.png",
        "screenshot",
        "docs/evidence/screenshots/flink-restart-checkpoints.png",
    ),
    Proof(
        "screenshots/airflow-dp1.png",
        "screenshot",
        "docs/evidence/screenshots/airflow-ingest_source_to_bronze.png",
    ),
    Proof(
        "screenshots/airflow-dp2.png",
        "screenshot",
        "docs/evidence/screenshots/airflow-build_silver_gold.png",
    ),
    Proof(
        "screenshots/airflow-dp3.png",
        "screenshot",
        "docs/evidence/screenshots/airflow-build_offline_features.png",
    ),
    Proof(
        "screenshots/datahub-dp1-lineage.png",
        "screenshot",
        "docs/evidence/screenshots/datahub-dp1-lineage.png",
    ),
    Proof(
        "screenshots/datahub-dp1-quality.png",
        "screenshot",
        "docs/evidence/screenshots/datahub-dp1-quality.png",
    ),
    Proof(
        "screenshots/datahub-dp2-lineage.png",
        "screenshot",
        "docs/evidence/screenshots/datahub-dp2-lineage.png",
    ),
    Proof(
        "screenshots/datahub-dp2-quality.png",
        "screenshot",
        "docs/evidence/screenshots/datahub-dp2-quality.png",
    ),
    Proof(
        "screenshots/datahub-dp3-lineage.png",
        "screenshot",
        "docs/evidence/screenshots/datahub-dp3-lineage.png",
    ),
    Proof(
        "screenshots/datahub-dp3-quality.png",
        "screenshot",
        "docs/evidence/screenshots/datahub-dp3-quality.png",
    ),
)

P = {proof.target: proof.target for proof in PROOFS}


def _artifacts(*paths: str) -> dict[str, object]:
    return {"status": "accepted", "artifacts": list(paths)}


CRITERIA = {
    "R01": _artifacts(
        P["documents/readme.md"],
        P["code/documentation-check.py"],
        P["screenshots/architecture.png"],
    ),
    "R02": _artifacts(P["config/compose.yaml"], "logs/quality-gates.txt"),
    "R03": _artifacts(P["documents/docker.md"], P["metrics/docker.json"]),
    "R04": _artifacts(
        P["config/generator.yaml"], P["metrics/generator.json"], P["screenshots/generator.png"]
    ),
    "R05": _artifacts(
        P["config/generator.yaml"], P["metrics/generator.json"], P["queries/generator.json"]
    ),
    "R06": _artifacts(
        P["config/generator.yaml"], P["metrics/generator.json"], P["screenshots/generator.png"]
    ),
    "R07": _artifacts(
        P["config/generator.yaml"], P["metrics/generator.json"], P["documents/generator.md"]
    ),
    "R08": _artifacts(P["config/generator.yaml"], P["logs/generator.json"]),
    "R09": _artifacts(P["metrics/generator.json"], P["screenshots/generator.png"]),
    "R10": _artifacts(
        P["config/generator.yaml"], P["metrics/generator.json"], P["screenshots/generator.png"]
    ),
    "R11": _artifacts(
        P["config/generator.yaml"], P["metrics/generator.json"], P["screenshots/generator.png"]
    ),
    "R12": _artifacts(
        P["config/generator.yaml"], P["metrics/generator.json"], P["documents/generator.md"]
    ),
    "R13": _artifacts(P["config/generator.yaml"], P["logs/generator.json"]),
    "R14": _artifacts(P["metrics/spark.json"], P["screenshots/spark-baseline.png"]),
    "R15": _artifacts(
        P["documents/spark.md"], P["metrics/spark.json"], P["screenshots/spark-optimized.png"]
    ),
    "R16": _artifacts(
        P["documents/spark.md"], P["metrics/spark.json"], P["screenshots/spark-optimized.png"]
    ),
    "R17": _artifacts(
        P["code/spark-optimized.py"], P["metrics/spark.json"], P["screenshots/spark-optimized.png"]
    ),
    "R18": _artifacts(
        P["code/spark-optimized.py"], P["metrics/spark.json"], P["screenshots/spark-optimized.png"]
    ),
    "R19": _artifacts(P["logs/airflow.json"], P["screenshots/airflow-dp2.png"]),
    "R20": _artifacts(P["metrics/flink.json"], P["screenshots/flink-baseline.png"]),
    "R21": _artifacts(P["metrics/flink.json"], P["screenshots/flink-optimized.png"]),
    "R22": _artifacts(
        P["code/flink-job.py"], P["metrics/flink.json"], P["screenshots/flink-optimized.png"]
    ),
    "R23": _artifacts(
        P["code/flink-job.py"], P["metrics/flink.json"], P["screenshots/flink-restart.png"]
    ),
    "R24": _artifacts(
        P["code/flink-job.py"], P["queries/flink.json"], P["screenshots/flink-optimized.png"]
    ),
    "R25": _artifacts(
        P["documents/spark.md"], P["metrics/spark.json"], P["queries/postgres-index.txt"]
    ),
    "R26": _artifacts(
        P["documents/spark.md"], P["metrics/spark.json"], P["queries/postgres-index.txt"]
    ),
    "R27": _artifacts(P["logs/airflow.json"], P["screenshots/airflow-dp1.png"]),
    "R28": _artifacts(
        P["logs/airflow.json"], P["queries/airflow.json"], P["screenshots/airflow-dp1.png"]
    ),
    "R29": _artifacts(P["logs/airflow.json"], P["screenshots/airflow-dp2.png"]),
    "R30": _artifacts(
        P["logs/airflow.json"], P["queries/airflow.json"], P["screenshots/airflow-dp2.png"]
    ),
    "R31": _artifacts(P["logs/airflow.json"], P["screenshots/airflow-dp3.png"]),
    "R32": _artifacts(
        P["logs/airflow.json"], P["queries/airflow.json"], P["screenshots/airflow-dp3.png"]
    ),
    "R33": _artifacts(P["ui/datahub.json"], P["screenshots/datahub-dp1-lineage.png"]),
    "R34": _artifacts(P["ui/datahub.json"], P["screenshots/datahub-dp1-quality.png"]),
    "R35": _artifacts(P["ui/datahub.json"], P["screenshots/datahub-dp2-lineage.png"]),
    "R36": _artifacts(P["ui/datahub.json"], P["screenshots/datahub-dp2-quality.png"]),
    "R37": _artifacts(P["ui/datahub.json"], P["screenshots/datahub-dp3-lineage.png"]),
    "R38": _artifacts(P["ui/datahub.json"], P["screenshots/datahub-dp3-quality.png"]),
    "R39": _artifacts(P["queries/schema.json"], P["screenshots/schema.png"]),
    "R40": _artifacts(P["queries/schema.json"], P["screenshots/schema.png"]),
    "R41": _artifacts(P["code/schema.sql"], P["screenshots/schema.png"]),
    "R42": _artifacts(P["queries/schema.json"], P["screenshots/schema.png"]),
    "R43": _artifacts(P["documents/schema.md"], P["screenshots/schema.png"]),
    "R44": _artifacts(
        P["documents/evidence-manifest.md"],
        P["code/run-manifest.py"],
        P["metrics/novel-ideas.json"],
    ),
    "R45": _artifacts(
        P["documents/pit-leakage.md"], P["code/pit.py"], P["metrics/novel-ideas.json"]
    ),
}


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or len(header) != 24:
        raise ValueError(f"invalid PNG screenshot: {path}")
    return struct.unpack(">II", header[16:24])


def _run_gate(command: list[str]) -> str:
    environment = os.environ.copy()
    environment.setdefault("UV_CACHE_DIR", "/tmp/financial-distress-uv-cache")
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    output = f"$ {' '.join(command)}\n{completed.stdout}{completed.stderr}"
    if completed.returncode:
        raise RuntimeError(f"quality gate failed ({completed.returncode}):\n{output}")
    return output


def build_package(run_id: str, output_root: Path) -> Path:
    """Copy reviewed proof, run gates, and freeze a scored evidence package."""
    package = output_root / run_id
    if package.exists():
        raise FileExistsError(f"refusing to overwrite immutable package: {package}")
    started_at = datetime.now(UTC).isoformat()
    for proof in PROOFS:
        source = ROOT / proof.source
        if not source.is_file() or source.stat().st_size == 0:
            raise FileNotFoundError(f"required proof is missing or empty: {source}")
        if proof.proof_type == "screenshot":
            width, height = _png_dimensions(source)
            if width < 800 or height < 300:
                raise ValueError(f"screenshot lacks reviewer context ({width}x{height}): {source}")

    gate_log = "\n".join(
        (
            _run_gate(["docker", "compose", "config", "--quiet"]),
            _run_gate(["uv", "run", "pytest", "-q"]),
            _run_gate(["uv", "run", "ruff", "check", "."]),
            _run_gate(["uv", "run", "ruff", "format", "--check", "."]),
        )
    )
    package.mkdir(parents=True)
    for proof in PROOFS:
        target = package / proof.target
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / proof.source, target)
    log_path = package / "logs/quality-gates.txt"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(gate_log, encoding="utf-8")

    evidence = {"schema_version": 1, "run_id": run_id, "criteria": CRITERIA}
    (package / "rubric-evidence.yaml").write_text(
        yaml.safe_dump(evidence, sort_keys=False, width=120), encoding="utf-8"
    )
    git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    artifact_specs = [(proof.target, proof.proof_type) for proof in PROOFS]
    artifact_specs.append(("logs/quality-gates.txt", "log"))
    manifest = build_run_manifest(
        evidence_dir=package,
        run_id=run_id,
        git_sha=git_sha,
        config_paths=[
            ROOT / "configs/rubric-requirements.yaml",
            ROOT / "configs/generator-config.yaml",
            ROOT / "docker-compose.yml",
        ],
        artifacts=artifact_specs,
        started_at=started_at,
        completed_at=datetime.now(UTC).isoformat(),
    )
    manifest.write(package / "run-manifest.json")
    report = audit_rubric(ROOT / "configs/rubric-requirements.yaml", package)
    if report.status != "pass" or report.earned_points != 100:
        raise RuntimeError(json.dumps(report.to_dict(), indent=2))
    (package / "audit-report.json").write_text(
        json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    (package / "evidence-index.md").write_text(
        render_evidence_index(report, evidence_dir_name="."), encoding="utf-8"
    )
    return package


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("evidence",), default="evidence")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-root", type=Path, default=Path("docs/evidence/final"))
    args = parser.parse_args()
    package = build_package(args.run_id, ROOT / args.output_root)
    print(package.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
