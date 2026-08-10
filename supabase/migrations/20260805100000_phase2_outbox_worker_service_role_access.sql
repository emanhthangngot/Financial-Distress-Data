-- Fix: the outbox worker's claim/complete/fail functions called
-- assert_platform_write_access(), which requires an operator/admin JWT at
-- AAL2. The worker is a background process holding the service-role key —
-- it has no end-user JWT and therefore no app role or AAL claim, so every
-- claim/complete/fail call raised "role <none> may not mutate evidence
-- sessions" and the worker could never actually run.
--
-- `current_setting('role', true)` reads the Postgres role GUC as it was set
-- by the caller (`set role service_role`, or the equivalent PostgREST
-- switch for a service-role request) — unlike `current_user`, this is not
-- overridden to the function owner inside a SECURITY DEFINER body, so it is
-- a reliable signal of which Postgres role invoked the function.
create or replace function assert_worker_access() returns void
language plpgsql
stable
set search_path = public
as $$
begin
  if current_setting('role', true) is distinct from 'service_role' then
    raise exception 'only the service role may claim or resolve outbox events'
      using errcode = '42501';
  end if;
end;
$$;

create or replace function claim_outbox_events(
  p_worker_id text,
  p_limit integer default 5,
  p_lease_seconds integer default 120
) returns setof outbox_events
language plpgsql
security definer
set search_path = public
as $$
begin
  perform assert_worker_access();

  return query
  with claimable as (
    select id
    from outbox_events
    where status = 'PENDING'
      and (lease_expiry is null or lease_expiry < now())
    order by created_at
    limit p_limit
    for update skip locked
  )
  update outbox_events
  set claimed_by = p_worker_id,
      claimed_at = now(),
      lease_expiry = now() + make_interval(secs => p_lease_seconds),
      attempts = attempts + 1
  where id in (select id from claimable)
  returning *;
end;
$$;

create or replace function complete_outbox_event(
  p_event_id uuid,
  p_worker_id text,
  p_result text
) returns outbox_events
language plpgsql
security definer
set search_path = public
as $$
declare
  v_event outbox_events;
  v_session_token text;
begin
  perform assert_worker_access();

  select * into v_event from outbox_events where id = p_event_id for update;

  if not found then
    raise exception 'outbox event % not found', p_event_id using errcode = 'P0002';
  end if;

  if v_event.claimed_by is distinct from p_worker_id then
    raise exception 'outbox event % is not claimed by %', p_event_id, p_worker_id
      using errcode = '40001';
  end if;

  select fencing_token into v_session_token
  from evidence_session where id = v_event.session_id;

  -- A raised exception here would abort this call's implicit transaction and
  -- roll back the very row update meant to record the rejection, leaving the
  -- event looking untouched. Returning the FAILED row instead of raising is
  -- what makes the mark durable; the caller distinguishes this outcome from a
  -- real success by inspecting the returned `status`, not by catching an
  -- error.
  if v_event.fencing_token is distinct from v_session_token then
    update outbox_events
    set status = 'FAILED',
        last_error = 'stale fencing token: session advanced past this event',
        completed_at = now()
    where id = p_event_id
    returning * into v_event;

    return v_event;
  end if;

  update outbox_events
  set status = 'DONE',
      result = p_result,
      completed_at = now(),
      lease_expiry = null
  where id = p_event_id
  returning * into v_event;

  return v_event;
end;
$$;

create or replace function fail_outbox_event(
  p_event_id uuid,
  p_worker_id text,
  p_error text,
  p_max_attempts integer default 5
) returns outbox_events
language plpgsql
security definer
set search_path = public
as $$
declare
  v_event outbox_events;
begin
  perform assert_worker_access();

  select * into v_event from outbox_events where id = p_event_id for update;

  if not found then
    raise exception 'outbox event % not found', p_event_id using errcode = 'P0002';
  end if;

  if v_event.claimed_by is distinct from p_worker_id then
    raise exception 'outbox event % is not claimed by %', p_event_id, p_worker_id
      using errcode = '40001';
  end if;

  update outbox_events
  set status = case when v_event.attempts >= p_max_attempts then 'FAILED'::outbox_status else 'PENDING'::outbox_status end,
      last_error = p_error,
      lease_expiry = null,
      claimed_by = null,
      completed_at = case when v_event.attempts >= p_max_attempts then now() else null end
  where id = p_event_id
  returning * into v_event;

  return v_event;
end;
$$;

revoke all on function assert_worker_access() from public, anon, authenticated;
grant execute on function assert_worker_access() to service_role;
