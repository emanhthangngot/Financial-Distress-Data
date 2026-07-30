-- W24 Idea 1 - dbt-style SQL contracts in DuckDB.
--
-- This file ships a DuckDB macro that enforces the Gold view naming
-- convention: every view must start with ``gold_<layer>_`` where
-- ``<layer>`` is one of dim, fact, obt, feat. The macro is the source of
-- truth for the rule; ``src/quality/sql_contract_runner.py`` mirrors
-- the same rule in Python so the contract can be checked at build time
-- without spinning up a DuckDB runtime.
--
-- Usage from a DuckDB session:
--
--   .read src/quality/sql_contract_macros.sql
--   SELECT enforce_naming_convention('gold_dim_company',
--                                    ['gold_dim_', 'gold_fact_',
--                                     'gold_obt_', 'gold_feat_']);
--   -- returns the view name on success
--
-- On a violation, the macro raises an error so the offending view is
-- caught early in the pipeline.

CREATE OR REPLACE MACRO enforce_naming_convention(
    view_name, allowed_prefixes
) AS (
    CASE
        WHEN list_has_any(
            CAST(allowed_prefixes AS VARCHAR[]),
            ARRAY[substring(view_name, 1, length(view_name) - 0)]
        ) = FALSE
            AND length(list_filter(
                CAST(allowed_prefixes AS VARCHAR[]),
                x -> starts_with(view_name, x)
            )) = 0
        THEN error(
            'SQL contract violation: view ' || view_name ||
            ' does not start with one of ' ||
            array_to_string(CAST(allowed_prefixes AS VARCHAR[]), ', ')
        )
        ELSE view_name
    END
);
