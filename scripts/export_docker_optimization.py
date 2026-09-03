#!/usr/bin/env python3
"""Export reproducible Docker image size comparison evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def image_size_bytes(image: str) -> int:
    """Read an image's content size from Docker without parsing human units."""
    completed = subprocess.run(
        ["docker", "image", "inspect", image, "--format", "{{.Size}}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(completed.stdout.strip())


def comparison(baseline_bytes: int, optimized_bytes: int) -> dict[str, object]:
    """Build a size report and reject comparisons without an improvement."""
    saved = baseline_bytes - optimized_bytes
    return {
        "schema_version": 1,
        "status": "pass" if saved > 0 else "fail",
        "baseline_bytes": baseline_bytes,
        "optimized_bytes": optimized_bytes,
        "saved_bytes": saved,
        "reduction_percent": round(saved / baseline_bytes * 100, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default="financial-distress-airflow:baseline")
    parser.add_argument("--optimized", default="financial-distress-airflow:lakehouse")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/evidence/docker/phase8-image-sizes.json"),
    )
    args = parser.parse_args()
    report = comparison(image_size_bytes(args.baseline), image_size_bytes(args.optimized))
    report["baseline_image"] = args.baseline
    report["optimized_image"] = args.optimized
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
