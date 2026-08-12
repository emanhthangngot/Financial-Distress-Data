# Evidence — Label table (id + label columns, joinable to feature tables)

Proves `src/ml/label_pipeline.py`'s `build_labels`: a label table keyed by
`ticker` (the `id` column, per the rubric's note that the id column may be
renamed to fit the domain) + `event_timestamp`, with a `label` column,
built from the same `financial_statements` rows the drift/Feast pipeline
publishes — so it joins to `company_financial_features`/
`company_risk_features` on the shared `ticker` key.

- rubric_id: LLM-improve-the-data-generato-t-o-b-ng-label-c-2-c-t-id-v-la
- execution_timestamp: 2026-08-08T07:32:59+00:00
- source_sha: 6c13197663dd6e2a11981167a19bd3ca21ce44ea
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: financial-distress-data@a82af7a, label_version=altman-z-v1
- command: .venv/bin/python -c "from pathlib import Path; from src.generator.config import load_generator_config; from src.generator.offline import generate_offline_data; from src.ml.label_pipeline import build_labels, LABEL_VERSION, LABEL_SOURCE; cfg = load_generator_config(Path('configs/generator-config.yaml'), profile='ci'); offline = generate_offline_data(cfg); labels = build_labels(offline.financial_statements); print(f'label_version={LABEL_VERSION}'); print(f'label_source={LABEL_SOURCE}'); print(f'financial_statement_rows={len(offline.financial_statements)}'); print(f'label_rows={len(labels)}'); [print(f\"{r['ticker']} | {r['event_timestamp']} | {r['label']} | {r['training_eligible']}\") for r in labels[:8]]"
- expected_result: one label row per financial_statement row, schema {ticker, event_timestamp, label, label_version, created_ts, training_eligible, label_source}, `ticker`+`label` project cleanly as the id/label pair the rubric asks for
- actual_result: 400 financial_statement rows in -> 400 label rows out; schema matches exactly (verified by `tests/phase2/pipelines/test_label_pipeline.py::test_build_labels_returns_exact_schema`); sample below
- redaction_status: none — synthetic generator output only, no real PII or secrets

## Command output (real run — verbatim, `command:` field above pasted as-is)

```
label_version=altman-z-v1
label_source=proxy_not_ground_truth
financial_statement_rows=400
label_rows=400
G0000000 | 2023-04-27T00:00:00+00:00 | None | False
G0000000 | 2023-07-28T00:00:00+00:00 | None | False
G0000000 | 2023-10-28T00:00:00+00:00 | 0 | False
G0000000 | 2024-01-27T00:00:00+00:00 | 0 | True
G0000001 | 2023-04-27T00:00:00+00:00 | None | False
G0000001 | 2023-07-28T00:00:00+00:00 | None | False
G0000001 | 2023-10-28T00:00:00+00:00 | 0 | False
G0000001 | 2024-01-27T00:00:00+00:00 | 0 | False
```

(columns are ticker | event_timestamp | label | training_eligible)

`label=None` rows are `financial_sector_excluded` (Altman Z''-Score does not
apply to financial-sector tickers — see
`src/transforms/compute_distress_labels.py::is_financial_sector`); this is
expected, not missing data — those rows correctly carry
`training_eligible=False`.

## The id + label join

`ticker` is the shared join key across every Feast structured feature view
(`src/ml/feast/feature_definitions.py`'s `ENTITY_NAME = "ticker"`) and this
label table — same key, same source dataset (`fact_financial_statement` /
its pre-Gold `financial_statements` rows). The Feast rows are `design_only`
(no Feast evidence file exists yet; that pipeline needs a live Redis/MinIO
this sandbox cannot reach — see the phase-04D scope note), so the join is
proven here at the schema/key level only, not against a live Feast
materialization.

`PROXY_LABEL_NOTICE` (`src/ml/label_pipeline.py`) is stamped alongside every
row's `label_source="proxy_not_ground_truth"` — the label is a rule-based
Altman Z''-Score proxy, never presented as verified ground truth.

## Persistence (design, not executed here)

`write_labels_postgres` upserts into `ml_metadata.label_table`
(`sql/init_ml_metadata.sql`) with `ON CONFLICT (ticker, event_timestamp,
label_version) DO UPDATE ... WHERE EXCLUDED.created_ts >= label_table.
created_ts` (AGENTS.md dedupe-by-latest-created_ts rule). Not exercised
against a live Postgres in this evidence run — no Docker network available
in this sandbox (see `tests/phase2/pipelines/test_label_pipeline.py`'s
`_FakeConn`-based unit tests for the upsert-logic proof, and
`dags/phase2/phase2_label_drift_build.py` for the real wiring).

## Test coverage

`.venv/bin/python -m pytest tests/phase2/pipelines/test_label_pipeline.py -q`
