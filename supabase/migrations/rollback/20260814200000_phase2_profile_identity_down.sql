-- Rollback for 20260814200000_phase2_profile_identity.sql.
-- Restores the pre-identity handle_new_user() body, the broad update grant,
-- and drops the owner-only policy and the two identity columns.

drop policy if exists profiles_update_own on profiles;

revoke update (display_name) on profiles from authenticated;
grant update on profiles to authenticated;

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

alter table profiles
  drop column if exists display_name,
  drop column if exists email;
