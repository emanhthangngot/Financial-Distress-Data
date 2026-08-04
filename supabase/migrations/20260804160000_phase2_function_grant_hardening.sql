-- Function privilege hardening, from the Supabase security advisor run after the
-- first deploy of the phase-02 schema.
--
-- The RLS migration revoked the write path `from public`, which is not the whole
-- story: Supabase's default privileges grant EXECUTE on new public-schema
-- functions to `anon` and `authenticated` directly, and a grant to a named role
-- survives a revoke from PUBLIC. The advisor correctly reported that `anon`
-- could still call `request_session_transition` over the REST RPC endpoint.
--
-- Nothing was exploitable: `assert_platform_write_access()` reads the caller's
-- profile row, an anonymous caller has none, and a null role raises. But an
-- unauthenticated caller reaching the state machine at all is one guard away
-- from a hole, so the privilege is removed rather than left to the guard.

-- 1. A trigger function with a mutable search_path can be redirected by a
--    caller-controlled search_path. It only sets a timestamp, but it runs on
--    every profile and session update, so it is pinned like the others.
create or replace function set_updated_at() returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

-- 2. The evidence-session write path is for signed-in platform roles only.
revoke execute on function create_evidence_session(text, text) from anon;
revoke execute on function request_session_transition(uuid, session_state, text, text, text) from anon;

-- 3. `handle_new_user` is a trigger function. Nothing should call it directly:
--    invoked over RPC it has no NEW record and fails, but it is security definer
--    and writes to profiles, so it is not left reachable.
revoke execute on function handle_new_user() from anon, authenticated;

-- 4. Role helpers stay callable by signed-in users — RLS policies evaluate them
--    as the querying role — but not by anonymous callers, who have no profile
--    row and no table grants to use them with.
revoke execute on function current_app_role() from anon;
revoke execute on function is_aal2() from anon;
revoke execute on function is_privileged_role() from anon;
revoke execute on function assert_platform_write_access() from anon, authenticated;

-- 5. The worker functions are explicitly granted to service_role rather than
--    relying on a default privilege that a later revoke could remove.
grant execute on function claim_outbox_events(text, integer, integer) to service_role;
grant execute on function complete_outbox_event(uuid, text, text) to service_role;
grant execute on function fail_outbox_event(uuid, text, text, integer) to service_role;
