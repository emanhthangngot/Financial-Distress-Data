-- Rollback for 20260814200100_phase2_step_up_relaxation.sql.
-- Restores meets_step_up() to defer to the real is_aal2() check, which puts
-- every policy and function below back behind real AAL2 without editing them
-- again -- they all call meets_step_up(), not is_aal2(), directly.

create or replace function meets_step_up() returns boolean
language sql stable security definer set search_path = public
as $$ select is_aal2() $$;
