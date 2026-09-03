-- Phase 1, rename class C: schema-rename rollback.
--
-- Mirrors sql/migrations/001-rename-schemas-to-ops-ml.sql in the
-- reverse direction. Apply this if the unified-naming deployment must
-- be undone (e.g. for a hotfix to a code path that still references
-- the legacy `project_metadata` / `ml_metadata` names).
--
-- After applying, the application code MUST be reverted to the legacy
-- names BEFORE the next deployment. The forward + rollback pair
-- covers only the schema-name swap, not the P2 metadata unification
-- (which is a separate, irreversible operation).

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'ops') THEN
        ALTER SCHEMA ops RENAME TO project_metadata;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'ml') THEN
        ALTER SCHEMA ml RENAME TO ml_metadata;
    END IF;
END
$$;
