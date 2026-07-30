\set ON_ERROR_STOP on
\timing on

BEGIN;

CREATE TEMP TABLE benchmark_source_request_log AS
SELECT
    'request-' || value AS request_id,
    'run-' || (value % 1000) AS run_id,
    'configurable_generator'::text AS source_system,
    '/companies'::text AS source_endpoint,
    'G' || lpad((value % 10000)::text, 7, '0') AS ticker,
    CASE WHEN value % 20 = 0 THEN 'failed' ELSE 'success' END AS request_status,
    timestamp '2026-01-01 00:00:00' + (value || ' seconds')::interval AS requested_at
FROM generate_series(1, 250000) AS value;

ANALYZE benchmark_source_request_log;
DROP INDEX IF EXISTS benchmark_source_request_log_idx;

EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT request_id, ticker, requested_at
FROM benchmark_source_request_log
WHERE run_id = 'run-42'
  AND request_status = 'success'
ORDER BY requested_at DESC
LIMIT 25;

CREATE INDEX benchmark_source_request_log_idx
ON benchmark_source_request_log (run_id, request_status, requested_at DESC);

ANALYZE benchmark_source_request_log;

EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT request_id, ticker, requested_at
FROM benchmark_source_request_log
WHERE run_id = 'run-42'
  AND request_status = 'success'
ORDER BY requested_at DESC
LIMIT 25;

ROLLBACK;

CREATE INDEX IF NOT EXISTS idx_source_request_log_run_status_requested_at
ON project_metadata.source_request_log (run_id, request_status, requested_at DESC);
