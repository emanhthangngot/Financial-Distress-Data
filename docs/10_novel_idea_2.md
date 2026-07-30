# Novel Idea 2 - Airbyte-style declarative ingestion manifest

## Motivation

Today, every new data source means new Python: a new class in
`src/collectors/`, a new branch in the dispatcher, a new entry in
the DAG, a new import in the test suite. The cost of adding a
source is paid in code, which means it is paid per-source rather
than per-convention. We want to make the *shape* of an ingestion
source a one-line declaration (YAML) and let a single dispatcher
class bind the convention to actual fetch logic. The inspiration is
[Airbyte connectors](https://docs.airbyte.com/connector-spec/): a
connector is a manifest plus a protocol, not a bespoke script.

## Prior art

- **Airbyte** is the most visible example. Each connector ships a
  `spec.yaml` and a `catalog.json`; the runtime reads both and
  drives the connector through a uniform interface.
- **Singer** taps follow the same pattern: a `catalog.json` plus
  a state file, with the tap implementing a single `read` method.
- **dlt** (data load tool) generates sources from function
  signatures and config dictionaries, leaning on Python typing
  rather than YAML.

The difference for this project: Airbyte/Singer are external
services that we are not running locally in Phase 1, and pulling
in `dlt` is overkill for two declared sources. The value is the
*pattern*, not the dependency - a small YAML manifest plus a
single dispatcher class is the right-size borrowing.

## Design

Two artefacts, kept in lock-step:

1. **Manifest** at `configs/ingestion_manifest.yaml` - one
   entry per source with `source_id`, `enabled`, `endpoint`,
   `field_map`, `rate_limit_per_min`, and `incremental_key`.
   All sources ship with `enabled: false`: turning a source on is
   an explicit, code-reviewable action tied to a real handler
   being implemented.

2. **Dispatcher** at `src/collectors/manifest_adapter.py` -
   `class ManifestAdapter` exposes `fetch(symbol, source_id)`,
   `sources()`, and `get_source(source_id)`. The dispatcher
   resolves the manifest entry, looks up the endpoint handler
   in an in-module dispatch table, and returns the canonical
   record whose keys are the `field_map` values.

The fixture handler ships in the same module so the adapter is
exercisable in CI without network access. The smoke runner
(`src/collectors/run_manifest_smoke.py`) is the proof of life: it
iterates the manifest, calls `fetch()` for a representative
symbol, and writes `docs/evidence/airbyte_manifest_run.json`
with `records`, `per_source_counts`, and `skipped` arrays.

## Code paths

| Layer | File |
|-------|------|
| Manifest | `configs/ingestion_manifest.yaml` |
| Dispatcher | `src/collectors/manifest_adapter.py` |
| Smoke runner | `src/collectors/run_manifest_smoke.py` |
| Tests (7) | `tests/test_manifest_adapter.py` |
| Evidence | `docs/evidence/airbyte_manifest_run.json` |

## Evidence

Regenerate the evidence with:

```bash
.venv/bin/python -m src.collectors.run_manifest_smoke
```

Current snapshot (regenerated on every CI run; both shipped
sources are `enabled: false` so the record list is empty by
design):

```json
{
  "manifest": "configs/ingestion_manifest.yaml",
  "sources": ["tcbs", "cafef"],
  "per_source_counts": {},
  "records": [],
  "skipped": [
    {"source_id": "tcbs", "reason": "disabled"},
    {"source_id": "cafef", "reason": "disabled"}
  ]
}
```

The seven tests in `tests/test_manifest_adapter.py` exercise the
dispatcher with inline enabled manifests (in `tmp_path`) so the
real fixture handler is invoked end-to-end.

## Limitations

- Live handlers (`vnstock`, `tcbs_http`, `cafef_scrape`) are
  reserved keys but not implemented; the manifest reserves them
  so the YAML is forward-compatible.
- The dispatch table is an in-module Python dict. A pluggable
  entry-point registry would be the natural extension when more
  than a handful of live handlers exist.
- The smoke runner defaults to one symbol per source; per-source
  fan-out and back-pressure logic are not in scope.

## Next steps

1. Implement the first live handler (`vnstock`) and flip its
   manifest entry to `enabled: true` once the handler is
   reviewed.
2. Add a CI assertion that the evidence JSON's `skipped` list is
   a subset of the manifest's `source_id` set, to catch
   dispatcher/manifest drift.
3. When Phase 2 lands, generalise the manifest schema with
   `cursor_field` and `primary_key` so incremental loads can be
   expressed declaratively rather than coded per-source.
