-- Rollback for 20260805100000_phase2_outbox_worker_service_role_access.sql.
-- Restores the pre-fix function bodies (assert_platform_write_access gate)
-- and drops assert_worker_access. This intentionally reintroduces the
-- worker-cannot-authenticate defect the forward migration fixed — only use
-- this to fully revert the migration, not as a standalone change.

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
  perform assert_platform_write_access();

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
  perform assert_platform_write_access();

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

  if v_event.fencing_token is distinct from v_session_token then
    update outbox_events
    set status = 'FAILED',
        last_error = 'stale fencing token: session advanced past this event',
        completed_at = now()
    where id = p_event_id
    returning * into v_event;

    raise exception 'stale fencing token for outbox event %', p_event_id
      using errcode = '40001';
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
  perform assert_platform_write_access();

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

drop function if exists assert_worker_access();
