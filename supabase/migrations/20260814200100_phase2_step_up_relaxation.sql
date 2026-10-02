-- Phase 2 auth: relax the AAL2 step-up requirement for this demo environment.
--
-- is_aal2() keeps telling the truth about the caller's assurance level; it is
-- not touched. meets_step_up() is a separate, named predicate that encodes the
-- environment decision: no MFA enrollment path exists in this deployment, so
-- step-up cannot be satisfied and gating on it only locks operators out.
-- Every policy/function that gated on is_aal2() now gates on meets_step_up()
-- instead, so the substitution is greppable in one direction.
--
-- Revert = restore this function to `select is_aal2()` (see the rollback
-- file), which puts every dependent policy back behind real AAL2 without
-- touching them again.
create or replace function meets_step_up() returns boolean
language sql stable security definer set search_path = public
as $$ select true $$;

revoke all on function meets_step_up() from public;
grant execute on function meets_step_up() to authenticated, service_role;

-- profiles: admin read/update of other rows.
drop policy if exists profiles_select_admin on profiles;
create policy profiles_select_admin on profiles
  for select using ((select current_app_role()) = 'platform_admin' and (select meets_step_up()));

drop policy if exists profiles_update_admin on profiles;
create policy profiles_update_admin on profiles
  for update using ((select current_app_role()) = 'platform_admin' and (select meets_step_up()))
  with check ((select current_app_role()) = 'platform_admin' and (select meets_step_up()));

-- evidence_session and its derived tables: privileged-role read.
drop policy if exists evidence_session_select on evidence_session;
create policy evidence_session_select on evidence_session
  for select using ((select is_privileged_role()) and (select meets_step_up()));

drop policy if exists evidence_session_transition_select on evidence_session_transition;
create policy evidence_session_transition_select on evidence_session_transition
  for select using ((select is_privileged_role()) and (select meets_step_up()));

drop policy if exists outbox_events_select on outbox_events;
create policy outbox_events_select on outbox_events
  for select using ((select is_privileged_role()) and (select meets_step_up()));

-- audit_log: privileged-role read.
drop policy if exists audit_log_select_privileged on audit_log;
create policy audit_log_select_privileged on audit_log
  for select using ((select is_privileged_role()) and (select meets_step_up()));

-- The evidence-session write path gate (create_evidence_session /
-- request_session_transition, via assert_platform_write_access()).
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

  if not meets_step_up() then
    raise exception 'AAL2 required to mutate evidence sessions'
      using errcode = '42501';
  end if;
end;
$$;
