# Novel Idea 1 - dbt-style SQL contracts in DuckDB

## Motivation

A lakehouse is only as good as the contracts on its Gold layer. When a
new view is added under `sql/duckdb_create_views.sql` with a typo in the
layer prefix (e.g. `gold_dim_company_x` instead of
`gold_dim_company_x_v2`), the failure is silent: the view parses,
DBeaver can browse it, and the downstream DuckDB queries keep
returning data - just the wrong data. Phase 1 already standardises
the *physical* layer (`gold/`) and the *logical* layer (dim/fact/obt/feat)
in `docs/02_schema_design.md`, but the link between the two has to be
remembered by humans. We need a machine-checkable contract so a typo
becomes a CI failure rather than a production incident.

## Prior art

- **dbt** enforces source and model naming through the `sources.yml`
  schema block and the `generate_schema_name` macro. The convention is
  declared once and validated on every `dbt build`.
- **SQLFluff** rules and **dbt-project-evaluator** ship pack-of-config
  rules that flag views whose names drift from the project convention.

The difference for this project: we do not have dbt, and adding it
would be a heavy dependency for a single contract. DuckDB already
gives us a macro system; we use that.

## Design

Two artefacts, kept in lock-step:

1. **DuckDB macro** at `src/quality/sql_contract_macros.sql` -
   `enforce_naming_convention(view_name, allowed_prefixes)`. The
   macro raises if the view does not start with one of the allowed
   prefixes; it is loaded by anyone running the views in DuckDB and
   is the authoritative rule.

2. **Python mirror** at `src/quality/sql_contract_runner.py` - the
   `classify_view(name)` and `check_duckdb_views(sql_path, evidence_path)`
   functions apply the same rule offline. The runner:
   - reads `sql/duckdb_create_views.sql`,
   - pulls out every `CREATE [OR REPLACE] VIEW <name>` statement,
   - classifies by layer prefix (`dim`, `fact`, `obt`, `feat`),
   - writes `docs/evidence/dbt_macro_check.json` with `{total_views,
     by_layer, violations}`.

The mirror exists so the contract is testable in CI without spinning
up a DuckDB runtime, and so a future pre-commit hook can run the same
check in milliseconds.

## Code paths

| Layer | File |
|-------|------|
| SQL rule | `src/quality/sql_contract_macros.sql` |
| Python runner | `src/quality/sql_contract_runner.py` |
| Tests (16) | `tests/test_sql_contract_runner.py` |
| Evidence | `docs/evidence/dbt_macro_check.json` |

## Evidence

Regenerate the evidence with:

```bash
.venv/bin/python -m src.quality.sql_contract_runner
```

Current snapshot (regenerated on every CI run):

```json
{
  "total_views": 11,
  "by_layer": {"dim": 2, "fact": 4, "feat": 4, "obt": 1},
  "violations": []
}
```

That is, the eleven Gold views currently registered all conform to
the convention; no rework needed.

## Limitations

- The macro syntax uses DuckDB-specific `error(...)` and
  `array_to_string`; the SQL file is committed as documentation and
  for direct DuckDB use, but the CI gate is the Python mirror.
- The mirror parses the SQL with a regex; complex edge cases
  (e.g. quoted view names with reserved words) would need a real
  SQL parser.
- `distress_labels` is a Gold materialisation read directly from
  Parquet and is intentionally excluded from the view contract.

## Next steps

1. Wire the runner into the data quality DAG (`dags/09_data_contracts.py`
   or equivalent) so the evidence is regenerated on every run.
2. Extend the allowed prefix set to include `silver_*` once Silver
   views are added in Phase 2.
3. Add a pre-commit hook that runs the runner on staged changes to
   `sql/duckdb_create_views.sql`.
