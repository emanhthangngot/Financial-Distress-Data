#!/usr/bin/env python3
"""Generate deterministic offline/stream data and publish its measured profile."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.generator.config import load_generator_config  # noqa: E402
from src.generator.offline import generate_offline_data  # noqa: E402
from src.generator.profile import build_generator_profile  # noqa: E402
from src.generator.storage import LocalSourceWriter, MinioSourceWriter  # noqa: E402
from src.generator.streaming import generate_stream_events  # noqa: E402
from src.streaming.kafka_producer import produce_events  # noqa: E402


def _minio_client() -> Any:
    import os

    from minio import Minio

    endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    secure = endpoint.startswith("https://") or os.getenv("MINIO_SECURE", "false").lower() == "true"
    endpoint = endpoint.removeprefix("http://").removeprefix("https://")
    return Minio(
        endpoint,
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=secure,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--profile", choices=("ci", "evidence"), default="ci")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--kafka-bootstrap-servers")
    parser.add_argument("--publish-minio", action="store_true")
    parser.add_argument("--publish-kafka", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_generator_config(args.config, args.profile)
    if args.output_root:
        config = replace(config, output=replace(config.output, root=str(args.output_root)))
    if args.kafka_bootstrap_servers:
        config = replace(
            config,
            output=replace(
                config.output,
                kafka_bootstrap_servers=args.kafka_bootstrap_servers,
            ),
        )
    offline = generate_offline_data(config)
    events = generate_stream_events(config)
    profile = build_generator_profile(config, offline, events)
    manifest = LocalSourceWriter().write(config, offline, events, profile)
    runtime: dict[str, Any] = {}
    if args.publish_minio:
        runtime["minio"] = MinioSourceWriter(_minio_client()).write(
            config, offline, events, profile
        )
    if args.publish_kafka:
        runtime["kafka_events"] = produce_events(
            events, bootstrap_servers=config.output.kafka_bootstrap_servers
        )
    summary = {
        "status": "pass",
        "run_id": config.run_id,
        "profile": args.profile,
        "manifest": manifest,
        "runtime": runtime,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
