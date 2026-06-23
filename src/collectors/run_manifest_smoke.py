"""W24 Idea 2 - manifest smoke runner.

Loads ``configs/ingestion_manifest.yaml`` via ``ManifestAdapter``,
iterates the sources, calls ``fetch()`` for a representative symbol
on each enabled source, and writes the result to
``docs/evidence/airbyte_manifest_run.json``. Disabled sources are
listed but not fetched.

The smoke run is the proof of life for the manifest: it shows the
dispatch works, the field map is honoured, and the runner is wired
into the same evidence directory as the rest of the pipeline.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from src.collectors.manifest_adapter import ManifestAdapter

DEFAULT_SYMBOL = "VCB"
SMOKE_SYMBOLS = {
    "tcbs": "VCB",
    "cafef": "VCB",
    "vnstock": "VCB",
}


def _default_manifest() -> Path:
    return Path(__file__).resolve().parents[2] / "configs" / "ingestion_manifest.yaml"


def _default_evidence() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "evidence"
        / "airbyte_manifest_run.json"
    )


def run_smoke(
    manifest_path: Path,
    evidence_path: Path,
    symbol_overrides: dict[str, str] | None = None,
) -> dict[str, object]:
    """Run the manifest smoke and return the payload that was written."""
    adapter = ManifestAdapter(manifest_path)
    sources = adapter.sources()
    overrides = dict(SMOKE_SYMBOLS)
    if symbol_overrides:
        overrides.update(symbol_overrides)

    records: list[dict[str, object]] = []
    per_source_counts: Counter[str] = Counter()
    skipped: list[dict[str, str]] = []

    for src in sources:
        source_id = src.get("source_id", "<unknown>")
        if not src.get("enabled", False):
            skipped.append({"source_id": source_id, "reason": "disabled"})
            continue
        try:
            symbol = overrides.get(source_id, DEFAULT_SYMBOL)
            record = adapter.fetch(symbol, source_id)
        except (KeyError, ValueError) as exc:
            skipped.append({"source_id": source_id, "reason": str(exc)})
            continue
        if record is None:
            skipped.append({"source_id": source_id, "reason": "fetch_returned_none"})
            continue
        record_with_source = {"_source": source_id, **record}
        records.append(record_with_source)
        per_source_counts[source_id] += 1

    payload: dict[str, object] = {
        "manifest": str(manifest_path),
        "sources": [src.get("source_id") for src in sources],
        "records": records,
        "per_source_counts": dict(sorted(per_source_counts.items())),
        "skipped": skipped,
    }

    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the W24 ingestion-manifest smoke and write the "
            "evidence JSON to docs/evidence/airbyte_manifest_run.json."
        )
    )
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--evidence", type=Path, default=None)
    args = parser.parse_args(argv)

    manifest = args.manifest or _default_manifest()
    evidence = args.evidence or _default_evidence()
    payload = run_smoke(manifest, evidence)
    print(
        f"Smoke run complete: {len(payload['records'])} records "
        f"across {len(payload['sources'])} sources; "
        f"skipped: {len(payload['skipped'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
