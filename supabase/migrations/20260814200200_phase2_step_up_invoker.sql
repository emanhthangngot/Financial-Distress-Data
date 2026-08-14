-- Follow-up to 20260814200100_phase2_step_up_relaxation.sql: meets_step_up()
-- has no reason to run as security definer -- it reads and touches nothing,
-- it is a constant. security advisor flagged it as an anon-executable
-- SECURITY DEFINER function (WARN); dropping the elevation removes the
-- warning with no behavior change, since the function never used any
-- elevated privilege in the first place.
create or replace function meets_step_up() returns boolean
language sql stable set search_path = public
as $$ select true $$;
