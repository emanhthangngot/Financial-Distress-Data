---
title: "Improve the Data Generator"
date: 2026-08-14
status: active
---

# Improve the Data Generator: config-driven drift simulation and a real label table

This doc proves the three rows in "Improve the Data Generator": drift
simulation is deterministic and seeded, the generator's behavior is entirely
config-driven (YAML, not scenario-specific code), and a real label table
joins to the feature tables on `ticker`. It does not prove a live Feast
materialization for the label join — that path is `design_only` in this
sandbox, disclosed explicitly below.

**Active deployment facts:** `configs/drift-config.yaml`,
`configs/generator-config.yaml` (`ci` profile: 100 companies, 4 quarters),
`src/drift/generator.py`, `src/ml/label_pipeline.py`.

## Part I — Deterministic, seeded drift simulation

### 1. Same seed, byte-identical report across reruns

```text
$ .venv/bin/python scripts/run_phase2_drift_report.py --scenario financial_deterioration
{
  "scenario": "financial_deterioration", "seed": 4001,
  "target_metric": "debt_to_asset",
  "before": {"mean": 0.5793}, "after": {"mean": 0.7079},
  "relative_change": 0.2220, "observed_direction": "increase",
  "configured_direction": "increase", "threshold": 0.10,
  "psi": 4.330, "passed": true
}
```

`apply_drift` uses its own seeded `random.Random(scenario.seed)`, never the
global RNG — verified byte-identical across two runs. Full evidence:
[`LLM-improve-the-data-generato-simulate-data-drift.md`](../../phase2/evidence/llm/LLM-improve-the-data-generato-simulate-data-drift.md).

### 2. Config-driven, not hardcoded — a second scenario proves it

```text
$ .venv/bin/python scripts/run_phase2_drift_report.py --scenario market_stress
{
  "scenario": "market_stress", "seed": 4002,
  "target_metric": "close_price", "observed_stat": "std",
  "before": {"std": 26.46}, "after": {"std": 37.34},
  "relative_change": 0.4109, "observed_direction": "increase",
  "threshold": 0.25, "psi": 1.949, "passed": true
}
```

`market_stress` differs from `financial_deterioration` in seed, target
metric, dataset (`market_prices` vs `financial_statements`), and threshold —
purely by changing `configs/drift-config.yaml`, no code path is
scenario-specific. Full evidence:
[`LLM-improve-the-data-generato-using-generator-configuration.md`](../../phase2/evidence/llm/LLM-improve-the-data-generato-using-generator-configuration.md).

## Part II — Label table

### 3. Label table keyed by ticker + event_timestamp, joinable to feature tables

```text
$ .venv/bin/python -c "... build_labels(offline.financial_statements) ..."
label_version=altman-z-v1
label_source=proxy_not_ground_truth
financial_statement_rows=400
label_rows=400
G0000000 | 2023-04-27T00:00:00+00:00 | None  | False
G0000000 | 2023-10-28T00:00:00+00:00 | 0     | False
G0000000 | 2024-01-27T00:00:00+00:00 | 0     | True
```

`ticker` is the shared join key across every Feast structured feature view
(`ENTITY_NAME = "ticker"`) and this label table. `label=None` rows are
`financial_sector_excluded` (Altman Z''-Score does not apply to
financial-sector tickers) — expected, not missing data, and correctly
carries `training_eligible=False`. `PROXY_LABEL_NOTICE` stamps every row
with `label_source="proxy_not_ground_truth"` — never presented as verified
ground truth. Full evidence:
[`LLM-improve-the-data-generato-t-o-b-ng-label-c-2-c-t-id-v-la.md`](../../phase2/evidence/llm/LLM-improve-the-data-generato-t-o-b-ng-label-c-2-c-t-id-v-la.md).

## Limitations

The Feast structured feature views this label table would join against in
production are `design_only` — no Feast evidence file exists yet because
that pipeline needs a live Redis/MinIO this sandbox cannot reach. The join
is proven at the schema/key level (`ticker`, same source dataset) only, not
against a live Feast materialization. `write_labels_postgres`'s upsert logic
is proven by fake-connection unit tests (`test_label_pipeline.py`), not
against a live Postgres in this evidence run — no Docker network available
in this sandbox.

## References

- Population Stability Index (PSI): standard drift-detection statistic
