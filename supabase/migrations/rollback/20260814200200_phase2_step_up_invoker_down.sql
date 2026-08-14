-- Rollback for 20260814200200_phase2_step_up_invoker.sql.
-- Restores security definer on meets_step_up(), matching
-- 20260814200100_phase2_step_up_relaxation.sql's original body.
create or replace function meets_step_up() returns boolean
language sql stable security definer set search_path = public
as $$ select true $$;
