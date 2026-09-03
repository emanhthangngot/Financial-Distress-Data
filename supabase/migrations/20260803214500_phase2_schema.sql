-- Phase 2 product shell schema: roles, evidence session state machine, outbox,
-- saved reports, audit log. Additive only; does not touch Phase 1 Postgres
-- schemas (ops / ml).

create type app_role as enum (
  'analyst',
  'platform_viewer',
  'platform_operator',
  'platform_admin'
);

create type session_state as enum (
  'OFF',
  'REQUESTED',
  'PROVISIONING',
  'SYNCING',
  'READY',
  'CAPTURING',
  'DESTROYING',
  'FAILED',
  'EXPIRED'
);

create type outbox_status as enum ('PENDING', 'CLAIMED', 'DONE', 'FAILED');

create table profiles (
  user_id uuid primary key references auth.users (id) on delete cascade,
  role app_role not null default 'analyst',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table evidence_session (
  id uuid primary key default gen_random_uuid(),
  state session_state not null default 'OFF',
  version integer not null default 1,
  actor text not null,
  idempotency_key text not null,
  lease_expiry timestamptz,
  fencing_token text not null default gen_random_uuid()::text,
  cost_snapshot_usd numeric(10, 2),
  git_sha text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table evidence_session_transition (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references evidence_session (id) on delete cascade,
  from_state session_state not null,
  to_state session_state not null,
  version integer not null,
  actor text not null,
  idempotency_key text not null,
  fencing_token text not null,
  created_at timestamptz not null default now()
);

create table outbox_events (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references evidence_session (id) on delete cascade,
  target_state session_state not null,
  status outbox_status not null default 'PENDING',
  claimed_by text,
  claimed_at timestamptz,
  lease_expiry timestamptz,
  attempts integer not null default 0,
  created_at timestamptz not null default now()
);

create table saved_reports (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users (id) on delete cascade,
  company_id text not null,
  payload jsonb not null,
  created_at timestamptz not null default now()
);

-- Consent-safe audit trail: caller must never write prompts, tokens, or
-- secrets into metadata; enforced at the application boundary, not here.
-- actor_role is not caller-supplied trivia: the insert policy pins it to the
-- writer's real role so the trail stays evidentiary.
create table audit_log (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid references auth.users (id) on delete set null,
  actor_role app_role not null,
  action text not null,
  resource text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index evidence_session_transition_session_id_idx on evidence_session_transition (session_id);
create index outbox_events_session_id_idx on outbox_events (session_id);
create index outbox_events_status_idx on outbox_events (status);
create index saved_reports_owner_id_idx on saved_reports (owner_id);
create index audit_log_actor_id_idx on audit_log (actor_id);

-- Single source of truth for the legal session state graph. The TypeScript
-- contract package reads the same pairs from session-transitions.json, and a
-- test asserts the two stay identical, so the graph is never hand-encoded in
-- two places that can drift apart.
create table session_transition_rule (
  from_state session_state not null,
  to_state session_state not null,
  primary key (from_state, to_state)
);

-- DESTROYING is reachable from every live state, not just READY/CAPTURING: an
-- operator must be able to tear down a session wedged mid-provision, which is
-- exactly the case that keeps burning cloud spend.
insert into session_transition_rule (from_state, to_state) values
  ('OFF', 'REQUESTED'),
  ('REQUESTED', 'PROVISIONING'),
  ('REQUESTED', 'DESTROYING'),
  ('REQUESTED', 'FAILED'),
  ('PROVISIONING', 'SYNCING'),
  ('PROVISIONING', 'DESTROYING'),
  ('PROVISIONING', 'FAILED'),
  ('SYNCING', 'READY'),
  ('SYNCING', 'DESTROYING'),
  ('SYNCING', 'FAILED'),
  ('READY', 'CAPTURING'),
  ('READY', 'DESTROYING'),
  ('READY', 'EXPIRED'),
  ('CAPTURING', 'DESTROYING'),
  ('CAPTURING', 'FAILED'),
  ('DESTROYING', 'OFF'),
  ('DESTROYING', 'FAILED'),
  ('FAILED', 'REQUESTED'),
  ('FAILED', 'DESTROYING'),
  ('FAILED', 'OFF'),
  ('EXPIRED', 'DESTROYING'),
  ('EXPIRED', 'OFF');

create or replace function set_updated_at() returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

create trigger profiles_set_updated_at
  before update on profiles
  for each row execute function set_updated_at();

create trigger evidence_session_set_updated_at
  before update on evidence_session
  for each row execute function set_updated_at();

-- Role/AAL helpers. security definer on current_app_role() is required: an RLS
-- policy on profiles would otherwise recurse when it asks for the caller's role.
create or replace function current_app_role() returns app_role
language sql
security definer
stable
set search_path = public
as $$
  select role from profiles where user_id = auth.uid();
$$;

create or replace function is_aal2() returns boolean
language sql
stable
set search_path = public
as $$
  select coalesce((auth.jwt() ->> 'aal') = 'aal2', false);
$$;

create or replace function is_privileged_role() returns boolean
language sql
stable
set search_path = public
as $$
  select current_app_role() in ('platform_viewer', 'platform_operator', 'platform_admin');
$$;

-- Shared guard for the security-definer write path. Written as an explicit
-- positive assertion: a caller with no profiles row yields a null role, and
-- `null not in (...)` evaluates to null rather than true, so a bare negated
-- membership test would wave an unknown role straight through.
create or replace function assert_platform_write_access() returns void
language plpgsql
stable
set search_path = public
as $$
declare
  v_role app_role := current_app_role();
begin
  if v_role is null or v_role not in ('platform_operator', 'platform_admin') then
    raise exception 'role % may not mutate evidence sessions', coalesce(v_role::text, '<none>')
      using errcode = '42501';
  end if;

  if not is_aal2() then
    raise exception 'AAL2 required to mutate evidence sessions'
      using errcode = '42501';
  end if;
end;
$$;

-- Sessions are created only here. Direct inserts are revoked from the client
-- roles so every row starts inside the state machine holding a server-issued
-- fencing token.
create or replace function create_evidence_session(
  p_actor text,
  p_idempotency_key text
) returns evidence_session
language plpgsql
security definer
set search_path = public
as $$
declare
  v_session evidence_session;
begin
  perform assert_platform_write_access();

  insert into evidence_session (actor, idempotency_key)
  values (p_actor, p_idempotency_key)
  returning * into v_session;

  return v_session;
end;
$$;

-- Atomic transition + outbox write: caller passes the fencing token and
-- idempotency key it observed; a stale fencing token or illegal target state
-- raises and rolls back the transition row, the outbox row, and the session
-- update together.
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
  -- security definer bypasses table RLS, so this guard is the sole enforcement
  -- point for the privileged write path.
  perform assert_platform_write_access();

  select * into v_session from evidence_session where id = p_session_id for update;

  if not found then
    raise exception 'evidence_session % not found', p_session_id
      using errcode = 'P0002';
  end if;

  if v_session.idempotency_key = p_idempotency_key then
    -- Same key, same destination: the caller is retrying a request that already
    -- landed, so replay the current row instead of transitioning twice.
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

  insert into outbox_events (session_id, target_state) values (p_session_id, p_target_state);

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
