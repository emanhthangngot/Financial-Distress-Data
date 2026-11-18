# ADR-020: Source data reality

## Status

Accepted — 2026-09-02 (`plans/260831-1644-rebuild-target-mlops-architecture/plan.md`
§Source Data Reality, verified against vnstock 4.0.7).

## Context

Claims about the live vnstock adapter must be checked, not assumed —
version-sensitive facts (API shapes, unit conventions, tier limits) are
stale until verified this session (`AGENTS.md` §Claim Discipline).

## Decision — record the measured facts, not the aspiration

- **The "live adapter" does not exist yet.**
  `src/collectors/source_adapters/vnstock_adapter.py` is a 13-line re-export
  of the fixture adapter. `vnstock` is in no dependency file
  (`requirements*.txt`, `pyproject.toml`). `src/collectors/` makes zero
  network calls. `configs/collector_config.yaml` nonetheless declares
  `source_mode: online` — a config claim the code does not back. This split
  (fixture-backed collectors, online-labeled config) is the adopted design
  for Phase 4, not a bug to silently fix: Phase 4 (`phase-04-data-plane.md`)
  owns wiring a real adapter.
- **vnstock 4.0.7 uses a Unified UI** (`Market`, `Reference`, `Fundamental`).
  Financial statements are served by the **`kbs`** and **`vci`** explorers
  only. TCBS was removed after 3.x; its REST paths return 404 (verified this
  session by direct call, not inferred from documentation).
- **Statements arrive in whole VND đồng at 1,000đ granularity.**
  `kbs/financial.py:572` requests `"unit": 1000  # Đơn vị ngàn đồng`;
  `:369` passes `unit_multiplier=1000.0`; `:259` applies
  `value * unit_multiplier`. VCI confirmed independently by a live call:
  VNM `current_assets` 2026-Q2 = `4.089226e+13`, matching Vinamilk's
  published balance sheet at whole-đồng scale. Both explorers deliver the
  same unit — `vci/const.py:105`'s `_UNIT_MAP = {"BILLION": "tỷ", ...,
  "MILLION": "triệu"}` looked like a divergence risk and is dead code (one
  grep hit across the package: its own definition).
- **Prices arrive in nghìn đồng, not VND.** `kbs/quote.py:345,506` divide by
  1000 for stock and ETF assets. Confirmed live: VNM `close` in the range
  46.45–98.98 for the observed window. This adapter normalizes prices back
  to đồng before they reach Bronze (F17) — the older doc claim that vnstock
  returns prices in VND is wrong by 1000× and is corrected by this ADR.
- **The four `fallback_sources` in `collector_config.yaml`
  (`cafe_f`/`vietstock`/`tcbs`/`ssi`) have no adapter.** `source_mapping.yaml`
  declares three sources with two `enabled: false`; `ingestion_manifest.yaml`
  declares two, both `enabled: false` with `endpoint: fixture`; `vietstock`
  and `ssi` appear in **no** mapping file at all; `cafe_f` is spelled two
  different ways across the config files (plan D-22). There was never a real
  unit to verify for these sources because there is no code path that calls
  them.
- **The free vnstock tier caps financial statements at 4 periods, hard.**
  `period='quarter'` returns the four most recent quarters, `period='year'`
  the four most recent years — not a pagination window, and Community
  registration does not lift it. Against `collector_config.yaml`'s
  2018-2025 quarterly range, 28 of 32 quarters per company are unobtainable
  on the free tier; KBS statements return `shape (0, 0)` entirely on the
  free tier (only VCI serves them). This is a Phase 4 free-tier data
  ceiling (plan D-21, R-18), not a Phase 2 contract concern — it affects
  volume, not the money-unit/type decisions ADR-017 makes.

## Decision — fail-closed rule

Every money-bearing Bronze contract carries `source_name` and `source_unit`
as `NOT NULL` (`src/metadata/schema_registry.py` v2 contracts). A row whose
`source_unit` is not in the recognized set is routed to
`ops.failed_records` with a `failure_reason` naming the unit — it is never
normalized by guess. The unit is a property of *which adapter answered*,
not of "vnstock" as a monolith, because the four unverified fallback
sources could deliver a different unit with no code currently able to
detect it.

## Consequences

- `DECIMAL(18,0)` (ADR-017) holds for every reachable source today —
  confirmed, not assumed, because the only two live explorers both deliver
  whole đồng and the four alternatives have no handler.
- Any future adapter for `cafe_f`/`vietstock`/`tcbs`/`ssi` must populate
  `source_unit` correctly on day one or every row it produces fails closed
  into `ops.failed_records` rather than silently corrupting the money
  columns.
- Statement history for the coursework's requested 2018-2025 window requires
  synthesis for 28 of 32 quarters per company (Phase 4), not only for
  volume padding.

## Alternatives Considered

- **Trust `collector_config.yaml`'s `source_mode: online` claim and treat
  the adapter as live** (rejected — zero network calls exist in
  `src/collectors/`; the claim would have been discovered false at the
  first live run, not before).
- **Assume vnstock returns VND for both statements and prices** (rejected —
  directly contradicted by source code and a live call; would have silently
  mis-scaled every price-derived feature by 1000×, exactly the class of bug
  F17 records).
