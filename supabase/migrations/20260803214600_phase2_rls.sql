-- RBAC enforcement in Postgres RLS, per phase-02 Authorization Model:
-- analyst | platform_viewer | platform_operator | platform_admin.
-- All privileged (non-analyst) roles additionally require Supabase AAL2.
--
-- Helper functions (current_app_role, is_aal2, is_privileged_role) live in the
-- schema migration next to the profiles table they read.
--
-- Every helper call is wrapped in a scalar subquery so the planner hoists it
-- into an InitPlan and evaluates it once per statement instead of once per
-- candidate row; current_app_role() reads profiles, so the unwrapped form costs
-- an index lookup for every row scanned.

-- Auto-provision a profile row (default role: analyst) on signup. The conflict
-- clause matters: an exception here aborts the auth.users insert and turns
-- signup into a 500, so a re-provisioned user id must not be fatal.
create or replace function handle_new_user() returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into profiles (user_id, role)
  values (new.id, 'analyst')
  on conflict (user_id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function handle_new_user();

alter table profiles enable row level security;
alter table evidence_session enable row level security;
alter table evidence_session_transition enable row level security;
alter table outbox_events enable row level security;
alter table saved_reports enable row level security;
alter table audit_log enable row level security;
alter table session_transition_rule enable row level security;

-- profiles: everyone reads their own row; platform_admin (AAL2) reads/updates
-- any row to administer roles.
create policy profiles_select_own on profiles
  for select using (user_id = (select auth.uid()));

create policy profiles_select_admin on profiles
  for select using ((select current_app_role()) = 'platform_admin' and (select is_aal2()));

create policy profiles_update_admin on profiles
  for update using ((select current_app_role()) = 'platform_admin' and (select is_aal2()))
  with check ((select current_app_role()) = 'platform_admin' and (select is_aal2()));

-- evidence_session and its derived tables are read-only to every client role.
-- There is deliberately no insert/update/delete policy: the only write path is
-- create_evidence_session() / request_session_transition(), which commit the
-- session row and its outbox row in one transaction. A direct client UPDATE
-- would skip the state machine, skip the outbox, and let the caller rewrite its
-- own fencing token, so the privilege is revoked outright below rather than
-- merely left unpoliced, where a later default grant could quietly re-open it.
create policy evidence_session_select on evidence_session
  for select using ((select is_privileged_role()) and (select is_aal2()));

create policy evidence_session_transition_select on evidence_session_transition
  for select using ((select is_privileged_role()) and (select is_aal2()));

create policy outbox_events_select on outbox_events
  for select using ((select is_privileged_role()) and (select is_aal2()));

-- The legal state graph is reference data for any signed-in user.
create policy session_transition_rule_select on session_transition_rule
  for select using ((select auth.uid()) is not null);

-- saved_reports: an analyst reads, writes, edits and deletes only their own.
create policy saved_reports_select_own on saved_reports
  for select using (owner_id = (select auth.uid()));

create policy saved_reports_insert_own on saved_reports
  for insert with check (
    owner_id = (select auth.uid()) and (select current_app_role()) = 'analyst'
  );

create policy saved_reports_update_own on saved_reports
  for update using (owner_id = (select auth.uid()))
  with check (owner_id = (select auth.uid()));

create policy saved_reports_delete_own on saved_reports
  for delete using (owner_id = (select auth.uid()));

-- audit_log: append-only (no update/delete policy exists, so both are denied).
-- actor_role is pinned to the writer's real role; leaving it caller-supplied
-- would let an analyst forge a platform_admin entry in the evidence trail.
create policy audit_log_insert_self on audit_log
  for insert with check (
    actor_id = (select auth.uid()) and actor_role = (select current_app_role())
  );

create policy audit_log_select_privileged on audit_log
  for select using ((select is_privileged_role()) and (select is_aal2()));

-- Explicit privilege surface. Supabase's default privileges grant broadly to
-- anon and authenticated, so policies alone are not the whole story: revoke
-- first, then grant back only what a policy is prepared to defend.
revoke all on profiles, evidence_session, evidence_session_transition,
  outbox_events, saved_reports, audit_log, session_transition_rule
  from anon, authenticated;

grant select, update on profiles to authenticated;
grant select on evidence_session, evidence_session_transition, outbox_events to authenticated;
grant select on session_transition_rule to authenticated;
grant select, insert, update, delete on saved_reports to authenticated;
grant select, insert on audit_log to authenticated;

-- The outbox worker runs as service_role, which bypasses RLS and needs to claim
-- and complete events.
grant select, insert, update, delete on profiles, evidence_session,
  evidence_session_transition, outbox_events, saved_reports, audit_log
  to service_role;
grant select on session_transition_rule to service_role;

-- Functions default to EXECUTE TO PUBLIC, which would otherwise expose the
-- security definer write path to anon.
revoke all on function create_evidence_session(text, text) from public;
revoke all on function request_session_transition(uuid, session_state, text, text, text) from public;
revoke all on function assert_platform_write_access() from public;
revoke all on function current_app_role() from public;
revoke all on function is_aal2() from public;
revoke all on function is_privileged_role() from public;
revoke all on function handle_new_user() from public;

grant execute on function create_evidence_session(text, text) to authenticated, service_role;
grant execute on function request_session_transition(uuid, session_state, text, text, text)
  to authenticated, service_role;
grant execute on function current_app_role() to authenticated, service_role;
grant execute on function is_aal2() to authenticated, service_role;
grant execute on function is_privileged_role() to authenticated, service_role;
