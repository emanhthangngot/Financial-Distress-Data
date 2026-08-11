# Evidence — Improve the Data Generator: Using generator configuration

Proves the generator is config-driven: `configs/generator-config.yaml`'s
`ci` profile plus `configs/drift-config.yaml`'s `market_stress` scenario
produce a different, independently-configured drift outcome from the
`financial_deterioration` scenario (different seed, different target
metric, different feature shifts) — the behaviour is a function of the YAML
configuration, not a hardcoded scenario.

- rubric_id: LLM-improve-the-data-generato-using-generator-configuration
- execution_timestamp: 2026-08-08T07:28:57+00:00
- source_sha: 758722c52ef3035a7e3f9464dc03c5a39e50a74e
- gitops_sha: 921bdc1075ef8335e0f509747bd64db2d525f73e
- versions: financial-distress-data@a82af7a, generator-config schema_version=1 profile=ci, drift-config schema_version=1
- command: .venv/bin/python scripts/run_phase2_drift_report.py --scenario market_stress
- expected_result: observed_direction == "increase" (configured), relative_change >= threshold (0.25), config-driven — changing configs/drift-config.yaml's market_stress block changes the outcome without any code change
- actual_result: observed_direction="increase", relative_change=0.4109 (before cross-sectional stdev of close_price=26.46, after=37.34), PSI=1.949, passed=true
- redaction_status: none — synthetic generator output only, no real PII or secrets

## Command output (real run)

```
$ .venv/bin/python scripts/run_phase2_drift_report.py --scenario market_stress
wrote /home/pearspringmind/Studying/FSDS/Financial-Distress-Data/outputs/phase2/drift/market_stress/20260808T075108Z/report.json and /home/pearspringmind/Studying/FSDS/Financial-Distress-Data/outputs/phase2/drift/market_stress/20260808T075108Z/report.md
$ echo $?
0
```

`report.json`:

```json
{
  "scenario": "market_stress",
  "seed": 4002,
  "target_metric": "close_price",
  "observed_stat": "std",
  "before": {"mean": 52.9983, "std": 26.4628560837639, "p50": 51.205, "p95": 91.44, "count": 100},
  "after": {"mean": 68.23806, "std": 37.33664825391267, "p50": 60.743, "p95": 140.032, "count": 100},
  "relative_change": 0.41090773179317974,
  "observed_direction": "increase",
  "configured_direction": "increase",
  "threshold": 0.25,
  "psi": 1.949282709163895,
  "passed": true
}
```

## Configuration used

`configs/generator-config.yaml`'s `ci` profile (100 companies, 4 quarters —
`schema_version: 1`, `offline.companies: 100`, `offline.quarters: 4`) drives
`src.generator.offline.generate_offline_data`, whose `market_prices` output
is what `market_stress` drifts:

```yaml
market_stress:
  seed: 4002
  start_quarter: 1
  affected_fraction: 0.5
  feature_shifts:
    close_price: {mode: multiplicative, magnitude: 0.60}
    volume: {mode: multiplicative, magnitude: 0.40}
  target_metric: close_price
  observed_stat: std
  expected_direction: increase
  threshold: 0.25
```

Different seed (4002 vs 4001), different target metric (`close_price` vs
`debt_to_asset`), different dataset (`market_prices` vs
`financial_statements`) — demonstrates the generator/drift pipeline reads
its behaviour entirely from YAML, not from scenario-specific code paths.

## Test coverage

`.venv/bin/python -m pytest tests/phase2/pipelines/test_drift_config.py tests/phase2/pipelines/test_drift_generator.py -q`
