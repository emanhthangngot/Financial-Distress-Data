-- Migration 002: data model v2 (plan phase-02-data-model.md).
--
-- One transaction. If any step fails the whole migration rolls back — there is
-- no partially-migrated state. Every timestamp cast is explicit
-- `AT TIME ZONE 'UTC'`; a bare `ALTER TYPE ... TO timestamptz` reinterprets a
-- naive value in the session timezone, which is exactly the silent 7-hour bug
-- (D-13) this migration exists to avoid, not reintroduce.
--
-- Idempotent: every step is guarded so re-running against an already-migrated
-- database is a no-op, not an error.

BEGIN;

-- ---------------------------------------------------------------------------
-- ops: TIMESTAMP -> TIMESTAMPTZ (explicit UTC), `_at` -> `_ts` rename
-- ---------------------------------------------------------------------------

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'ops' AND table_name = 'pipeline_run_log' AND column_name = 'started_at'
    ) THEN
        ALTER TABLE ops.pipeline_run_log
            ALTER COLUMN started_at TYPE TIMESTAMPTZ USING started_at AT TIME ZONE 'UTC',
            ALTER COLUMN ended_at TYPE TIMESTAMPTZ USING ended_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';
        ALTER TABLE ops.pipeline_run_log RENAME COLUMN started_at TO started_ts;
        ALTER TABLE ops.pipeline_run_log RENAME COLUMN ended_at TO ended_ts;
        ALTER TABLE ops.pipeline_run_log RENAME COLUMN created_at TO created_ts;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'ops' AND table_name = 'dataset_freshness' AND column_name = 'checked_at'
    ) THEN
        ALTER TABLE ops.dataset_freshness
            ALTER COLUMN latest_event_timestamp TYPE TIMESTAMPTZ USING latest_event_timestamp AT TIME ZONE 'UTC',
            ALTER COLUMN latest_ingest_ts TYPE TIMESTAMPTZ USING latest_ingest_ts AT TIME ZONE 'UTC',
            ALTER COLUMN checked_at TYPE TIMESTAMPTZ USING checked_at AT TIME ZONE 'UTC';
        ALTER TABLE ops.dataset_freshness RENAME COLUMN latest_event_timestamp TO latest_event_ts;
        ALTER TABLE ops.dataset_freshness RENAME COLUMN checked_at TO checked_ts;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'ops' AND table_name = 'schema_version_registry' AND column_name = 'effective_from'
    ) THEN
        ALTER TABLE ops.schema_version_registry
            ALTER COLUMN effective_from TYPE TIMESTAMPTZ USING effective_from AT TIME ZONE 'UTC',
            ALTER COLUMN effective_to TYPE TIMESTAMPTZ USING effective_to AT TIME ZONE 'UTC';
        ALTER TABLE ops.schema_version_registry RENAME COLUMN effective_from TO effective_from_ts;
        ALTER TABLE ops.schema_version_registry RENAME COLUMN effective_to TO effective_to_ts;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'ops' AND table_name = 'failed_records' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE ops.failed_records
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';
        ALTER TABLE ops.failed_records RENAME COLUMN created_at TO created_ts;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'ops' AND table_name = 'backfill_request' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE ops.backfill_request
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';
        ALTER TABLE ops.backfill_request RENAME COLUMN created_at TO created_ts;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'ops' AND table_name = 'source_request_log' AND column_name = 'requested_at'
    ) THEN
        ALTER TABLE ops.source_request_log
            ALTER COLUMN requested_at TYPE TIMESTAMPTZ USING requested_at AT TIME ZONE 'UTC';
        ALTER TABLE ops.source_request_log RENAME COLUMN requested_at TO requested_ts;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'ops' AND table_name = 'collector_checkpoint' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE ops.collector_checkpoint
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC';
        ALTER TABLE ops.collector_checkpoint RENAME COLUMN updated_at TO updated_ts;
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- ops.data_quality_result: add `track`, `run_id` FK, rename checked_at -> checked_ts
-- ---------------------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'ops' AND table_name = 'data_quality_result' AND column_name = 'track'
    ) THEN
        ALTER TABLE ops.data_quality_result ADD COLUMN track TEXT;
        UPDATE ops.data_quality_result SET track = 'mini' WHERE track IS NULL;
        ALTER TABLE ops.data_quality_result ALTER COLUMN track SET NOT NULL;
        ALTER TABLE ops.data_quality_result
            ADD CONSTRAINT data_quality_result_track_check CHECK (track IN ('mini', 'ml', 'llm'));
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'ops' AND table_name = 'data_quality_result' AND column_name = 'checked_at'
    ) THEN
        ALTER TABLE ops.data_quality_result
            ALTER COLUMN checked_at TYPE TIMESTAMPTZ USING checked_at AT TIME ZONE 'UTC';
        ALTER TABLE ops.data_quality_result RENAME COLUMN checked_at TO checked_ts;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'data_quality_result_run_id_fkey'
    ) THEN
        ALTER TABLE ops.data_quality_result
            ADD CONSTRAINT data_quality_result_run_id_fkey
            FOREIGN KEY (run_id) REFERENCES ops.pipeline_run_log (run_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_data_quality_result_track_checked
    ON ops.data_quality_result (track, checked_ts);

-- ---------------------------------------------------------------------------
-- ops.failed_records / ops.source_request_log: run_id FK (nullable — MATCH
-- SIMPLE lets ad-hoc scripts degrade gracefully; the NULL-rate ceiling lives
-- in the DQ gate, not here, because "zero orphans" is vacuous on an
-- entirely-NULL column, F16).
-- ---------------------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'failed_records_run_id_fkey') THEN
        ALTER TABLE ops.failed_records
            ADD CONSTRAINT failed_records_run_id_fkey
            FOREIGN KEY (run_id) REFERENCES ops.pipeline_run_log (run_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'source_request_log_run_id_fkey') THEN
        ALTER TABLE ops.source_request_log
            ADD CONSTRAINT source_request_log_run_id_fkey
            FOREIGN KEY (run_id) REFERENCES ops.pipeline_run_log (run_id);
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- ops.schema_version_registry: is_current becomes a derived flag enforced by
-- a partial unique index, never a write-time filter.
-- ---------------------------------------------------------------------------

CREATE UNIQUE INDEX IF NOT EXISTS uq_schema_version_registry_current
    ON ops.schema_version_registry (dataset_name) WHERE is_current;

COMMIT;

-- ---------------------------------------------------------------------------
-- ml schema: separate Postgres instance (platform-postgres). Run this block
-- there. Kept in the same file for one source of truth; the two BEGIN/COMMIT
-- blocks are independent transactions because they target different servers.
-- ---------------------------------------------------------------------------

BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'ml' AND table_name = 'label_table'
    ) THEN
        ALTER TABLE ml.label_table RENAME TO distress_label;
    END IF;
END $$;

-- ml.data_quality_result is dropped: merged into ops.data_quality_result (F4).
-- Only drop if empty or the operator has already migrated its rows — this
-- migration does not silently discard DQ history.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'ml' AND table_name = 'data_quality_result'
    ) THEN
        IF NOT EXISTS (SELECT 1 FROM ml.data_quality_result LIMIT 1) THEN
            EXECUTE 'DROP TABLE ml.data_quality_result';
        END IF;
    END IF;
END $$;

COMMIT;
