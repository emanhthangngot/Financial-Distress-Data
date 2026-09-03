-- Phase 1, rename class C: Postgres schema rename forward migration.
--
-- Brings an existing platform database to the
-- unified target. Idempotent: re-runs cleanly on a partially-migrated
-- instance because the existence checks short-circuit.
--
-- Apply this migration AFTER the application code that uses the new
-- schema names (`ops` and `ml`) has been deployed. The operation is
-- transactional; on a single connection, the application reads either
-- the old names or the new names but never a half-renamed state.
--
-- P2 work (NOT in this migration):
--   - the physical merge of `ops` and `ml` into a single database
--   - the conversion of `created_at` / `updated_at` columns from
--     TIMESTAMP to TIMESTAMPTZ (the "P2 metadata unification" task)
--   - any foreign-key wiring between the two schemas
--
-- This migration is intentionally narrow: schema rename only. The
-- `ALTER SCHEMA ... RENAME TO ...` form is symmetric (reverse
-- direction requires only re-issuing the statements with the original
-- names) and is captured by the rollback file
-- `sql/migrations/001-rename-schemas-to-ops-ml.rollback.sql`.
--
-- The two renames are independent: each guards on the existence of
-- the source schema and the absence of the destination schema, so a
-- partial application does not leave the database in a bad state.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'project_metadata') THEN
        ALTER SCHEMA project_metadata RENAME TO ops;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'ml_metadata') THEN
        ALTER SCHEMA ml_metadata RENAME TO ml;
    END IF;
END
$$;
