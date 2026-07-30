#!/usr/bin/env python3
"""Run positive and negative probes for the two coursework novel ideas."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evidence.run_manifest import build_run_manifest  # noqa: E402
from src.orchestration.pipeline_contracts import (  # noqa: E402
    PipelineValidationError,
    validate_feature_snapshot,
)
from src.transforms.features.pit import pit_join_features  # noqa: E402


def run_probes(run_id: str) -> dict[str, object]:
    """Return manifest-integrity and PIT-leakage probe results."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        artifact = root / "metric.json"
        artifact.write_text('{"rows": 2}\n', encoding="utf-8")
        manifest = build_run_manifest(
            evidence_dir=root,
            run_id=run_id,
            git_sha="phase8-probe",
            config_paths=[],
            artifacts=[("metric.json", "metrics")],
        )
        clean_errors = manifest.verify(root)
        artifact.write_text('{"rows": 999}\n', encoding="utf-8")
        tamper_errors = manifest.verify(root)

    joined = pit_join_features(
        [{"ticker": "AAA", "event_timestamp": "2026-01-10"}],
        [
            {"ticker": "AAA", "event_timestamp": "2026-01-09", "value": "past"},
            {"ticker": "AAA", "event_timestamp": "2026-01-11", "value": "future"},
        ],
    )
    rejected_future = False
    try:
        validate_feature_snapshot(
            [
                {
                    "ticker": "AAA",
                    "event_timestamp": "2026-01-10",
                    "feature_event_timestamp": "2026-01-11",
                    "created_ts": "2026-01-11T00:00:01+00:00",
                }
            ]
        )
    except PipelineValidationError:
        rejected_future = True

    manifest_pass = clean_errors == [] and tamper_errors == ["artifact hash mismatch: metric.json"]
    pit_pass = joined[0]["feature_value"] == "past" and rejected_future
    return {
        "schema_version": 1,
        "status": "pass" if manifest_pass and pit_pass else "fail",
        "run_id": run_id,
        "evidence_manifest": {
            "clean_verification_errors": clean_errors,
            "tamper_verification_errors": tamper_errors,
            "tamper_detected": manifest_pass,
        },
        "pit_leakage_guard": {
            "selected_feature": joined[0]["feature_value"],
            "future_candidate_excluded": joined[0]["feature_value"] != "future",
            "injected_future_snapshot_rejected": rejected_future,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/evidence/novel/phase8-novel-ideas.json"),
    )
    args = parser.parse_args()
    report = run_probes(args.run_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
