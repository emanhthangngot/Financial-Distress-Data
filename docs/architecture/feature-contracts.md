# Feature Contracts: TTL and Knowledge-Time Axis

Rubric: mini-19 (`ML-feature-store-define-ttl-cho-t-ng-b-ng-featu`), phase-05-cdc-streaming.md
AC-P5-6, F14. Owner: `src/ml/feast/feature_definitions.py` (`FEATURE_VIEW_TTL`,
`FEATURE_VIEW_RATIONALE`) — this document explains those values; it does not define new ones.
Values here are read directly from that module, not retyped from memory; a divergence between
this table and the module is a bug in this document, not a second source of truth.

## Knowledge-time axis (ADR-017 §Feast temporal contract, F14)

Every file-backed `FeatureView`'s `event_timestamp` join axis is bound to the Gold
`known_from_ts` column, never a raw `event_timestamp` field:

```
feat_*  event_timestamp   := known_from_ts     ← knowledge time IS Feast's join axis
        created_timestamp := ingest wall clock ← breaks ties between retries of one ingest only
        report_period     := feature attribute, NOT a time axis
```

This is a design decision, not a fallback. Feast's default tie-break on `created_timestamp`
selects the **highest** value for a given `event_timestamp` — i.e. the newest vintage — which is
exactly the point-in-time leakage this data model exists to prevent (schema audit F14). Mapping
`event_timestamp` to `known_from_ts` instead makes "what was knowable as of `known_from_ts`" the
axis Feast actually joins on. Enforced by `tests/platform/pipelines/test_feast_known_from_ts_axis.py`,
which asserts `timestamp_field == "known_from_ts"` on every declared `FileSource`.

## TTL table

| Feature view | Gold source | TTL | Reason |
|---|---|---|---|
| `company_financial_features` | `fact_financial_statement` | 100 days | A quarterly filing stays the authoritative view of the company until the next filing lands; 100 days is approximately one quarter plus filing lag, so nothing expires while it is still the newest truth. |
| `company_risk_features` | `obt_company_quarter_risk` | 100 days | Derived from the same quarterly filing as `company_financial_features` (`obt_company_quarter_risk` joins the fact to the label), so it must not expire before its parent fact does. |
| `market_price_features` | `fact_market_price` | 2 days | A daily bar is superseded by the next trading session; 2 days survives a weekend/holiday gap without ever serving a week-old price as current. |
| `stream_market_features` | `fact_market_price` (batch fallback via `PushSource`) | 1 hour | Intraday aggregates describe the current trading hour only; a longer TTL would let the online API answer "live" with a stale tick. |

`stream_market_features` has no Gold `FileSource` of its own — its `PushSource.batch_source` is
`market_price_features`'s `FileSource`, so an online-store miss still resolves through the daily
bar rather than failing closed.

## Verification

- `tests/platform/pipelines/test_feast_definitions_ttl.py` pins the TTL table above, one rationale
  string per view, and that `GOLD_DATASETS` covers every file-backed view.
- `tests/platform/pipelines/test_feast_known_from_ts_axis.py` pins the `known_from_ts` binding.
- Both import real Feast and run under `.venv-platform` only (D4 lazy-import rule); `.venv`'s fast
  loop never imports Feast.

## Not verified this session

`AC-P5-3` (Feast materializes from a live Postgres offline store into Redis) and the live-cluster
half of `AC-P5-16` (a restated vintage observed through a running materialization job does not
overwrite the earlier vintage's online row) require a deployed `platform-features` stack. This
document covers the code-level contract (TTL values, rationale, and the `known_from_ts` binding)
that a live materialization run would execute against; it does not claim that run happened.
