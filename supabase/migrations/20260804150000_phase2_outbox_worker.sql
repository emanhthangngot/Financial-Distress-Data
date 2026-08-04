-- Outbox worker claim path.
--
-- The transition and the outbox row already commit atomically in
-- request_session_transition. What was missing is the other half: a worker that
-- can pick up pending events exactly once, record what happened, and be safe to
-- run as more than one process.
--
-- The design is lease-based rather than lock-based. A worker claims an event for
-- a bounded window; if it dies, the lease expires and another worker picks the
-- event up. That is why claim_outbox_events also reclaims events whose lease has
-- passed: a crashed worker must not strand infrastructure work forever.

alter table outbox_events
  add column if not exists result text,
  add column if not exists last_error text,
  add column if not exists completed_at timestamptz,
  -- The fencing token observed when the event was written. A worker that wakes
  -- up holding an old token must not act: the session has moved on without it.
  add column if not exists fencing_token text;

-- Existing rows predate the column and have no token to check against; they are
-- historical and are never claimed again.
update outbox_events set status = 'FAILED', last_error = 'no fencing token recorded'
where fencing_token is null and status = 'PENDING';

create index if not exists outbox_events_claimable_idx
  on outbox_events (status, lease_expiry);

-- Record the fencing token on every new outbox row so the worker can prove the
-- session has not moved on since the event was written.
create or replace function request_session_transition(
  p_session_id uuid,
  p_target_state session_state,
  p_actor text,
  p_idempotency_key text,
  p_fencing_token text
) returns evidence_session
language plpgsql
security definer
set search_path = public
as $$
declare
  v_session evidence_session;
  v_next_fencing_token text := gen_random_uuid()::text;
begin
  perform assert_platform_write_access();

  select * into v_session from evidence_session where id = p_session_id for update;

  if not found then
    raise exception 'evidence_session % not found', p_session_id
      using errcode = 'P0002';
  end if;

  if v_session.idempotency_key = p_idempotency_key then
    if v_session.state = p_target_state then
      return v_session;
    end if;

    raise exception
      'idempotency key % already applied to session % at state %, cannot reuse it to reach %',
      p_idempotency_key, p_session_id, v_session.state, p_target_state
      using errcode = '23505';
  end if;

  if v_session.fencing_token <> p_fencing_token then
    raise exception 'stale fencing token for session %', p_session_id
      using errcode = '40001';
  end if;

  if not exists (
    select 1 from session_transition_rule
    where from_state = v_session.state and to_state = p_target_state
  ) then
    raise exception 'illegal transition % -> % for session %', v_session.state, p_target_state, p_session_id
      using errcode = '22023';
  end if;

  insert into evidence_session_transition (
    session_id, from_state, to_state, version, actor, idempotency_key, fencing_token
  ) values (
    p_session_id, v_session.state, p_target_state, v_session.version + 1, p_actor, p_idempotency_key, p_fencing_token
  );

  -- The token written here is the NEW one the session will hold after this
  -- transition, so the worker's check passes only while no later transition has
  -- rotated it again.
  insert into outbox_events (session_id, target_state, fencing_token)
  values (p_session_id, p_target_state, v_next_fencing_token);

  update evidence_session
  set state = p_target_state,
      version = version + 1,
      actor = p_actor,
      idempotency_key = p_idempotency_key,
      fencing_token = v_next_fencing_token
  where id = p_session_id
  returning * into v_session;

  return v_session;
end;
$$;

-- Claim up to p_limit events for p_worker_id for p_lease_seconds.
--
-- `for update skip locked` is what makes two workers running concurrently safe:
-- each takes different rows rather than blocking on the same one.
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
      -- Either never claimed, or claimed by a worker whose lease has expired.
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

-- Mark a claimed event done. Rejects a claim the worker no longer holds and a
-- token the session has rotated past, so a worker that stalled through another
-- operator's transition cannot report success for work that is now irrelevant.
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

-- Record a failed attempt. The event returns to PENDING until it exhausts
-- p_max_attempts, so a transient infrastructure error retries and a persistent
-- one stops rather than looping forever.
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

revoke all on function claim_outbox_events(text, integer, integer) from public, anon, authenticated;
revoke all on function complete_outbox_event(uuid, text, text) from public, anon, authenticated;
revoke all on function fail_outbox_event(uuid, text, text, integer) from public, anon, authenticated;
