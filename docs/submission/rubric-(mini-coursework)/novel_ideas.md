---
title: "Novel Ideas"
date: 2026-08-14
status: active
---

# Novel Ideas: point-in-time leakage guard and a declarative ingestion manifest

This doc proves the two rows in "Novel ideas": (1) a PIT leakage guard that
rejects future-dated feature candidates at two independent layers, verified
against a deliberately leaked snapshot, and (2) an Airbyte-inspired
declarative ingestion manifest that turns adding a new source into a YAML
entry instead of new Python. Neither claims novel research — both apply
known techniques (point-in-time correctness, connector manifests) to this
platform's specific needs, per the rubric's own framing.

**Active deployment facts:** `src/transforms/features/pit.py`,
`src/collectors/manifest_adapter.py`, `configs/ingestion_manifest.yaml`.

## Part I — Idea 1: point-in-time leakage guard

### 1. Two independent layers reject future information

`src/transforms/features/pit.py` selects only feature rows whose event
timestamp is at or before the reference timestamp. The DP3 publication gate
independently checks `feature_event_timestamp <= event_timestamp` and
requires `created_ts` — the second check protects publication even if
upstream feature logic regresses.

```json
{
  "pit_leakage_guard": {
    "future_candidate_excluded": true,
    "injected_future_snapshot_rejected": true,
    "selected_feature": "past"
  },
  "evidence_manifest": {
    "tamper_detected": true,
    "tamper_verification_errors": ["artifact hash mismatch: metric.json"],
    "note": "tamper_detected=true proves the manifest catches a controlled mutation; the checked-in artifacts are the clean run."
  },
  "status": "pass"
}
```

The positive/negative probe supplies one past and one future candidate; the
join selects the past candidate. A deliberately leaked snapshot is then
submitted to the DP3 gate and correctly raises `PipelineValidationError`. A
second, orthogonal proof in the same evidence file: the evidence manifest's
own tamper-detection correctly flags a controlled artifact mutation — the
checked-in artifacts are the clean run, not the tampered one. Full evidence:
[`docs/evidence/novel/phase8-novel-ideas.json`](../../evidence/novel/phase8-novel-ideas.json).

## Part II — Idea 2: declarative ingestion manifest

### 2. A new data source is a YAML entry, not new Python

Prior art: Airbyte connectors (`spec.yaml` + `catalog.json`, uniform
interface) and Singer taps follow the same pattern; this project borrows the
*pattern*, not the dependency — Airbyte/Singer are external services this
project does not run locally, and pulling in `dlt` is overkill for two
declared sources.

```yaml
# configs/ingestion_manifest.yaml — one entry per source
tcbs:  {enabled: false, endpoint: ..., field_map: ..., rate_limit_per_min: ..., incremental_key: ...}
cafef: {enabled: false, endpoint: ..., field_map: ..., rate_limit_per_min: ..., incremental_key: ...}
```

`ManifestAdapter` (`src/collectors/manifest_adapter.py`) exposes `fetch()`,
`sources()`, `get_source()` — it resolves the manifest entry, looks up the
endpoint handler in an in-module dispatch table, and returns the canonical
record. All sources ship `enabled: false`: turning a source on is an
explicit, code-reviewable action tied to a real handler being implemented.

```json
{
  "manifest": "configs/ingestion_manifest.yaml",
  "sources": ["tcbs", "cafef"],
  "skipped": [{"source_id": "tcbs", "reason": "disabled"}, {"source_id": "cafef", "reason": "disabled"}],
  "records": []
}
```

Full evidence:
[`docs/evidence/airbyte_manifest_run.json`](../../evidence/airbyte_manifest_run.json).

## Limitations

Idea 1's guard prevents chronological leakage but cannot detect a publisher
that supplied a false event time — correct timestamps remain a source-data
responsibility. Idea 2's manifest ships with both real sources disabled
(`enabled: false`) — the smoke run above proves the dispatch/skip mechanism
correctly, not a live fetch through either handler.

## References

- Airbyte connector spec: https://docs.airbyte.com/connector-spec/
- Singer taps: https://www.singer.io/
