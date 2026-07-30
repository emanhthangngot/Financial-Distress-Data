"""Compute reviewer-facing generator characteristics from generated rows."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from statistics import median
from typing import Any

from src.generator.config import GeneratorConfig
from src.generator.offline import OfflineData


def logical_digest(rows: Iterable[dict[str, Any]]) -> str:
    payload = "\n".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True) for row in rows
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _rate(events: list[dict[str, Any]], field: str) -> float:
    return sum(bool(event[field]) for event in events) / len(events) if events else 0.0


def build_generator_profile(
    config: GeneratorConfig,
    offline: OfflineData,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize every data characteristic required by rubric rows R04-R13."""
    base_companies = [row for row in offline.companies if not row["is_injected_duplicate"]]
    sectors = Counter(row["sector"] for row in base_companies)
    exchanges = Counter(row["exchange"] for row in base_companies)
    schemas = Counter(row["schema_version"] for row in offline.financial_statements)
    nulls = Counter(
        row["schema_version"]
        for row in offline.financial_statements
        if row["operating_cash_flow"] is None
    )
    window_counts = Counter()
    start = min(datetime.fromisoformat(row["ingest_timestamp"]) for row in events)
    for row in events:
        offset = (datetime.fromisoformat(row["ingest_timestamp"]) - start).total_seconds()
        window_counts[int(offset // config.streaming.window_seconds)] += 1
    burst_count = window_counts.get(config.streaming.burst_window, 0)
    baseline_counts = [
        count for window, count in window_counts.items() if window != config.streaming.burst_window
    ]
    baseline_median = median(baseline_counts) if baseline_counts else 0
    return {
        "schema_version": 1,
        "run_id": config.run_id,
        "seed": config.seed,
        "effective_config_digest": logical_digest([config_to_dict(config)]),
        "offline": {
            "rows_by_dataset": {name: len(rows) for name, rows in offline.datasets().items()},
            "sector_distribution": dict(sorted(sectors.items())),
            "exchange_distribution": dict(sorted(exchanges.items())),
            "dominant_sector_rate": sectors[config.offline.dominant_sector] / len(base_companies),
            "dominant_exchange_rate": exchanges[config.offline.dominant_exchange]
            / len(base_companies),
            "exact_cardinality": {
                "source_record_id": len({row["source_record_id"] for row in base_companies}),
                "high_cardinality_id": len({row["high_cardinality_id"] for row in base_companies}),
                "ticker": len({row["ticker"] for row in base_companies}),
            },
            "schema_versions": {
                str(version): {
                    "rows": count,
                    "operating_cash_flow_nulls": nulls[version],
                }
                for version, count in sorted(schemas.items())
            },
            "duplicate_rate": offline.offline_duplicate_rate,
        },
        "streaming": {
            "events": len(events),
            "window_counts": {str(key): value for key, value in sorted(window_counts.items())},
            "peak_to_baseline_ratio": burst_count / baseline_median if baseline_median else 0.0,
            "late_rate": _rate(events, "is_late"),
            "out_of_order_rate": _rate(events, "is_out_of_order"),
            "duplicate_rate": _rate(events, "is_injected_duplicate"),
            "unique_event_ids": len({event["event_id"] for event in events}),
        },
        "logical_digest": logical_digest(offline.logical_rows() + events),
        "storage": {
            "local_format": config.output.format,
            "minio_format": "parquet",
            "stream_transport": "kafka-json",
            "minio_prefix": (f"{config.output.minio_prefix}/run_id={config.run_id}"),
        },
    }


def config_to_dict(config: GeneratorConfig) -> dict[str, Any]:
    from dataclasses import asdict

    return asdict(config)


def render_profile_html(profile: dict[str, Any]) -> str:
    """Render a self-contained evidence page suitable for browser capture."""
    offline = profile["offline"]
    streaming = profile["streaming"]
    sector_rows = "".join(
        f"<tr><td>{name}</td><td>{count:,}</td></tr>"
        for name, count in offline["sector_distribution"].items()
    )
    schema_rows = "".join(
        "<tr><td>v{}</td><td>{:,}</td><td>{:,}</td></tr>".format(
            version, values["rows"], values["operating_cash_flow_nulls"]
        )
        for version, values in offline["schema_versions"].items()
    )
    windows = streaming["window_counts"]
    peak = max(windows.values()) if windows else 1
    bars = "".join(
        f'<div class="bar-row"><span>{window}</span>'
        f'<i style="width:{max(2, count / peak * 100)}%"></i>'
        f"<b>{count:,}</b></div>"
        for window, count in windows.items()
    )
    metrics = [
        ("Dominant sector", f"{offline['dominant_sector_rate']:.1%}"),
        ("Dominant exchange", f"{offline['dominant_exchange_rate']:.1%}"),
        ("Offline duplicates", f"{offline['duplicate_rate']:.2%}"),
        ("High-cardinality IDs", f"{offline['exact_cardinality']['source_record_id']:,}"),
        ("Burst ratio", f"{streaming['peak_to_baseline_ratio']:.1f}x"),
        ("Late arrivals", f"{streaming['late_rate']:.2%}"),
        ("Out-of-order", f"{streaming['out_of_order_rate']:.2%}"),
        ("Stream duplicates", f"{streaming['duplicate_rate']:.2%}"),
        ("Source storage", "MinIO Parquet"),
    ]
    metric_html = "".join(
        f'<div class="metric">{label}<b>{value}</b></div>' for label, value in metrics
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Generator Profile</title>
<style>
body{{font:15px system-ui;margin:32px;color:#17202a;background:#f7f8fa}}
main{{max-width:1100px;margin:auto}}
h1,h2{{letter-spacing:0}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
section{{background:white;border:1px solid #d8dde5;padding:20px;border-radius:6px}}
table{{width:100%;border-collapse:collapse}}
th,td{{text-align:left;padding:7px;border-bottom:1px solid #e6e9ee}}
.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
.metric{{padding:12px;background:#eef3f8;border-left:4px solid #1769aa}}
.metric b{{display:block;font-size:22px}}
.bar-row{{display:grid;grid-template-columns:32px 1fr 70px;gap:8px;align-items:center}}
.bar-row{{margin:5px 0}}
.bar-row i{{height:14px;background:#1769aa}}
</style></head><body><main><h1>Configurable Problem Generator</h1>
<p>Run <code>{profile["run_id"]}</code> · seed <code>{profile["seed"]}</code> ·
digest <code>{profile["logical_digest"][:16]}</code></p>
<div class="metrics">{metric_html}</div>
<div class="grid"><section><h2>Sector skew</h2><table>
<tr><th>Sector</th><th>Rows</th></tr>{sector_rows}</table></section>
<section><h2>Schema evolution</h2><table>
<tr><th>Version</th><th>Rows</th><th>OCF nulls</th></tr>{schema_rows}
</table></section></div>
<section><h2>Source inventory</h2><table>
<tr><th>Dataset</th><th>Rows</th><th>Runtime target</th></tr>
<tr><td>Companies</td><td>{offline["rows_by_dataset"]["companies"]:,}</td>
<td>MinIO Parquet</td></tr>
<tr><td>Financial statements</td>
<td>{offline["rows_by_dataset"]["financial_statements"]:,}</td>
<td>MinIO Parquet</td></tr>
<tr><td>Market prices</td><td>{offline["rows_by_dataset"]["market_prices_daily"]:,}</td>
<td>MinIO Parquet</td></tr>
<tr><td>Price events</td><td>{streaming["events"]:,}</td><td>Kafka JSON</td></tr>
</table></section><section><h2>Streaming windows</h2>{bars}</section>
</main></body></html>"""
