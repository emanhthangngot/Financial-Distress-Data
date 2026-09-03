"""Cluster entrypoints for Gold production and Feast batch materialization."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.collectors.fixture_config import load_fixture_config
from src.collectors.source_adapters.vnstock_fixture_adapter import VnstockFixtureAdapter
from src.io.paths import DEFAULT_BUCKET
from src.jobs.lakehouse_evidence_job import build_evidence_payload, write_minio_outputs

DEFAULT_CLUSTER_CONFIG = "configs/cluster-collector-config.yaml"
RISK_FEATURES = (
    "current_ratio",
    "debt_to_asset",
    "roa",
    "z_score",
    "distress_label",
    "distress_reason",
    "training_eligible",
)


def configure_s3_environment() -> None:
    """Map the established MinIO settings to the AWS variables Feast uses."""
    endpoint = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"http://{endpoint}"
    os.environ.setdefault("AWS_ENDPOINT_URL", endpoint)
    os.environ.setdefault("AWS_ACCESS_KEY_ID", os.environ["MINIO_ROOT_USER"])
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", os.environ["MINIO_ROOT_PASSWORD"])
    os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    os.environ.setdefault("FEAST_REDIS_HOST", "phase2-redis")
    os.environ.setdefault(
        "FEAST_REGISTRY_PATH",
        f"s3://{os.environ.get('FINANCIAL_DISTRESS_BUCKET', DEFAULT_BUCKET)}"
        "/phase2/feast/structured/registry.db",
    )


def produce_gold() -> dict[str, Any]:
    config_path = os.environ.get("PHASE1_CLUSTER_CONFIG", DEFAULT_CLUSTER_CONFIG)
    bucket = os.environ.get("FINANCIAL_DISTRESS_BUCKET", DEFAULT_BUCKET)
    adapter = VnstockFixtureAdapter(config=load_fixture_config(config_path))
    payload = build_evidence_payload(bucket=bucket, adapter=adapter)
    write_minio_outputs(payload, bucket)
    risk_rows = payload.datasets["gold_obt_company_quarter_risk"]
    return {
        "bucket": bucket,
        "gold_rows": sum(
            count for name, count in payload.row_counts.items() if name.startswith("gold_")
        ),
        "risk_tickers": sorted({row["ticker"] for row in risk_rows}),
        "risk_rows": len(risk_rows),
    }


def materialize_risk_features() -> dict[str, Any]:
    configure_s3_environment()
    from src.ml.feast.feature_definitions import build_feature_objects
    from src.ml.feast.materialization import FeastMaterializationService

    entity = os.environ.get("PLATFORM_VERIFY_TICKER", "NVL")
    start = os.environ.get("PLATFORM_MATERIALIZE_START_TS", "2020-01-01T00:00:00+00:00")
    end = os.environ.get("PLATFORM_MATERIALIZE_END_TS", datetime.now(UTC).isoformat())
    configured_repo = os.environ.get("PLATFORM_FEAST_REPO_PATH")
    with tempfile.TemporaryDirectory(prefix="fd-feast-") as temp_dir:
        repo_path = configured_repo or temp_dir
        if not configured_repo:
            cluster_config = Path("feature_repo/structured/feature_store.cluster.yaml").read_text(
                encoding="utf-8"
            )
            Path(temp_dir, "feature_store.yaml").write_text(cluster_config, encoding="utf-8")
        service = FeastMaterializationService(repo_path)
        store = service._store()
        store.apply(list(build_feature_objects().values()))
        result = service.materialize_offline_to_online("company_risk_features", start, end)
        response = store.get_online_features(
            features=[f"company_risk_features:{name}" for name in RISK_FEATURES],
            entity_rows=[{"ticker": entity}],
        ).to_dict()
    missing = [
        name for name in RISK_FEATURES if not response.get(name) or response[name][0] is None
    ]
    if missing:
        raise RuntimeError(f"materialized entity {entity!r} has null risk features: {missing}")
    return {
        **result,
        "verified_entity": entity,
        "verified_features": list(RISK_FEATURES),
    }


def produce_and_materialize() -> dict[str, Any]:
    """Refresh canonical Gold data, then publish and verify its online features."""
    return {
        "gold": produce_gold(),
        "materialization": materialize_risk_features(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("produce-gold", "materialize-risk", "produce-and-materialize"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    commands = {
        "produce-gold": produce_gold,
        "materialize-risk": materialize_risk_features,
        "produce-and-materialize": produce_and_materialize,
    }
    result = commands[args.command]()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
