"""Persistence adapters for generated source-area datasets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.generator.config import GeneratorConfig
from src.generator.offline import OfflineData
from src.generator.profile import config_to_dict, logical_digest, render_profile_html


def _jsonl(rows: list[dict[str, Any]]) -> bytes:
    return (
        "\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows) + "\n"
    ).encode()


def build_source_manifest(
    config: GeneratorConfig,
    offline: OfflineData,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    datasets = {**offline.datasets(), "stream_events": events}
    return {
        "schema_version": 1,
        "run_id": config.run_id,
        "format": config.output.format,
        "datasets": {
            name: {"rows": len(rows), "sha256": logical_digest(rows)}
            for name, rows in datasets.items()
        },
    }


class LocalSourceWriter:
    """Write replayable JSONL source files atomically enough for local CI use."""

    def write(
        self,
        config: GeneratorConfig,
        offline: OfflineData,
        events: list[dict[str, Any]],
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        root = Path(config.output.root) / config.run_id
        offline_root = root / "offline"
        stream_root = root / "streaming"
        offline_root.mkdir(parents=True, exist_ok=True)
        stream_root.mkdir(parents=True, exist_ok=True)
        for name, rows in offline.datasets().items():
            (offline_root / f"{name}.jsonl").write_bytes(_jsonl(rows))
        (stream_root / "price-events.jsonl").write_bytes(_jsonl(events))
        manifest = build_source_manifest(config, offline, events)
        documents = {
            root / "effective-config.json": config_to_dict(config),
            root / "profile.json": profile,
            root / "source-manifest.json": manifest,
        }
        for path, payload in documents.items():
            path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (root / "profile.html").write_text(render_profile_html(profile), encoding="utf-8")
        return manifest


class MinioSourceWriter:
    """Publish generated Parquet source objects to a configured MinIO prefix."""

    def __init__(self, client: Any):
        self.client = client

    def write(
        self,
        config: GeneratorConfig,
        offline: OfflineData,
        events: list[dict[str, Any]],
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        from src.io.minio_writer import write_minio_dataset, write_minio_text

        prefix = f"{config.output.minio_prefix}/run_id={config.run_id}"
        for name, rows in offline.datasets().items():
            write_minio_dataset(
                self.client,
                config.output.minio_bucket,
                f"{prefix}/offline/{name}/part-00000.parquet",
                rows,
            )
        write_minio_text(
            self.client,
            config.output.minio_bucket,
            f"{prefix}/profile.json",
            json.dumps(profile, indent=2, sort_keys=True) + "\n",
            "application/json",
        )
        manifest = build_source_manifest(config, offline, events)
        documents = {
            "effective-config.json": config_to_dict(config),
            "source-manifest.json": manifest,
        }
        for name, payload in documents.items():
            write_minio_text(
                self.client,
                config.output.minio_bucket,
                f"{prefix}/{name}",
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                "application/json",
            )
        objects = list(
            self.client.list_objects(
                config.output.minio_bucket,
                prefix=prefix,
                recursive=True,
            )
        )
        return {
            "bucket": config.output.minio_bucket,
            "prefix": prefix,
            "objects": len(objects),
            "bytes": sum(item.size for item in objects),
        }
