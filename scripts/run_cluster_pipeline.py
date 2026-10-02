"""Cluster entrypoints for Gold production and Feast batch materialization."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.collectors.fixture_config import load_fixture_config  # noqa: E402
from src.collectors.source_adapters.vnstock_adapter import (  # noqa: E402
    build_source_adapter,
)
from src.collectors.source_adapters.vnstock_fixture_adapter import (  # noqa: E402
    VnstockFixtureAdapter,
)
from src.io.paths import DEFAULT_BUCKET  # noqa: E402
from src.jobs.lakehouse_evidence_job import (  # noqa: E402
    build_evidence_payload,
    write_minio_outputs,
)
from src.metadata.metadata_writer import MetadataWriter  # noqa: E402

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


class _TickerBoundAdapter:
    """Restrict a real adapter run to an explicit, bounded ticker set."""

    def __init__(self, delegate: Any, tickers: tuple[str, ...]) -> None:
        self._delegate = delegate
        self._tickers = tickers
        self.source_name = getattr(delegate, "source_name", "source")

    def fetch_companies(self) -> list[dict[str, Any]]:
        rows = self._delegate.fetch_companies()
        by_ticker = {str(row.get("ticker", "")).upper(): row for row in rows}
        missing = [ticker for ticker in self._tickers if ticker not in by_ticker]
        if missing:
            raise RuntimeError(f"requested real tickers were not listed by source: {missing}")
        return [by_ticker[ticker] for ticker in self._tickers]

    def fetch_financial_statements(
        self, ticker: str, start_year: int, end_year: int
    ) -> list[dict[str, Any]]:
        return self._delegate.fetch_financial_statements(ticker, start_year, end_year)

    def fetch_market_prices(
        self, ticker: str, start_year: int, end_year: int
    ) -> list[dict[str, Any]]:
        return self._delegate.fetch_market_prices(ticker, start_year, end_year)


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
    os.environ.setdefault("FEAST_REDIS_HOST", "platform-redis")
    os.environ.setdefault("FEAST_REDIS_PORT", "6379")
    os.environ.setdefault(
        "FEAST_REGISTRY_PATH",
        f"s3://{os.environ.get('FINANCIAL_DISTRESS_BUCKET', DEFAULT_BUCKET)}"
        "/platform/feast/structured/registry.db",
    )


def produce_gold() -> dict[str, Any]:
    config_path = os.environ.get("LAKEHOUSE_CLUSTER_CONFIG", DEFAULT_CLUSTER_CONFIG)
    bucket = os.environ.get("FINANCIAL_DISTRESS_BUCKET", DEFAULT_BUCKET)
    source_mode = os.environ.get("CLUSTER_SOURCE_MODE", "fixture").lower()
    metadata = MetadataWriter() if source_mode in {"online", "live"} else None
    run_id = os.environ.get("CLUSTER_RUN_ID", f"cluster-{datetime.now(UTC):%Y%m%dT%H%M%SZ}")
    if metadata is not None:
        raw_tickers = os.environ.get("CLUSTER_TICKERS", "VNM")
        tickers = tuple(
            dict.fromkeys(
                ticker.strip().upper() for ticker in raw_tickers.split(",") if ticker.strip()
            )
        )
        if not tickers:
            raise ValueError("CLUSTER_TICKERS must contain at least one ticker in real mode")
        adapter = _TickerBoundAdapter(
            build_source_adapter(source_mode=source_mode, metadata_sink=metadata, run_id=run_id),
            tickers,
        )
    else:
        adapter = VnstockFixtureAdapter(config=load_fixture_config(config_path))

    payload = build_evidence_payload(
        bucket=bucket,
        adapter=adapter,
        event_anchor_ts=datetime.now(UTC).isoformat() if metadata is not None else None,
    )
    write_minio_outputs(payload, bucket)
    risk_rows = payload.datasets["gold_obt_company_quarter_risk"]
    result: dict[str, Any] = {
        "bucket": bucket,
        "source_mode": source_mode,
        "gold_rows": sum(
            count for name, count in payload.row_counts.items() if name.startswith("gold_")
        ),
        "risk_tickers": sorted({row["ticker"] for row in risk_rows}),
        "risk_rows": len(risk_rows),
    }
    if metadata is not None:
        real_periods = sorted(
            row["report_period"]
            for row in payload.datasets["bronze_financial_statements"]
            if row.get("is_synthetic") is False
        )
        synthetic_periods = sorted(
            row["report_period"]
            for row in payload.datasets["bronze_financial_statements"]
            if row.get("is_synthetic") is True
        )
        evidence_path = Path(
            os.environ.get(
                "REAL_SOURCE_EVIDENCE_PATH",
                f"docs/evidence/live/real-source-cluster-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json",
            )
        )
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "captured_at_utc": datetime.now(UTC).isoformat(),
                    "source_mode": source_mode,
                    "tickers": list(adapter._tickers),
                    "row_counts": {
                        **payload.row_counts,
                        "dq_failed_records": payload.row_counts.get("failed_records", 0),
                        "adapter_failed_records": len(metadata.failed_records),
                    },
                    "real_financial_periods": real_periods,
                    "synthetic_financial_periods": synthetic_periods,
                    "failed_records": [
                        {
                            "dataset_name": record["dataset_name"],
                            "failure_reason": record["failure_reason"],
                            "raw_payload": record["raw_payload"],
                        }
                        for record in metadata.failed_records
                    ],
                    "source_request_count": len(metadata.source_request_log),
                },
                indent=2,
                sort_keys=True,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )
        result["real_source_evidence"] = str(evidence_path)
        result["failed_record_count"] = len(metadata.failed_records)
    return result


def _utc_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _python_scalar(value: Any) -> Any:
    item = getattr(value, "item", None)
    return item() if callable(item) else value


def _is_missing_scalar(value: Any) -> bool:
    if value is None:
        return True
    import pandas as pd

    missing = pd.isna(_python_scalar(value))
    try:
        return bool(missing)
    except (TypeError, ValueError):
        return False


def _feature_values_match(expected: Any, actual: Any) -> bool:
    expected = _python_scalar(expected)
    actual = _python_scalar(actual)
    if _is_missing_scalar(expected) or _is_missing_scalar(actual):
        return _is_missing_scalar(expected) and _is_missing_scalar(actual)
    try:
        import math

        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            return math.isclose(expected, actual, rel_tol=1e-9, abs_tol=1e-12)
    except (TypeError, ValueError):
        pass
    return expected == actual


def verify_materialized_vintage(
    store: Any,
    entity: str,
    cutoff_ts: str,
    feature_view: str,
    feature_names: tuple[str, ...],
) -> tuple[dict[str, list[Any]], dict[str, str]]:
    """Compare online values and source time with the offline row at ``cutoff_ts``."""
    import pandas as pd

    cutoff = _utc_datetime(cutoff_ts)
    feature_refs = [f"{feature_view}:{name}" for name in feature_names]
    expected_frame = store.get_historical_features(
        entity_df=pd.DataFrame([{"ticker": entity, "event_timestamp": cutoff}]),
        features=feature_refs,
    ).to_df()
    if len(expected_frame.index) != 1:
        raise RuntimeError(
            f"offline vintage lookup for {entity!r} at {cutoff.isoformat()} "
            f"returned {len(expected_frame.index)} rows"
        )

    response = store.get_online_features(
        features=feature_refs,
        entity_rows=[{"ticker": entity}],
    ).to_dict(include_event_timestamps=True)
    missing = [
        name
        for name in feature_names
        if not response.get(name) or _is_missing_scalar(response[name][0])
    ]
    if missing:
        raise RuntimeError(
            f"materialized entity {entity!r} has null {feature_view} features: {missing}"
        )

    expected = expected_frame.iloc[0]
    mismatches = {
        name: {
            "offline": _python_scalar(expected[name]),
            "online": response[name][0],
        }
        for name in feature_names
        if not _feature_values_match(expected[name], response[name][0])
    }
    if mismatches:
        raise RuntimeError(
            f"materialized entity {entity!r} does not match its offline cutoff vintage: "
            f"{mismatches}"
        )

    source_timestamps = {
        response[f"{name}__ts"][0] for name in feature_names if response.get(f"{name}__ts")
    }
    if len(source_timestamps) != 1 or None in source_timestamps:
        raise RuntimeError(
            f"materialized entity {entity!r} has inconsistent source timestamps: "
            f"{sorted(str(value) for value in source_timestamps)}"
        )
    known_from_ts = datetime.fromtimestamp(source_timestamps.pop(), UTC)
    if known_from_ts > cutoff:
        raise RuntimeError(
            f"materialized entity {entity!r} selected future vintage "
            f"{known_from_ts.isoformat()} after cutoff {cutoff.isoformat()}"
        )
    return response, {
        "ticker": entity,
        "cutoff_ts": cutoff.isoformat(),
        "known_from_ts": known_from_ts.isoformat(),
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
        if callable(getattr(store, "get_historical_features", None)):
            _, source_identity = verify_materialized_vintage(
                store,
                entity,
                end,
                "company_risk_features",
                RISK_FEATURES,
            )
        else:
            # Compatibility for existing lightweight callers that provide only
            # the v1 online-store surface; real Feast stores always take the
            # value-level offline/online verification path above.
            response = store.get_online_features(
                features=[f"company_risk_features:{name}" for name in RISK_FEATURES],
                entity_rows=[{"ticker": entity}],
            ).to_dict()
            missing = [
                name
                for name in RISK_FEATURES
                if not response.get(name) or response[name][0] is None
            ]
            if missing:
                raise RuntimeError(
                    f"materialized entity {entity!r} has null risk features: {missing}"
                )
            source_identity = {}
    return {
        **result,
        "verified_entity": entity,
        "verified_features": list(RISK_FEATURES),
        "verified_source_identity": source_identity,
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
