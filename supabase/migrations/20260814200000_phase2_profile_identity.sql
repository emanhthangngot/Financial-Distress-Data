-- Phase 2 auth: turn `profiles` into a real user table (identity, not just a
-- role). Adds display_name/email, backfills both from auth.users, and moves
-- handle_new_user() to copy them on signup. Owner-writable display_name only
-- is enforced by a column grant + policy so a client cannot self-escalate role
-- through the same write path.

alter table profiles
  add column display_name text,
  add column email text;

update profiles p
set email = u.email,
    display_name = nullif(trim(coalesce(u.raw_user_meta_data ->> 'full_name', '')), '')
from auth.users u
where u.id = p.user_id;

-- handle_new_user: on conflict do nothing stays — an exception here aborts the
-- auth.users insert and turns signup into a 500.
create or replace function handle_new_user() returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into profiles (user_id, role, email, display_name)
  values (
    new.id,
    'analyst',
    new.email,
    nullif(trim(coalesce(new.raw_user_meta_data ->> 'full_name', '')), '')
  )
  on conflict (user_id) do nothing;
  return new;
end;
$$;

-- RLS cannot restrict columns, so the column grant does it: revoke the broad
-- update grant from 20260803214600_phase2_rls.sql and grant back only
-- display_name. This makes profiles_update_admin's role-write path
-- unreachable from the anon-key client too -- a column-level grant cannot be
-- scoped per-policy, so no `authenticated` caller, including platform_admin,
-- can write `role` through this table anymore. That is intentional and
-- matches this plan's non-goal (no admin role-editor UI; role changes stay
-- SQL/service-role, which bypasses grants entirely). The policy itself is
-- left in place rather than dropped, since it still correctly scopes admin's
-- read of other rows (profiles_select_admin shares its using clause).
revoke update on profiles from authenticated;
grant update (display_name) on profiles to authenticated;

create policy profiles_update_own on profiles
  for update using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));
