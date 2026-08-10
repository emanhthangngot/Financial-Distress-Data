-- Rollback for 20260805090000_phase2_ai_usage_audit.sql.
-- Drops the AI request path's counters and audit RPCs in dependency order.
-- Nothing else references these objects, so a clean apply/rollback cycle
-- leaves the schema exactly where it was.

drop function if exists record_audit_event(text, text, text, jsonb);
drop function if exists consume_ai_quota(integer, interval, integer, interval);
drop table if exists ai_request_usage;
drop type if exists ai_usage_kind;