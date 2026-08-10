-- Per-user AI budget persistence: quota and rate-limit counters plus a
-- consent-safe audit write for the AI request path.
--
-- Two problems in one migration:
--
-- 1. checkQuota / checkRateLimit in apps/web/src/lib/server/guards.ts already
--    decide correctly, but nothing supplies them with persisted state. This
--    migration gives the counters a durable, RLS-protected home and makes the
--    consume+check one atomic call so two concurrent requests cannot both take
--    the last unit of a limit.
-- 2. Every product-boundary decision writes one audit_log row. The RPC below is
--    the only AI-request audit path, and its signature makes prompt text
--    unrepresentable: there is no free-text message parameter at all.
--
-- The window is fixed and bucketed (epoch-seconds floor), not sliding: a fixed
-- window lets the UI state an exact reset time. TypeScript formats the window
-- start returned here and never recomputes it, so the two cannot drift.

create type ai_usage_kind as enum ('QUOTA', 'RATE_LIMIT');

-- One row per (user, kind, window_start): a bounded counter table whose old
-- rows are pruned by the consuming RPC itself, so it never needs a scheduler.
create table ai_request_usage (
  user_id      uuid not null references auth.users (id) on delete cascade,
  kind         ai_usage_kind not null,
  window_start timestamptz not null,
  used         integer not null default 0 check (used >= 0),
  updated_at   timestamptz not null default now(),
  primary key (user_id, kind, window_start)
);

alter table ai_request_usage enable row level security;

-- A user reads only their own usage; there is deliberately no insert/update/
-- delete policy, so the counters can only move through consume_ai_quota().
create policy ai_request_usage_select_own on ai_request_usage
  for select using (user_id = (select auth.uid()));

