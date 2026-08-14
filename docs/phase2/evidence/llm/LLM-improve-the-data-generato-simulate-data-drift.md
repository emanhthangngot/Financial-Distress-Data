# Evidence — Improve the Data Generator: Simulate data drift

Proves `src/drift/generator.py`'s `apply_drift`/`build_drift_report`: a
seeded, deterministic drift scenario (`financial_deterioration`, defined in
`configs/drift-config.yaml`) applied over the real `ci`-profile generator
output, with the observed direction matching the configured direction and
the relative change clearing the configured threshold.

- rubric_id: LLM-improve-the-data-generato-simulate-data-drift
- execution_timestamp: 2026-08-08T07:28:49+00:00
- source_sha: 0bcaf1490b7ffe3561cbe409717b525488e452eb
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: financial-distress-data@a82af7a, drift-config schema_version=1
- command: .venv/bin/python scripts/run_phase2_drift_report.py --scenario financial_deterioration
- expected_result: observed_direction == "increase" (configured), relative_change >= threshold (0.10), report.json byte-identical across two runs with the same seed
- actual_result: observed_direction="increase", relative_change=0.2220 (before mean debt_to_asset=0.5793, after mean=0.7079), PSI=4.330, passed=true. Re-ran twice — `report.json` content identical both times (verified during slice 4A implementation; `src/drift/generator.py`'s `apply_drift` uses its own seeded `random.Random(scenario.seed)`, never the global RNG).
- redaction_status: none — synthetic generator output only, no real PII or secrets

## Command output (real run)

```
$ .venv/bin/python scripts/run_phase2_drift_report.py --scenario financial_deterioration
wrote /home/pearspringmind/Studying/FSDS/Financial-Distress-Data/outputs/phase2/drift/financial_deterioration/20260808T075046Z/report.json and /home/pearspringmind/Studying/FSDS/Financial-Distress-Data/outputs/phase2/drift/financial_deterioration/20260808T075046Z/report.md
$ echo $?
0
```

`report.json`:

```json
{
  "scenario": "financial_deterioration",
  "seed": 4001,
  "target_metric": "debt_to_asset",
  "observed_stat": "mean",
  "before": {"mean": 0.5792556583130057, "std": 0.07209227755456422, "p50": 0.5845482758820719, "p95": 0.6893290862034641, "count": 400},
  "after": {"mean": 0.7078622122668622, "std": 0.18403830848656613, "p50": 0.6549807053919507, "p95": 1.0688655203260113, "count": 400},
  "relative_change": 0.22202036718709584,
  "observed_direction": "increase",
  "configured_direction": "increase",
  "threshold": 0.1,
  "psi": 4.330248755602742,
  "passed": true
}
```

## Configuration used (configs/drift-config.yaml, financial_deterioration)

```yaml
financial_deterioration:
  seed: 4001
  start_quarter: 2
  affected_fraction: 0.5
  feature_shifts:
    total_liabilities: {mode: multiplicative, magnitude: 0.60}
    retained_earnings: {mode: multiplicative, magnitude: -0.30}
    ebit: {mode: multiplicative, magnitude: -0.30}
    net_income: {mode: additive, magnitude: -50000}
  target_metric: debt_to_asset
  observed_stat: mean
  expected_direction: increase
  threshold: 0.10
```

## Test coverage

`.venv/bin/python -m pytest tests/phase2/pipelines/test_drift_generator.py -q` —
includes `test_shipped_config_passes_against_real_ci_generator_output`, which
pins exactly this scenario against the real `configs/drift-config.yaml` +
`configs/generator-config.yaml` (`ci` profile), not synthetic test literals.