-- Atomic consume + check. Returns the post-decision state so the caller never
-- needs a second read, and so the check and the increment cannot interleave:
-- `insert ... on conflict do update` locks the conflicting row, so a concurrent
-- caller blocks until this one commits, then sees the incremented count.
create or replace function consume_ai_quota(
  p_quota_limit  integer,
  p_quota_window interval,
  p_rate_limit   integer,
  p_rate_window  interval
) returns table (
  allowed         boolean,
  denial          text,   -- null | 'RATE_LIMITED' | 'QUOTA_EXHAUSTED'
  quota_used      integer,
  quota_limit     integer,
  quota_resets_at timestamptz,
  rate_used       integer,
  rate_limit      integer,
  rate_resets_at  timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id           uuid := auth.uid();
  v_quota_window_secs double precision;
  v_rate_window_secs  double precision;
  v_quota_start       timestamptz;
  v_rate_start        timestamptz;
  v_quota_before      integer;
  v_rate_before       integer;
  v_quota_after       integer;
  v_rate_after        integer;
begin
  if v_user_id is null then
    raise exception 'consume_ai_quota requires an authenticated caller'
      using errcode = 'P0002';
  end if;

  v_quota_window_secs := extract(epoch from p_quota_window);
  v_rate_window_secs := extract(epoch from p_rate_window);

  if v_quota_window_secs <= 0 or v_rate_window_secs <= 0 then
    raise exception 'AI quota and rate windows must be positive'
      using errcode = '22023';
  end if;

  v_quota_start := to_timestamp(
    floor(extract(epoch from now()) / v_quota_window_secs) * v_quota_window_secs
  );
  v_rate_start := to_timestamp(
    floor(extract(epoch from now()) / v_rate_window_secs) * v_rate_window_secs
  );

  -- Serialize on the counter row. When the row does not exist yet this inserts
  -- a zero row; a concurrent insert on the same primary key blocks until this
  -- transaction commits and then takes the conflict path, so the lock is real.
  insert into ai_request_usage (user_id, kind, window_start, used)
  values (v_user_id, 'QUOTA', v_quota_start, 0)
  on conflict (user_id, kind, window_start)
  do update set used = ai_request_usage.used
  returning used into v_quota_before;

  insert into ai_request_usage (user_id, kind, window_start, used)
  values (v_user_id, 'RATE_LIMIT', v_rate_start, 0)
  on conflict (user_id, kind, window_start)
  do update set used = ai_request_usage.used
  returning used into v_rate_before;

  -- A denial increments neither counter: a refused request must not spend the
  -- analyst's budget.
  if v_rate_before >= p_rate_limit then
    allowed := false;
    denial := 'RATE_LIMITED';
    quota_used := v_quota_before;
    quota_limit := p_quota_limit;
    quota_resets_at := v_quota_start + p_quota_window;
    rate_used := v_rate_before;
    rate_limit := p_rate_limit;
    rate_resets_at := v_rate_start + p_rate_window;
    return next;
    return;
  end if;

  if v_quota_before >= p_quota_limit then
    allowed := false;
    denial := 'QUOTA_EXHAUSTED';
    quota_used := v_quota_before;
    quota_limit := p_quota_limit;
    quota_resets_at := v_quota_start + p_quota_window;
    rate_used := v_rate_before;
    rate_limit := p_rate_limit;
    rate_resets_at := v_rate_start + p_rate_window;
    return next;
    return;
  end if;

  update ai_request_usage set used = used + 1, updated_at = now()
  where user_id = v_user_id and kind = 'QUOTA' and window_start = v_quota_start
  returning used into v_quota_after;

  update ai_request_usage set used = used + 1, updated_at = now()
  where user_id = v_user_id and kind = 'RATE_LIMIT' and window_start = v_rate_start
  returning used into v_rate_after;

  -- Bounded table without a scheduler: drop this caller's rows older than two
  -- windows of their kind, inside the same call that just used them.
  delete from ai_request_usage
  where user_id = v_user_id and kind = 'QUOTA'
    and window_start < now() - 2 * p_quota_window;
  delete from ai_request_usage
  where user_id = v_user_id and kind = 'RATE_LIMIT'
    and window_start < now() - 2 * p_rate_window;

  allowed := true;
  denial := null;
  quota_used := v_quota_after;
  quota_limit := p_quota_limit;
  quota_resets_at := v_quota_start + p_quota_window;
  rate_used := v_rate_after;
  rate_limit := p_rate_limit;
  rate_resets_at := v_rate_start + p_rate_window;
  return next;
end;
$$;

-- Consent-safe audit write for the AI request path. No prompt, no token, no
-- response body: p_context_id is a ticker or session id, never free text, and
-- p_metadata admits only whitelisted scalar keys. `outcome` is added by the
-- function itself after validation, never accepted from the caller's jsonb.
create or replace function record_audit_event(
  p_action     text,   -- e.g. 'ai.request'
  p_outcome    text,   -- ALLOWED | RATE_LIMITED | QUOTA_EXHAUSTED | FORBIDDEN | PLANE_OFF | FAILED
  p_context_id text,   -- ticker or session id, never free text
  p_metadata   jsonb   -- whitelisted scalar keys only, validated in-function
) returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid := auth.uid();
  v_role    app_role := current_app_role();
  v_id      uuid;
begin
  if v_user_id is null or v_role is null then
    raise exception 'record_audit_event requires an authenticated caller'
      using errcode = 'P0002';
  end if;

  if not (p_outcome = any (array['ALLOWED', 'RATE_LIMITED', 'QUOTA_EXHAUSTED',
                               'FORBIDDEN', 'PLANE_OFF', 'FAILED'])) then
    raise exception 'audit outcome % is not permitted', p_outcome
      using errcode = '22023';
  end if;

  -- Reject a non-whitelisted key and any compound value (object/array): a
  -- nested object is exactly where prompt text could be hidden.
  if exists (
    select 1
    from jsonb_each(p_metadata) as kv(key, value)
    where kv.key <> all (array['reason', 'quota_remaining', 'rate_remaining', 'attempt'])
       or jsonb_typeof(kv.value) in ('object', 'array')
  ) then
    raise exception 'audit metadata key or value type is not permitted'
      using errcode = '22023';
  end if;

  insert into audit_log (actor_id, actor_role, action, resource, metadata)
  values (
    v_user_id,
    v_role,
    p_action,
    p_context_id,
    p_metadata || jsonb_build_object('outcome', p_outcome)
  )
  returning id into v_id;

  return v_id;
end;
$$;

-- Explicit privilege surface, following the hardening pattern in
-- 20260804160000_phase2_function_grant_hardening.sql: revoke the Supabase
-- default broad grants first, then hand back only what a policy defends.
revoke all on ai_request_usage from anon, authenticated;

grant select on ai_request_usage to authenticated;
grant select, insert, update, delete on ai_request_usage to service_role;

revoke all on function consume_ai_quota(integer, interval, integer, interval)
  from public, anon, authenticated;
revoke all on function record_audit_event(text, text, text, jsonb)
  from public, anon, authenticated;

grant execute on function consume_ai_quota(integer, interval, integer, interval)
  to authenticated;
grant execute on function record_audit_event(text, text, text, jsonb)
  to authenticated;
